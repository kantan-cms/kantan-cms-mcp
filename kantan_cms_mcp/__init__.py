"""Kantan CMS MCP.

A per-user MCP (authenticated with an MCP key that acts as the signed-in user)
for managing your tenants and projects and generating websites: read a
spreadsheet, create tenants + projects, generate a site, and download/upload it
to a project's repository. It calls the backend user-JWT surface (/v1/app) with
the key, so everything is owned and billed to that user.

Layout mirrors the backend's clean architecture:
  interfaces/   MCP tools (entrypoints)
  applications/ use cases (orchestration)
  domains/      entities + the KantanApi port
  infras/       HTTP client (X-MCP-Key + /v1/app) and the Excel reader
"""
from fastmcp import FastMCP

from kantan_cms_mcp.interfaces.tools import register_tools

mcp = FastMCP("kantan-cms")
register_tools(mcp)

__all__ = ["mcp"]
