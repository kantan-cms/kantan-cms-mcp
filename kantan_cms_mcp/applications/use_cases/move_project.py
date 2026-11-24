"""Move a project to another tenant — thin wrapper over the backend's
owner-gated, hard-validated move endpoint (the backend enforces the rules)."""
from __future__ import annotations

from kantan_cms_mcp.domains.kantan_api import KantanApi


class MoveProjectUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def execute(self, project_id: str, destination_tenant_id: str) -> dict:
        return self._api.move_project(project_id, destination_tenant_id)
