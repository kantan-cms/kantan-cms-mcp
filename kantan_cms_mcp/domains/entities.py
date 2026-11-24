"""Domain entities — plain data the use cases speak in, independent of HTTP."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LeadClient:
    """One row of the operator's lead spreadsheet."""

    name: str
    # Optional columns, best-effort from the sheet.
    project_name: str | None = None
    description: str | None = None
    brief: str | None = None
    client_email: str | None = None
    # A stable key the operator controls, used for idempotency/traceability.
    external_key: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class ProvisionResult:
    lead: LeadClient
    tenant_id: str | None = None
    project_id: str | None = None
    status: str = "ok"  # ok | skipped | error
    detail: str | None = None
