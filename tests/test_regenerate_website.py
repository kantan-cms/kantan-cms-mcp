"""RegenerateWebsiteUseCase orchestration, against a fake KantanApi (no HTTP)."""
from __future__ import annotations

from kantan_cms_mcp.applications.use_cases.regenerate_website import (
    RegenerateWebsiteUseCase,
)


class FakeApi:
    def __init__(self, latest="wb1", statuses=None):
        self.events = []
        self._latest = latest
        self._statuses = list(statuses or ["done"])

    def latest_web_baker_id(self, project_id):
        self.events.append(("latest", project_id))
        return self._latest

    def generate_baker_instruction(self, project_id, title, description):
        self.events.append(("instruction", title))
        return {"title": title, "kantan_cms": {"content_collection": {"id": "c1"}}}

    def set_web_baker_instruction(self, project_id, web_baker_id, instruction):
        self.events.append(("set", web_baker_id, instruction["title"]))

    def reset_web_baker(self, project_id, web_baker_id):
        self.events.append(("reset", web_baker_id))

    def run_web_baker(self, project_id, web_baker_id, version="v2"):
        self.events.append(("run", web_baker_id))

    def get_web_baker_status(self, project_id, web_baker_id):
        return self._statuses.pop(0) if self._statuses else "done"


def test_regenerate_order_and_done():
    api = FakeApi(latest="wb1", statuses=["running", "done"])
    out = RegenerateWebsiteUseCase(api, poll_seconds=0).execute(
        "p-1", "Clinic", "a clinic site"
    )
    assert out == {"ok": True, "web_baker_id": "wb1", "status": "done"}
    kinds = [e[0] for e in api.events]
    # instruction rebuilt, set, reset, run — in that order
    assert kinds == ["latest", "instruction", "set", "reset", "run"]


def test_regenerate_no_existing():
    api = FakeApi(latest=None)
    out = RegenerateWebsiteUseCase(api, poll_seconds=0).execute("p-1", "Clinic")
    assert out["ok"] is False and "generate one first" in out["detail"]


def test_regenerate_surfaces_failure():
    api = FakeApi(latest="wb1", statuses=["policy"])
    out = RegenerateWebsiteUseCase(api, poll_seconds=0).execute("p-1", "Clinic")
    assert out["ok"] is False and out["status"] == "policy"
