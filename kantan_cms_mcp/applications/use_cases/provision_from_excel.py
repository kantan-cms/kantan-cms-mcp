"""Batch: read a lead spreadsheet and provision each row. One ProvisionResult
per row — a failure on one row doesn't abort the rest, so the operator can fix
and re-run. (Re-running currently re-creates; idempotency by external_key is a
planned enhancement — see README.)"""
from __future__ import annotations

from kantan_cms_mcp.applications.use_cases.provision_lead_client import (
    ProvisionLeadClientUseCase,
)
from kantan_cms_mcp.domains.entities import ProvisionResult
from kantan_cms_mcp.domains.kantan_api import KantanApi
from kantan_cms_mcp.infras.excel_reader import read_lead_clients


class ProvisionFromExcelUseCase:
    def __init__(self, api: KantanApi):
        self._provision = ProvisionLeadClientUseCase(api)

    def execute(self, path: str) -> list[ProvisionResult]:
        leads = read_lead_clients(path)
        return [self._provision.execute(lead) for lead in leads]
