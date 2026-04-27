"""scriptorium.mcp — MCP server package for Cowork integration (T04).

Entry points:
    scriptorium-mcp   → scriptorium.mcp:main  (console script)
    python -m scriptorium.mcp                 (module run via __main__.py)
"""
from __future__ import annotations


def main() -> None:
    """Run the Scriptorium MCP server over stdio."""
    from scriptorium.mcp.server import mcp
    mcp.run(transport="stdio")
