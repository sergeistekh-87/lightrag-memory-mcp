"""HTTP client for LightRAG REST API."""

import os
import httpx

LIGHTRAG_URL = os.getenv("LIGHTRAG_BASE_URL", "http://localhost:9621")
API_KEY = os.getenv("LIGHTRAG_API_KEY", "")

HEADERS: dict[str, str] = {}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY


def get_client(timeout: float = 60.0) -> httpx.AsyncClient:
    """Return a configured async HTTP client."""
    return httpx.AsyncClient(
        base_url=LIGHTRAG_URL,
        headers=HEADERS,
        timeout=timeout,
    )
