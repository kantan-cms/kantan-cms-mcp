"""Regenerate an existing project's website against its CURRENT collections.

A project has at most one web_baker, so you can't just create another. This
rebuilds the instruction from the project's current collections (so a site made
on an empty project now wires in the blog/form collections), replaces the stored
instruction, resets, and re-runs — then polls to completion.
"""
from __future__ import annotations

import time

from kantan_cms_mcp.domains.kantan_api import KantanApi

_DONE = "done"
_TERMINAL_FAIL = {"error", "failed", "policy"}


class RegenerateWebsiteUseCase:
    def __init__(self, api: KantanApi, poll_seconds: int = 10,
                 timeout_seconds: int = 900):
        self._api = api
        self._poll = poll_seconds
        self._timeout = timeout_seconds

    def execute(self, project_id: str, title: str, description: str | None = None,
                web_baker_id: str | None = None, wait: bool = True) -> dict:
        wb_id = web_baker_id or self._api.latest_web_baker_id(project_id)
        if not wb_id:
            return {
                "ok": False,
                "detail": "No existing website to regenerate; generate one first.",
            }
        # Rebuild the instruction from the project's current collections.
        instruction = self._api.generate_baker_instruction(
            project_id, title, description
        )
        self._api.set_web_baker_instruction(project_id, wb_id, instruction)
        self._api.reset_web_baker(project_id, wb_id)
        self._api.run_web_baker(project_id, wb_id)

        result = {"ok": True, "web_baker_id": wb_id}
        if not wait:
            result["status"] = "running"
            return result

        deadline = time.time() + self._timeout
        while time.time() < deadline:
            status = self._api.get_web_baker_status(project_id, wb_id)
            if status == _DONE:
                result["status"] = _DONE
                return result
            if status in _TERMINAL_FAIL:
                result["ok"] = False
                result["status"] = status
                result["detail"] = f"Generation {status}"
                return result
            time.sleep(self._poll)
        result["ok"] = False
        result["status"] = "timeout"
        result["detail"] = "Generation timed out"
        return result
