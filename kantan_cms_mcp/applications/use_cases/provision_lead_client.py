"""Provision one lead client: create a tenant (operator = owner), create the
project, and move it into the new tenant.

Why create-then-move: the backend's create-project places the project in the
operator's *default* tenant (it has no tenant_id parameter). Moving it into the
freshly-created tenant lands it in the right place and reuses the owner-gated,
single-member move (the operator is the sole member and owns both tenants, so
the move's hard checks pass). A dedicated tenant_id on create-project would let
us skip the move — tracked as a backend improvement.
"""
from __future__ import annotations

from kantan_cms_mcp.domains.entities import LeadClient, ProvisionResult
from kantan_cms_mcp.domains.kantan_api import KantanApi


class ProvisionLeadClientUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def execute(self, lead: LeadClient) -> ProvisionResult:
        result = ProvisionResult(lead=lead)
        try:
            tenant_id = self._api.create_tenant(lead.name)
            result.tenant_id = tenant_id

            project = self._api.create_project(
                name=lead.project_name or lead.name,
                description=lead.description,
            )
            project_id = project["id"]
            result.project_id = project_id

            # Relocate the project from the operator's default tenant into the
            # client's new tenant (no-op if it already landed there).
            if project.get("tenant_id") != tenant_id:
                self._api.move_project(project_id, tenant_id)

            result.status = "ok"
        except Exception as e:  # surface, don't abort the whole batch
            result.status = "error"
            result.detail = str(e)
        return result
