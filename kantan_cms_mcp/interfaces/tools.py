"""MCP tools — the interface layer (analogous to the backend's views). Each tool
builds the use case with the shared client and returns plain dicts. The client
is created lazily on first use so the server can start without credentials
(tools then raise a clear error)."""
from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache

from fastmcp import FastMCP

from kantan_cms_mcp.applications.use_cases.download_website import (
    DownloadWebsiteUseCase,
)
from kantan_cms_mcp.applications.use_cases.hand_over_client import HandOverClientUseCase
from kantan_cms_mcp.applications.use_cases.move_project import MoveProjectUseCase
from kantan_cms_mcp.applications.use_cases.provision_and_generate import (
    ProvisionAndGenerateUseCase,
)
from kantan_cms_mcp.applications.use_cases.provision_from_excel import (
    ProvisionFromExcelUseCase,
)
from kantan_cms_mcp.applications.use_cases.provision_lead_client import (
    ProvisionLeadClientUseCase,
)
from kantan_cms_mcp.applications.use_cases.publish_website_to_repository import (
    PublishWebsiteToRepositoryUseCase,
)
from kantan_cms_mcp.config import load_config
from kantan_cms_mcp.domains.entities import LeadClient
from kantan_cms_mcp.infras.excel_reader import read_lead_clients as _read_leads
from kantan_cms_mcp.infras.kantan_http_client import KantanHttpClient
from kantan_cms_mcp.infras.ledger import Ledger


@lru_cache(maxsize=1)
def _client() -> KantanHttpClient:
    return KantanHttpClient(load_config())


@lru_cache(maxsize=1)
def _ledger() -> Ledger:
    return Ledger(load_config().ledger_path)


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def read_lead_clients(path: str) -> list[dict]:
        """Parse a lead-client spreadsheet (.xlsx) into rows for review before
        provisioning. Does not create anything."""
        return [asdict(lead) for lead in _read_leads(path)]

    @mcp.tool()
    def provision_lead_client(
        name: str,
        project_name: str | None = None,
        description: str | None = None,
        client_email: str | None = None,
        external_key: str | None = None,
    ) -> dict:
        """Provision ONE lead client: create a tenant (you become owner) and the
        project inside it. Idempotent — pass a stable external_key (else the name
        is used) so re-runs skip/resume instead of duplicating. Returns the
        tenant/project ids (or an error detail)."""
        lead = LeadClient(
            name=name,
            project_name=project_name,
            description=description,
            client_email=client_email,
            external_key=external_key,
        )
        return asdict(ProvisionLeadClientUseCase(_client(), _ledger()).execute(lead))

    @mcp.tool()
    def provision_from_excel(path: str) -> list[dict]:
        """Provision every row of a lead spreadsheet. One result per row; a failed
        row doesn't stop the others. Idempotent/resumable via the ledger, so
        re-running a sheet skips rows already provisioned."""
        results = ProvisionFromExcelUseCase(_client(), _ledger()).execute(path)
        return [asdict(r) for r in results]

    @mcp.tool()
    def provision_and_generate(
        name: str,
        brief: str,
        project_name: str | None = None,
        description: str | None = None,
        external_key: str | None = None,
    ) -> dict:
        """Provision a lead AND generate their website end-to-end: create a tenant
        + project and generate in place. Blocks until generation finishes (minutes)
        or times out. The tenant must have an active subscription to generate
        (a brand-new one does not) — otherwise the result reports "no active
        subscription". Idempotent and resumable via the ledger — a re-run continues
        from the last stage."""
        lead = LeadClient(
            name=name,
            project_name=project_name,
            description=description,
            brief=brief,
            external_key=external_key,
        )
        return asdict(ProvisionAndGenerateUseCase(_client(), _ledger()).execute(lead))

    @mcp.tool()
    def move_project(project_id: str, destination_tenant_id: str) -> dict:
        """Move a project into another tenant. The backend enforces owner-of-both,
        single-member, and member-in-destination; it fails with a clear message
        otherwise."""
        return MoveProjectUseCase(_client()).execute(project_id, destination_tenant_id)

    @mcp.tool()
    def download_website(
        project_id: str, out_path: str, web_baker_id: str | None = None
    ) -> dict:
        """Download a project's generated-website SOURCE (website.zip) to a local
        file so you can edit its "taste" with external tools. Defaults to the
        project's most recent generation; pass web_baker_id to pick a specific
        one. Returns {path, bytes, web_baker_id}."""
        return DownloadWebsiteUseCase(_client()).execute(
            project_id, out_path, web_baker_id
        )

    @mcp.tool()
    def upload_website_to_repository(
        project_id: str,
        zip_path: str,
        name: str = "website.zip",
        set_as_source: bool = False,
    ) -> dict:
        """Upload an (edited) website zip into the project's Repository store under
        `name`. Set set_as_source=True to also make it the project's source so the
        next build/deploy uses the edits. Requires the Repository app to be active
        on the project (fails with a clear message otherwise)."""
        return PublishWebsiteToRepositoryUseCase(_client()).from_local_zip(
            project_id, zip_path, name, set_as_source
        )

    @mcp.tool()
    def import_generated_website_to_repository(
        project_id: str, name: str = "website.zip"
    ) -> dict:
        """Copy the project's CURRENT generated website.zip straight into its
        Repository store (server-side, no local download). Use this to seed the
        repository from a freshly generated site. Requires the Repository app."""
        return PublishWebsiteToRepositoryUseCase(_client()).import_generated(
            project_id, name
        )

    @mcp.tool()
    def hand_over_client(tenant_id: str, client_email: str, role: str = "owner") -> dict:
        """Invite the paying client to their tenant (they must accept before the
        role applies)."""
        return HandOverClientUseCase(_client()).execute(tenant_id, client_email, role)
