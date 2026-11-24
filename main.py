"""Entrypoint: start the operator-provisioning MCP server.

Required env (the operator account + target backend):
  CMS_BASE_URL              e.g. https://api.kantan-cms.dev
  SUPABASE_URL              the project's Supabase URL
  SUPABASE_ANON_KEY         the Supabase anon key
  KANTAN_OPERATOR_EMAIL     the operator account's email
  KANTAN_OPERATOR_PASSWORD  the operator account's password

Credentials are validated lazily on the first tool call (so the server can
start and advertise its tools without them), but we check them up front here to
fail fast when run directly.
"""
from kantan_cms_mcp import mcp
from kantan_cms_mcp.config import load_config

if __name__ == "__main__":
    try:
        load_config()
        print("Operator credentials present; starting MCP server.")
    except ValueError as e:
        print(f"Error: {e}")
        print("MCP server startup aborted due to missing environment variables.")
        raise SystemExit(1)
    mcp.run()
