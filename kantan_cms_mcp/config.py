"""Runtime configuration (environment). The MCP authenticates as a single
Kantan USER via a per-user MCP key (`X-MCP-Key`) and calls the backend's
user-JWT surface (/v1/app). The key acts as that user across all their tenants,
so everything it does — tenants, projects, generation — is owned and billed to
that user. Each person who runs the MCP supplies their own key."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    cms_base_url: str  # e.g. https://api.kantan-cms.dev
    mcp_key: str  # per-user MCP key, created in the console (account → MCP)
    # Idempotency ledger file (local). Override with KANTAN_MCP_LEDGER.
    ledger_path: str = "kantan_mcp_ledger.json"

    @property
    def app_base(self) -> str:
        return f"{self.cms_base_url.rstrip('/')}/v1/app"


def load_config() -> Config:
    missing = [
        k for k in ("CMS_BASE_URL", "KANTAN_MCP_KEY") if not os.environ.get(k)
    ]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    return Config(
        cms_base_url=os.environ["CMS_BASE_URL"],
        mcp_key=os.environ["KANTAN_MCP_KEY"],
        ledger_path=os.environ.get("KANTAN_MCP_LEDGER", "kantan_mcp_ledger.json"),
    )
