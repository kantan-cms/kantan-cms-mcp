"""MCP tools — the interface layer (analogous to the backend's views). Each tool
builds the use case with the shared client and returns plain dicts. The client
is created lazily on first use so the server can start without credentials
(tools then raise a clear error)."""
from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache

from fastmcp import FastMCP

from kantan_cms_mcp.applications.use_cases.api_access import ApiAccessUseCase
from kantan_cms_mcp.applications.use_cases.download_website import (
    DownloadWebsiteUseCase,
)
from kantan_cms_mcp.applications.use_cases.generate_images_to_collection import (
    GenerateImagesToCollectionUseCase,
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
from kantan_cms_mcp.applications.use_cases.regenerate_website import (
    RegenerateWebsiteUseCase,
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
    def regenerate_website(
        project_id: str,
        title: str,
        description: str | None = None,
        web_baker_id: str | None = None,
    ) -> dict:
        """Regenerate an existing project's website against its CURRENT
        collections (a project has one web_baker, so you can't create another).
        Rebuilds the instruction, resets, re-runs, and blocks to completion.
        Use this instead of POST /web_baker/ (which 400s when one exists). The
        tenant must have an active subscription to generate."""
        return RegenerateWebsiteUseCase(_client()).execute(
            project_id, title, description, web_baker_id
        )

    @mcp.tool()
    def reset_website(project_id: str, web_baker_id: str) -> object:
        """Reset a web_baker back to 'new' (keeps its instruction). Pair with
        run_website to re-run the stored instruction."""
        ApiAccessUseCase(_client()).call(
            "POST", f"/web_baker/{web_baker_id}/reset", project_id=project_id
        )
        return {"ok": True}

    @mcp.tool()
    def run_website(project_id: str, web_baker_id: str, version: str = "v2") -> object:
        """Kick off generation for an existing web_baker (needs an active
        subscription on the tenant)."""
        return ApiAccessUseCase(_client()).call(
            "POST", f"/web_baker/{web_baker_id}/run",
            {"version": version}, project_id,
        )

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

    # --- flexible API access ------------------------------------------------
    @mcp.tool()
    def list_api_endpoints() -> list[dict]:
        """Discover what `kantan_request` can reach: every /v1/app endpoint as
        {method, path, summary}. Call this first when you need an operation that
        has no dedicated tool below."""
        return ApiAccessUseCase(_client()).endpoints()

    @mcp.tool()
    def kantan_request(
        method: str,
        path: str,
        body: dict | None = None,
        project_id: str | None = None,
    ) -> object:
        """Call ANY Kantan /v1/app endpoint as the signed-in user — the escape
        hatch for anything without a dedicated tool. `path` is relative to
        /v1/app (e.g. "/collections", "/installations/"); pass project_id for
        project-scoped endpoints (it becomes the X-Project-Id header). Use
        list_api_endpoints to discover paths. Returns parsed JSON."""
        return ApiAccessUseCase(_client()).call(method, path, body, project_id)

    @mcp.tool()
    def list_collections(project_id: str) -> object:
        """List a project's collections."""
        return ApiAccessUseCase(_client()).list_collections(project_id)

    @mcp.tool()
    def create_collection(
        project_id: str,
        name: str,
        type: str,
        description: str | None = None,
        icon: str | None = None,
    ) -> object:
        """Create a collection. `type` is one of blog|form|media|dict|custom;
        default fields for that type are seeded automatically, so the collection
        is immediately usable (e.g. for website generation)."""
        return ApiAccessUseCase(_client()).create_collection(
            project_id, name, type, description, icon
        )

    @mcp.tool()
    def update_collection(
        project_id: str,
        collection_id: str,
        name: str | None = None,
        description: str | None = None,
        icon: str | None = None,
    ) -> object:
        """Update a collection's name/description/icon (its type is immutable)."""
        return ApiAccessUseCase(_client()).update_collection(
            project_id, collection_id, name, description, icon
        )

    @mcp.tool()
    def delete_collection(project_id: str, collection_id: str) -> object:
        """Delete a collection — its fields and records go with it (DB cascade)."""
        return ApiAccessUseCase(_client()).delete_collection(project_id, collection_id)

    # --- collection schema (fields) -----------------------------------------
    @mcp.tool()
    def list_fields(project_id: str, collection_id: str) -> object:
        """List a collection's fields (schema). Each has id, name, type,
        custom_key, required, order, etc."""
        return ApiAccessUseCase(_client()).list_fields(project_id, collection_id)

    @mcp.tool()
    def add_field(
        project_id: str,
        collection_id: str,
        name: str,
        type: str,
        key: str | None = None,
        required: bool = False,
        order: int | None = None,
        default_value: object | None = None,
        attr: dict | None = None,
    ) -> object:
        """Add a field to a collection. `type` is a CMS field type (text,
        textarea, markdown, tags, datetime, file, dict, number, …). `key` is the
        machine key (derived from name if omitted). For select/tag fields put
        options in `attr`. Appended unless `order` is given."""
        return ApiAccessUseCase(_client()).add_field(
            project_id, collection_id, name, type, key, required, order,
            default_value, attr,
        )

    @mcp.tool()
    def update_field(
        project_id: str,
        collection_id: str,
        field_id: str,
        name: str | None = None,
        type: str | None = None,
        required: bool | None = None,
        order: int | None = None,
        visible: bool | None = None,
        default_value: object | None = None,
        attr: dict | None = None,
    ) -> object:
        """Update a field (field_id from list_fields). Only provided attrs
        change."""
        return ApiAccessUseCase(_client()).update_field(
            project_id, collection_id, field_id, name, type, required, order,
            visible, default_value, attr,
        )

    @mcp.tool()
    def delete_field(project_id: str, collection_id: str, field_id: str) -> object:
        """Delete a field from a collection (field_id from list_fields)."""
        return ApiAccessUseCase(_client()).delete_field(
            project_id, collection_id, field_id
        )

    @mcp.tool()
    def list_records(
        project_id: str,
        collection_id: str,
        page_size: int = 100,
        page_num: int = 1,
    ) -> object:
        """List records in a collection (paginated)."""
        return ApiAccessUseCase(_client()).list_records(
            project_id, collection_id, page_size, page_num
        )

    @mcp.tool()
    def generate_images_to_collection(
        project_id: str,
        collection_id: str,
        prompts: list[str],
        aspect_ratio: str = "1:1",
    ) -> dict:
        """Generate images from `prompts` (one image each, max 10 per call) and
        store them as records in a MEDIA collection, so they show up like any
        uploaded media and can be referenced by the site generator.

        The backend reuses its own image model (Gemini); each image is uploaded
        to the content store and a media record is created pointing at it.
        `aspect_ratio` applies to all prompts (e.g. "1:1", "16:9", "4:3").
        Blocks until all images are generated (seconds each) and bills the
        project's tenant per image. The collection must be of type `media`.
        Returns { images: [{ id, url, prompt }] }."""
        return GenerateImagesToCollectionUseCase(_client()).execute(
            project_id, collection_id, prompts, aspect_ratio
        )

    @mcp.tool()
    def get_record(project_id: str, collection_id: str, record_id: str) -> object:
        """Fetch one record by id."""
        return ApiAccessUseCase(_client()).get_record(
            project_id, collection_id, record_id
        )

    @mcp.tool()
    def create_record(project_id: str, collection_id: str, data: dict) -> object:
        """Create a record in a collection. `data` is a flat map of field
        custom_key -> value (match the collection's fields)."""
        return ApiAccessUseCase(_client()).create_record(
            project_id, collection_id, data
        )

    @mcp.tool()
    def update_record(
        project_id: str, collection_id: str, record_id: str, data: dict
    ) -> object:
        """Update a record. `data` holds the fields to change (field
        custom_key -> value)."""
        return ApiAccessUseCase(_client()).update_record(
            project_id, collection_id, record_id, data
        )

    @mcp.tool()
    def delete_record(project_id: str, collection_id: str, record_id: str) -> object:
        """Delete a record by id."""
        return ApiAccessUseCase(_client()).delete_record(
            project_id, collection_id, record_id
        )

    @mcp.tool()
    def bulk_create_records(
        project_id: str, collection_id: str, records: list
    ) -> object:
        """Create many records at once. `records` is a list of flat field maps
        (custom_key -> value). Faster than one-by-one; does NOT fire per-record
        app events."""
        return ApiAccessUseCase(_client()).bulk_create_records(
            project_id, collection_id, records
        )

    @mcp.tool()
    def bulk_update_records(
        project_id: str, collection_id: str, records: list
    ) -> object:
        """Update many records at once. `records` is a list of
        {"id": <record_id>, "data": {field: value}}. Does NOT fire events."""
        return ApiAccessUseCase(_client()).bulk_update_records(
            project_id, collection_id, records
        )

    @mcp.tool()
    def bulk_delete_records(
        project_id: str, collection_id: str, ids: list
    ) -> object:
        """Delete many records by id in one call. Does NOT fire events."""
        return ApiAccessUseCase(_client()).bulk_delete_records(
            project_id, collection_id, ids
        )

    @mcp.tool()
    def list_apps(project_id: str) -> object:
        """The installable app catalog (app ids + metadata)."""
        return ApiAccessUseCase(_client()).list_apps(project_id)

    @mcp.tool()
    def list_installed_apps(project_id: str) -> object:
        """Apps currently installed on the project."""
        return ApiAccessUseCase(_client()).list_installed_apps(project_id)

    @mcp.tool()
    def install_app(
        project_id: str, app_id: str, config: dict | None = None
    ) -> object:
        """Install an app on the project. Pass `config` to set the installation's
        settings in the same step (otherwise configure later with configure_app).
        app_id comes from list_apps."""
        return ApiAccessUseCase(_client()).install_app(project_id, app_id, config)

    @mcp.tool()
    def activate_website_app(project_id: str, mode: str) -> object:
        """Activate the Website Editor app in a specific mode via MCP (no in-app
        chooser). mode = 'generator' (Created by Website Generator) or 'editor'
        (Designed by Website Editor). Installs if needed and sets the mode;
        idempotent (reuses an existing install)."""
        return ApiAccessUseCase(_client()).activate_website_app(project_id, mode)

    @mcp.tool()
    def configure_app(project_id: str, installation_id: str, config: dict) -> object:
        """Set an installed app's settings (installation_id from
        list_installed_apps; config shape per the app's settings schema)."""
        return ApiAccessUseCase(_client()).configure_app(
            project_id, installation_id, config
        )

    @mcp.tool()
    def uninstall_app(project_id: str, installation_id: str) -> object:
        """Remove an installed app from the project."""
        return ApiAccessUseCase(_client()).uninstall_app(project_id, installation_id)

    # --- hosting / deploy / preview -----------------------------------------
    @mcp.tool()
    def deploy_to_preview(project_id: str, web_baker_id: str) -> object:
        """Publish the generated build to the project's preview site
        (web_baker_id from list_api_endpoints/the generation result or
        latest_web_baker_id)."""
        return ApiAccessUseCase(_client()).deploy_to_preview(project_id, web_baker_id)

    @mcp.tool()
    def deploy_to_live(project_id: str) -> object:
        """Promote the current preview to the live/production host."""
        return ApiAccessUseCase(_client()).deploy_to_live(project_id)

    @mcp.tool()
    def enable_hosting(
        project_id: str, enabled: bool = True, url: str | None = None
    ) -> object:
        """Enable (or disable) hosting for the project and optionally set its
        URL — what the console's Hosting Settings toggle does. Pass enabled=False
        to turn hosting off. (Deploying also serves the site; this flips the
        hosting-enabled setting explicitly.)"""
        return ApiAccessUseCase(_client()).set_hosting(project_id, enabled, url)

    @mcp.tool()
    def get_hosting_status(project_id: str, web_baker_id: str) -> object:
        """Hosting status + live URL for the project's build."""
        return ApiAccessUseCase(_client()).get_hosting_status(project_id, web_baker_id)

    @mcp.tool()
    def delete_preview(project_id: str) -> object:
        """Tear down the preview site (production hosting untouched)."""
        return ApiAccessUseCase(_client()).delete_preview(project_id)

    @mcp.tool()
    def delete_hosting(project_id: str) -> object:
        """Tear down live hosting (Cloudflare domain settings are kept so you
        can redeploy without re-registering)."""
        return ApiAccessUseCase(_client()).delete_hosting(project_id)

    # --- custom domain (CNAME / TXT validation) -----------------------------
    @mcp.tool()
    def set_custom_domain(project_id: str, hostname: str) -> object:
        """Register a custom domain for the project. Returns the Cloudflare
        settings, including the TXT validation records to add to DNS. After the
        customer adds the records, poll get_domain_status to confirm."""
        return ApiAccessUseCase(_client()).set_custom_domain(project_id, hostname)

    @mcp.tool()
    def list_custom_hostnames(project_id: str) -> object:
        """List the project's custom hostnames and their SSL/validation status."""
        return ApiAccessUseCase(_client()).list_custom_hostnames(project_id)

    @mcp.tool()
    def get_domain_status(project_id: str, hostname_id: str) -> object:
        """Live domain/SSL status, including the TXT ownership_verification and
        ssl.validation_records the customer must add to DNS to validate."""
        return ApiAccessUseCase(_client()).get_domain_status(project_id, hostname_id)

    # --- project membership -------------------------------------------------
    @mcp.tool()
    def list_project_members(project_id: str) -> object:
        """List the users attached to a project."""
        return ApiAccessUseCase(_client()).list_project_members(project_id)

    @mcp.tool()
    def list_project_roles(project_id: str) -> object:
        """List assignable project roles (id + name)."""
        return ApiAccessUseCase(_client()).list_project_roles(project_id)

    @mcp.tool()
    def connect_user_to_project(project_id: str, user_id: str) -> object:
        """Add an existing tenant member to the project (as 'member'; change with
        set_project_member_role). The user must already belong to the project's
        tenant. Subject to the backend's role checks."""
        return ApiAccessUseCase(_client()).connect_user_to_project(project_id, user_id)

    @mcp.tool()
    def set_project_member_role(
        project_id: str, project_user_id: str, project_role_id: str
    ) -> object:
        """Change a project member's role (ids from list_project_members /
        list_project_roles)."""
        return ApiAccessUseCase(_client()).set_project_member_role(
            project_id, project_user_id, project_role_id
        )

    @mcp.tool()
    def remove_project_member(project_id: str, project_user_id: str) -> object:
        """Remove a user from a project (project_user_id from
        list_project_members)."""
        return ApiAccessUseCase(_client()).remove_project_member(
            project_id, project_user_id
        )

    # --- project settings ---------------------------------------------------
    @mcp.tool()
    def update_project(
        project_id: str, name: str | None = None, description: str | None = None
    ) -> object:
        """Update a project's name and/or description (members only)."""
        return ApiAccessUseCase(_client()).update_project(
            project_id, name, description
        )

    @mcp.tool()
    def get_notifications(project_id: str) -> object:
        """Read the project's notification settings (email + form_submissions)."""
        return ApiAccessUseCase(_client()).get_notifications(project_id)

    @mcp.tool()
    def set_notifications(
        project_id: str,
        email: str | None = None,
        form_submissions: bool | None = None,
    ) -> object:
        """Set notification settings — the form-submission notification email
        and/or whether form submissions notify. Only provided fields change."""
        return ApiAccessUseCase(_client()).set_notifications(
            project_id, email, form_submissions
        )

    @mcp.tool()
    def get_feature_toggles(project_id: str) -> object:
        """Read the project's feature toggles (disabled app/category list)."""
        return ApiAccessUseCase(_client()).get_feature_toggles(project_id)

    @mcp.tool()
    def set_feature_toggles(project_id: str, disabled_categories: list) -> object:
        """Set the project's disabled feature categories (full list; everything
        not listed is enabled)."""
        return ApiAccessUseCase(_client()).set_feature_toggles(
            project_id, disabled_categories
        )

    # --- API keys + build env (vault) + build -------------------------------
    @mcp.tool()
    def create_api_key(
        project_id: str,
        name: str,
        permissions: list | None = None,
        expires_at: str | None = None,
    ) -> object:
        """Generate a project API key (for /v1/api + /v1/public). Returns the raw
        token ONCE (the backend stores only its hash). permissions default to
        ["*"]; pass narrower scopes (e.g. ["records:read"]) for least privilege."""
        return ApiAccessUseCase(_client()).create_api_key(
            project_id, name, permissions, expires_at
        )

    @mcp.tool()
    def list_env_vars(project_id: str) -> object:
        """List the project's build env vars (secret values are write-only)."""
        return ApiAccessUseCase(_client()).list_env_vars(project_id)

    @mcp.tool()
    def set_env_var(
        project_id: str, key: str, value: str, secret: bool = False
    ) -> object:
        """Set a project env var the website build injects at build time
        (secret=True stores it write-only, e.g. for an API key)."""
        return ApiAccessUseCase(_client()).set_env_var(
            project_id, key, value, secret
        )

    @mcp.tool()
    def delete_env_var(project_id: str, key: str) -> object:
        """Delete a project build env var."""
        return ApiAccessUseCase(_client()).delete_env_var(project_id, key)

    @mcp.tool()
    def configure_site_env(
        project_id: str, key_name: str = "website-build"
    ) -> object:
        """One-shot: create an API key and store CMS_API_KEY (secret) + PROJECT_ID
        in the build vault, so a generated/base website can read the CMS. The
        builder injects these at build time. Returns the key ONCE. (CMS_BASE_URL
        is not set — the site defaults it; use set_env_var if you need it.)"""
        return ApiAccessUseCase(_client()).configure_site_env(project_id, key_name)

    @mcp.tool()
    def build_from_repository(
        project_id: str,
        bundle: str,
        runtime: str = "node22",
        script_file: str = "build.sh",
    ) -> object:
        """Trigger a Kantan Builder build from a Repository-app zip bundle
        (requires the Repository app active). `bundle` is the stored zip name
        (see the repository list). Follow with deploy_to_live to publish."""
        return ApiAccessUseCase(_client()).build_from_repository(
            project_id, bundle, runtime, script_file
        )

    @mcp.tool()
    def hand_over_client(tenant_id: str, client_email: str, role: str = "owner") -> dict:
        """Invite the paying client to their tenant (they must accept before the
        role applies)."""
        return HandOverClientUseCase(_client()).execute(tenant_id, client_email, role)
