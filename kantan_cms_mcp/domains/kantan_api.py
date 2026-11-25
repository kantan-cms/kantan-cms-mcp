"""The port (interface) the use cases depend on. The concrete implementation
(infras/kantan_http_client.py) talks to the backend /v1/app surface as the
signed-in user (via a per-user MCP key). Keeping this abstract lets use cases be
tested without HTTP."""
from __future__ import annotations

from typing import Any, Protocol


class KantanApi(Protocol):
    def request(self, method: str, path: str, body: dict | None = None,
                project_id: str | None = None) -> Any:
        """Call any /v1/app endpoint as the user (generic escape hatch)."""
        ...

    def get_openapi(self) -> dict:
        """The /v1/app OpenAPI document (endpoint discovery)."""
        ...

    def create_tenant(self, name: str) -> str:
        """Create a tenant (the key's user becomes its owner). Returns tenant_id."""
        ...

    def create_project(
        self, name: str, description: str | None = None, tenant_id: str | None = None
    ) -> dict:
        """Create a project. With tenant_id, create it directly in that tenant
        (the user must own it); without, the user's default tenant.
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
        """Kick off generation (needs the project's tenant to be subscribed)."""
        ...

    def get_web_baker_status(self, project_id: str, web_baker_id: str) -> str:
        """Current status: new|navigate|running|baking|done|policy|error|failed."""
        ...

    def set_web_baker_instruction(
        self, project_id: str, web_baker_id: str, instruction: dict
    ) -> None:
        """Replace a web_baker's instruction (to regenerate against new
        collections)."""
        ...

    def reset_web_baker(self, project_id: str, web_baker_id: str) -> None:
        """Reset a web_baker back to 'new' (keeps its instruction)."""
        ...

    # --- website source download / repository upload -------------------------
    def latest_web_baker_id(self, project_id: str) -> str | None:
        """The project's most recent web_baker row id (or None if it has none)."""
        ...

    def download_website_zip(self, project_id: str, web_baker_id: str) -> bytes:
        """Fetch the generated-website SOURCE (website.zip) as raw bytes."""
        ...

    def overwrite_website_zip(
        self, project_id: str, web_baker_id: str, zip_bytes: bytes
    ) -> None:
        """Replace the project's source website.zip (what a rebuild reads)."""
        ...

    def upload_repository_zip(
        self, project_id: str, name: str, zip_bytes: bytes
    ) -> None:
        """Upload a zip bundle into the project's Repository store under `name`
        (requires the Repository app to be active)."""
        ...

    def import_website_to_repository(self, project_id: str, name: str) -> dict:
        """Server-side copy of the generated website.zip into the Repository store
        under `name` (no local download; requires the Repository app)."""
        ...

    # --- website generation (web editor) -------------------------------------
    def generate_website_in_editor(
        self, project_id: str, specification: str, media_collection_id: str | None = None
    ) -> dict:
        """Generate a whole site from scratch in the Web Editor (backend proxies
        to the editor; blocks for minutes). Returns {ok, reply, changed, pages}."""
        ...
