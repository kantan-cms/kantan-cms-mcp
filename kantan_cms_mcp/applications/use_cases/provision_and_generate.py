"""Provision a lead client AND generate their website, then hand the finished
project to the lead's tenant.

A brand-new lead tenant has no subscription, so it cannot run the generator. We
therefore build in the OPERATOR's (subscribed) tenant and relocate the result:

  create lead tenant (destination, operator = owner)
  create project in the OPERATOR's default tenant   (has credits to generate)
  instruction (AI) -> web_baker row -> run (v2)
  poll until done
  move_project into the lead's tenant               (owner-gated, single-member)

Idempotent/resumable via the ledger, keyed by external_key (else name): each
stage is checkpointed so a re-run picks up where it stopped and never duplicates
tenants/projects. Generation bills to the operator (you sell the site upfront).
"""
from __future__ import annotations

import time

from kantan_cms_mcp.domains.entities import LeadClient, ProvisionResult
from kantan_cms_mcp.domains.kantan_api import KantanApi
from kantan_cms_mcp.infras.ledger import Ledger

_DONE = "done"
_TERMINAL_FAIL = {"error", "failed", "policy"}


class ProvisionAndGenerateUseCase:
    def __init__(self, api: KantanApi, ledger: Ledger, poll_seconds: int = 10,
                 timeout_seconds: int = 900):
        self._api = api
        self._ledger = ledger
        self._poll = poll_seconds
        self._timeout = timeout_seconds

    def execute(self, lead: LeadClient) -> ProvisionResult:
        key = lead.external_key or lead.name
        state = self._ledger.get(key)
        result = ProvisionResult(
            lead=lead, tenant_id=state.get("tenant_id"), project_id=state.get("project_id")
        )

        if state.get("moved"):
            result.status = "skipped"
            result.detail = "already provisioned + generated"
            return result

        try:
            # 1. Destination tenant for the lead (operator becomes owner).
            tenant_id = state.get("tenant_id") or self._api.create_tenant(lead.name)
            result.tenant_id = tenant_id
            self._checkpoint(key, state, tenant_id=tenant_id)

            # 2. Project in the OPERATOR's default tenant (it has credits).
            project_id = state.get("project_id")
            if not project_id:
                project = self._api.create_project(
                    name=lead.project_name or lead.name, description=lead.description
                )
                project_id = project["id"]
            result.project_id = project_id
            self._checkpoint(key, state, project_id=project_id)

            # 3. Generate (instruction -> web_baker -> run), unless already done.
            if not state.get("generated"):
                wb_id = state.get("web_baker_id")
                if not wb_id:
                    instruction = self._api.generate_baker_instruction(
                        project_id, lead.project_name or lead.name, lead.brief or lead.description
                    )
                    wb_id = self._api.create_web_baker(project_id, instruction)
                    self._checkpoint(key, state, web_baker_id=wb_id)
                    self._api.run_web_baker(project_id, wb_id)
                self._wait_for_done(wb_id)
                self._checkpoint(key, state, generated=True)

            # 4. Relocate the finished project into the lead's tenant.
            self._api.move_project(project_id, tenant_id)
            self._checkpoint(key, state, moved=True)

            result.status = "ok"
        except Exception as e:  # surface; batch continues
            result.status = "error"
            result.detail = str(e)
        return result

    def _wait_for_done(self, web_baker_id: str) -> None:
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            status = self._api.get_web_baker_status(web_baker_id)
            if status == _DONE:
                return
            if status in _TERMINAL_FAIL:
                raise RuntimeError(f"Generation {status}")
            time.sleep(self._poll)
        raise TimeoutError("Generation timed out")

    def _checkpoint(self, key: str, state: dict, **updates) -> None:
        state.update(updates)
        self._ledger.put(key, state)
