"""Batch: read a lead spreadsheet and provision each row. One ProvisionResult
per row — a failure on one row doesn't abort the rest. Idempotent/resumable via
the ledger (see ProvisionLeadClientUseCase), so re-running a sheet skips rows
already provisioned and resumes partial ones."""
from __future__ import annotations

from kantan_cms_mcp.applications.use_cases.provision_lead_client import (
    ProvisionLeadClientUseCase,
)
from kantan_cms_mcp.domains.entities import ProvisionResult
from kantan_cms_mcp.domains.kantan_api import KantanApi
from kantan_cms_mcp.infras.excel_reader import read_lead_clients
from kantan_cms_mcp.infras.ledger import Ledger


class ProvisionFromExcelUseCase:
    def __init__(self, api: KantanApi, ledger: Ledger):
        self._provision = ProvisionLeadClientUseCase(api, ledger)

    def execute(self, path: str) -> list[ProvisionResult]:
        leads = read_lead_clients(path)
        return [self._provision.execute(lead) for lead in leads]
