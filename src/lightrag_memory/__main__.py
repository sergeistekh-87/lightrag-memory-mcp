"""Entry point for CLI execution: uvx lightrag-memory or uv run -m lightrag_memory"""

from .server import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
