"""The port (interface) the use cases depend on. The concrete implementation
(infras/kantan_http_client.py) talks to the backend /v1/app surface as the
operator. Keeping this abstract lets use cases be tested without HTTP."""
from __future__ import annotations

from typing import Protocol


class KantanApi(Protocol):
    def create_tenant(self, name: str) -> str:
        """Create a tenant (the operator becomes its owner). Returns tenant_id."""
        ...

    def create_project(self, name: str, description: str | None = None) -> dict:
        """Create a project. NOTE: the backend places it in the operator's
        default tenant; callers move it with move_project. Returns {id, tenant_id}."""
        ...

    def move_project(self, project_id: str, destination_tenant_id: str) -> dict:
        """Move a project into another tenant (owner-gated, single-member)."""
        ...

    def invite_tenant_member(self, tenant_id: str, email: str, role: str) -> None:
        """Invite a user to a tenant with a role (they must accept)."""
        ...
