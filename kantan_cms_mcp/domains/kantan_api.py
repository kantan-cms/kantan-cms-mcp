"""The port (interface) the use cases depend on. The concrete implementation
(infras/kantan_http_client.py) talks to the backend /v1/app surface as the
operator. Keeping this abstract lets use cases be tested without HTTP."""
from __future__ import annotations

from typing import Protocol


class KantanApi(Protocol):
    def create_tenant(self, name: str) -> str:
        """Create a tenant (the operator becomes its owner). Returns tenant_id."""
        ...

    def create_project(
        self, name: str, description: str | None = None, tenant_id: str | None = None
    ) -> dict:
        """Create a project. With tenant_id, create it directly in that tenant
        (the caller must own it); without, the operator's default tenant.
        Returns {id, tenant_id, ...}."""
        ...

    def move_project(self, project_id: str, destination_tenant_id: str) -> dict:
        """Move a project into another tenant (owner-gated, single-member)."""
        ...

    def invite_tenant_member(self, tenant_id: str, email: str, role: str) -> None:
        """Invite a user to a tenant with a role (they must accept)."""
        ...

    def generate_baker_instruction(
        self, project_id: str, title: str, description: str | None
    ) -> dict:
        """Turn a title + brief into a web-baker instruction."""
        ...

    def create_web_baker(self, project_id: str, instruction: dict) -> str:
        """Create a web_baker row for the project. Returns its id."""
        ...

    def run_web_baker(self, project_id: str, web_baker_id: str, version: str = "v2") -> None:
        """Kick off generation (needs the project to have a subscribed tenant)."""
        ...

    def get_web_baker_status(self, web_baker_id: str) -> str:
        """Current status: new|navigate|running|baking|done|policy|error|failed."""
        ...
