"""Provision one lead client: create a tenant (operator = owner) and the project
directly inside it (create-project with tenant_id).

Idempotent + resumable via the ledger, keyed by external_key (else name):
  - already has a project recorded  -> skipped
  - has a tenant but no project yet  -> resume (reuse the tenant, create project)
  - nothing recorded                 -> create tenant (checkpoint) then project
So a re-run after a partial failure never creates duplicate tenants.
"""
from __future__ import annotations

from kantan_cms_mcp.domains.entities import LeadClient, ProvisionResult
from kantan_cms_mcp.domains.kantan_api import KantanApi
from kantan_cms_mcp.infras.ledger import Ledger


class ProvisionLeadClientUseCase:
    def __init__(self, api: KantanApi, ledger: Ledger):
        self._api = api
        self._ledger = ledger

    def execute(self, lead: LeadClient) -> ProvisionResult:
        key = lead.external_key or lead.name
        recorded = self._ledger.get(key)

        if recorded.get("project_id"):
            return ProvisionResult(
                lead=lead,
                tenant_id=recorded.get("tenant_id"),
                project_id=recorded.get("project_id"),
                status="skipped",
                detail="already provisioned",
            )

        result = ProvisionResult(lead=lead)
        try:
            tenant_id = recorded.get("tenant_id")
            if not tenant_id:
                tenant_id = self._api.create_tenant(lead.name)
                self._ledger.put(key, {"tenant_id": tenant_id})  # checkpoint
            result.tenant_id = tenant_id

            project = self._api.create_project(
                name=lead.project_name or lead.name,
                description=lead.description,
                tenant_id=tenant_id,
            )
            result.project_id = project["id"]
            self._ledger.put(key, {"tenant_id": tenant_id, "project_id": result.project_id})
            result.status = "ok"
        except Exception as e:  # surface; don't abort the batch
            result.status = "error"
            result.detail = str(e)
            result.tenant_id = result.tenant_id or recorded.get("tenant_id")
        return result
