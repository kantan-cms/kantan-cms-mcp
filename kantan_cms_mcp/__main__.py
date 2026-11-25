"""Console entrypoint: `kantan-cms-mcp`, `python -m kantan_cms_mcp`, or the root
`main.py` all land here. Starts the MCP over stdio.

Credentials are validated lazily on the first tool call (so the server can
start and advertise its tools without them), but we check them up front to fail
fast when run directly. Required env:
  CMS_BASE_URL, KANTAN_MCP_KEY
"""
from __future__ import annotations

from kantan_cms_mcp import mcp
from kantan_cms_mcp.config import load_config


def main() -> None:
    try:
        load_config()
        print("MCP key present; starting MCP server.")
    except ValueError as e:
        print(f"Error: {e}")
        print("MCP server startup aborted due to missing environment variables.")
        raise SystemExit(1) from e
    mcp.run()


if __name__ == "__main__":
    main()
