"""load_config fail-fast behavior."""
from __future__ import annotations

import pytest

from kantan_cms_mcp.config import load_config


def test_missing_env_raises(monkeypatch):
    for k in ("CMS_BASE_URL", "KANTAN_MCP_KEY"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ValueError) as exc:
        load_config()
    assert "CMS_BASE_URL" in str(exc.value)
    assert "KANTAN_MCP_KEY" in str(exc.value)


def test_loads_when_present(monkeypatch):
    monkeypatch.setenv("CMS_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("KANTAN_MCP_KEY", "mcp_abc")
    monkeypatch.delenv("KANTAN_MCP_LEDGER", raising=False)
    cfg = load_config()
    assert cfg.mcp_key == "mcp_abc"
    assert cfg.app_base == "https://api.example.test/v1/app"
