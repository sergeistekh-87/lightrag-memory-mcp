"""HTTP client for LightRAG REST API with typed error handling."""

import json
import logging
import os
from typing import Any, Optional, AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

LIGHTRAG_URL = os.getenv("LIGHTRAG_BASE_URL", "http://localhost:9621").rstrip("/")
API_KEY = os.getenv("LIGHTRAG_API_KEY", "")
DEFAULT_TIMEOUT = float(os.getenv("LIGHTRAG_TIMEOUT", "60.0"))

BASE_HEADERS: dict[str, str] = {}
if API_KEY:
    BASE_HEADERS["X-API-Key"] = API_KEY


# ─── Exception Hierarchy ─────────────────────────────────────────────────────

class LightRAGError(Exception):
    """Base exception for all LightRAG client errors."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class LightRAGConnectionError(LightRAGError):
    """Server is unreachable."""


class LightRAGAuthError(LightRAGError):
    """Authentication failed (401/403). Check LIGHTRAG_API_KEY."""


class LightRAGValidationError(LightRAGError):
    """Bad request parameters (400/422)."""


class LightRAGNotFoundError(LightRAGError):
    """Resource not found (404)."""


class LightRAGRateLimitError(LightRAGError):
    """Rate limited (429). Slow down or retry later."""


class LightRAGServerError(LightRAGError):
    """Server-side error (5xx). May be temporary (503 = Gemini overloaded)."""


class LightRAGTimeoutError(LightRAGError):
    """Request timed out."""


# ─── Error Mapping ───────────────────────────────────────────────────────────

def _map_error(status_code: int, body: str) -> LightRAGError:
    """Map HTTP status code to a typed exception."""
    try:
        detail = json.loads(body).get("detail", body)
    except Exception:
        detail = body

    msg = str(detail)
    if status_code in (401, 403):
        return LightRAGAuthError(msg, status_code)
    if status_code in (400, 422):
        return LightRAGValidationError(msg, status_code)
    if status_code == 404:
        return LightRAGNotFoundError(msg, status_code)
    if status_code == 429:
        return LightRAGRateLimitError(msg, status_code)
    if status_code >= 500:
        return LightRAGServerError(msg, status_code)
    return LightRAGError(msg, status_code)


# ─── Client ──────────────────────────────────────────────────────────────────

def get_client(timeout: float | None = None) -> httpx.AsyncClient:
    """Return a configured async HTTP client with auth headers."""
    return httpx.AsyncClient(
        base_url=LIGHTRAG_URL,
        headers=BASE_HEADERS,
        timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
    )


async def request(
    method: str,
    path: str,
    *,
    json: Any = None,
    params: dict | None = None,
    files: dict | None = None,
    timeout: float = 60.0,
) -> Any:
    """
    Make a single HTTP request and return parsed JSON.
    Raises typed LightRAGError subclasses on failures.
    """
    try:
        async with get_client(timeout=timeout) as c:
            if files:
                r = await c.request(method, path, data=json or {}, files=files)
            elif json is not None:
                r = await c.request(method, path, json=json, params=params)
            else:
                r = await c.request(method, path, params=params)

        if not r.is_success:
            raise _map_error(r.status_code, r.text)

        if r.content:
            try:
                return r.json()
            except Exception:
                return r.text
        return None

    except (LightRAGError,):
        raise
    except httpx.ConnectError as e:
        raise LightRAGConnectionError(
            f"Cannot connect to LightRAG at {LIGHTRAG_URL}. "
            f"Is the server running? (docker compose up -d): {e}"
        )
    except httpx.TimeoutException as e:
        raise LightRAGTimeoutError(f"Request timed out ({timeout}s): {e}")
    except Exception as e:
        raise LightRAGError(f"Unexpected error: {e}")


async def stream_request(
    method: str,
    path: str,
    *,
    json: Any = None,
    timeout: float = 90.0,
) -> AsyncGenerator[str, None]:
    """Make a streaming HTTP request and yield text chunks."""
    try:
        async with get_client(timeout=timeout) as c:
            async with c.stream(method, path, json=json) as r:
                if not r.is_success:
                    body = await r.aread()
                    raise _map_error(r.status_code, body.decode())
                async for chunk in r.aiter_text():
                    if chunk.strip():
                        yield chunk
    except (LightRAGError,):
        raise
    except httpx.ConnectError as e:
        raise LightRAGConnectionError(f"Cannot connect to {LIGHTRAG_URL}: {e}")
    except httpx.TimeoutException as e:
        raise LightRAGTimeoutError(f"Streaming request timed out: {e}")
    except Exception as e:
        raise LightRAGError(f"Streaming error: {e}")
