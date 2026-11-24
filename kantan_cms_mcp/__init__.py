"""Kantan CMS operator-provisioning MCP.

An OPERATOR-only MCP (keyed to a single Kantan account's Supabase credentials)
that automates agency-style lead provisioning: read a spreadsheet, create a
tenant + project per lead (the operator is the owner), and hand tenants to
paying clients. It calls the backend user-JWT surface (/v1/app). Do NOT expose
this to end users — it can create tenants and memberships.

Layout mirrors the backend's clean architecture:
  interfaces/   MCP tools (entrypoints)
  applications/ use cases (orchestration)
  domains/      entities + the KantanApi port
  infras/       HTTP client (Supabase auth + /v1/app) and the Excel reader
"""
from fastmcp import FastMCP

from kantan_cms_mcp.interfaces.tools import register_tools

mcp = FastMCP("kantan-cms-operator")
register_tools(mcp)

__all__ = ["mcp"]
