"""Runtime configuration (environment). The MCP acts as a single OPERATOR
account — it holds that account's Supabase credentials and calls the backend's
user-JWT surface (/v1/app). It is NOT a multi-tenant/user service and must not
be exposed to end users."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    cms_base_url: str  # e.g. https://api.kantan-cms.dev
    supabase_url: str
    supabase_anon_key: str
    operator_email: str
    operator_password: str
    # Idempotency ledger file (local). Override with KANTAN_MCP_LEDGER.
    ledger_path: str = "kantan_mcp_ledger.json"

    @property
    def app_base(self) -> str:
        return f"{self.cms_base_url.rstrip('/')}/v1/app"


def load_config() -> Config:
    missing = [
        k
        for k in (
            "CMS_BASE_URL",
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "KANTAN_OPERATOR_EMAIL",
            "KANTAN_OPERATOR_PASSWORD",
        )
        if not os.environ.get(k)
    ]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    return Config(
        cms_base_url=os.environ["CMS_BASE_URL"],
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_anon_key=os.environ["SUPABASE_ANON_KEY"],
        operator_email=os.environ["KANTAN_OPERATOR_EMAIL"],
        operator_password=os.environ["KANTAN_OPERATOR_PASSWORD"],
        ledger_path=os.environ.get("KANTAN_MCP_LEDGER", "kantan_mcp_ledger.json"),
    )
