"""Flexible access to the Kantan /v1/app surface.

A generic `call` (the escape hatch to any endpoint) + `endpoints` discovery, plus
thin convenience wrappers for the common content/app operations so the AI
doesn't have to hand-build those calls. Everything runs as the key's user, so
reach == that user's own account."""
from __future__ import annotations

import secrets
from typing import Any

from kantan_cms_mcp.domains.kantan_api import KantanApi


class ApiAccessUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    # --- generic ----------------------------------------------------------
    def call(self, method: str, path: str, body: dict | None = None,
             project_id: str | None = None) -> Any:
        return self._api.request(method, path, body, project_id)

    def endpoints(self) -> list[dict]:
        """Compact list of {method, path, summary} from the OpenAPI doc, so the
        AI can discover what `call` can reach."""
        doc = self._api.get_openapi()
        out: list[dict] = []
        for path, ops in (doc.get("paths") or {}).items():
            for method, op in ops.items():
                if method.lower() not in (
                    "get", "post", "put", "patch", "delete"
                ):
                    continue
                out.append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "summary": (op or {}).get("summary")
                        or (op or {}).get("operationId")
                        or "",
                    }
                )
        out.sort(key=lambda e: (e["path"], e["method"]))
        return out

    # --- collections / records -------------------------------------------
    def list_collections(self, project_id: str) -> Any:
        return self._api.request("GET", "/collections/", project_id=project_id)

    def create_collection(self, project_id: str, name: str, type: str,
                          description: str | None = None,
                          icon: str | None = None) -> Any:
        # Creating a collection auto-seeds the default fields for its type
        # (blog/form/media/dict/custom), so the result is immediately usable.
        body = {"name": name, "type": type, "description": description, "icon": icon}
        return self._api.request("POST", "/collections", body, project_id)

    def update_collection(self, project_id: str, collection_id: str,
                          name: str | None = None, description: str | None = None,
                          icon: str | None = None) -> Any:
        body = {
            k: v for k, v in
            {"name": name, "description": description, "icon": icon}.items()
            if v is not None
        }
        return self._api.request(
            "PATCH", f"/collections/{collection_id}", body, project_id
        )

    def delete_collection(self, project_id: str, collection_id: str) -> Any:
        # Removes the collection and (by DB cascade) its fields + records.
        return self._api.request(
            "DELETE", f"/collections/{collection_id}", project_id=project_id
        )

    def list_records(self, project_id: str, collection_id: str,
                     page_size: int = 100, page_num: int = 1) -> Any:
        path = (
            f"/collections/{collection_id}/records/"
            f"?page_size={page_size}&page_num={page_num}"
        )
        return self._api.request("GET", path, project_id=project_id)

    def get_record(self, project_id: str, collection_id: str,
                   record_id: str) -> Any:
        return self._api.request(
            "GET", f"/collections/{collection_id}/records/{record_id}",
            project_id=project_id,
        )

    def create_record(self, project_id: str, collection_id: str,
                      data: dict) -> Any:
        # `data` is a flat map of field custom_key -> value.
        return self._api.request(
            "POST", f"/collections/{collection_id}/records/", data, project_id
        )

    def update_record(self, project_id: str, collection_id: str,
                      record_id: str, data: dict) -> Any:
        return self._api.request(
            "PATCH", f"/collections/{collection_id}/records/{record_id}",
            data, project_id,
        )

    def delete_record(self, project_id: str, collection_id: str,
                      record_id: str) -> Any:
        return self._api.request(
            "DELETE", f"/collections/{collection_id}/records/{record_id}",
            project_id=project_id,
        )

    # --- bulk records (no per-record app events fired) --------------------
    def bulk_create_records(self, project_id: str, collection_id: str,
                            records: list) -> Any:
        return self._api.request(
            "POST", f"/collections/{collection_id}/records/bulk",
            {"records": records}, project_id,
        )

    def bulk_update_records(self, project_id: str, collection_id: str,
                            records: list) -> Any:
        # records: [{"id": "...", "data": {field: value}}, ...]
        return self._api.request(
            "PATCH", f"/collections/{collection_id}/records/bulk",
            {"records": records}, project_id,
        )

    def bulk_delete_records(self, project_id: str, collection_id: str,
                            ids: list) -> Any:
        return self._api.request(
            "POST", f"/collections/{collection_id}/records/bulk/delete",
            {"ids": ids}, project_id,
        )

    # --- hosting / deploy / preview --------------------------------------
    def deploy_to_preview(self, project_id: str, web_baker_id: str) -> Any:
        """Publish the generated build to the preview site."""
        return self._api.request(
            "POST", f"/web_baker/{web_baker_id}/deploy", project_id=project_id
        )

    def deploy_to_live(self, project_id: str) -> Any:
        """Promote the current preview to the live/production host."""
        return self._api.request("POST", "/hosting/deploy/", project_id=project_id)

    def get_hosting_status(self, project_id: str, web_baker_id: str) -> Any:
        return self._api.request(
            "GET", f"/web_baker/{web_baker_id}/hosting_status",
            project_id=project_id,
        )

    def delete_preview(self, project_id: str) -> Any:
        return self._api.request("DELETE", "/preview/", project_id=project_id)

    def delete_hosting(self, project_id: str) -> Any:
        """Tear down the live host (Cloudflare domain settings are kept)."""
        return self._api.request("DELETE", "/hosting/", project_id=project_id)

    # --- custom domain (CNAME / TXT validation) --------------------------
    def set_custom_domain(self, project_id: str, hostname: str) -> Any:
        """Register a custom domain; returns cloudflare_settings incl. the TXT
        validation records to add to DNS."""
        return self._api.request(
            "POST", "/hosting/domain/", {"hostname": hostname}, project_id
        )

    def list_custom_hostnames(self, project_id: str) -> Any:
        return self._api.request(
            "GET", "/hosting/hostnames/", project_id=project_id
        )

    def get_domain_status(self, project_id: str, hostname_id: str) -> Any:
        """Live domain/SSL status incl. the TXT ownership_verification +
        ssl.validation_records the customer must add to DNS."""
        return self._api.request(
            "GET", f"/hosting/hostnames/{hostname_id}", project_id=project_id
        )

    # --- project membership (role-gated server-side) ---------------------
    def list_project_members(self, project_id: str) -> Any:
        return self._api.request("GET", "/project_user/", project_id=project_id)

    def list_project_roles(self, project_id: str) -> Any:
        return self._api.request(
            "GET", "/project_user/roles", project_id=project_id
        )

    def connect_user_to_project(self, project_id: str, user_id: str) -> Any:
        """Add an existing tenant member to the project (as 'member'; change
        with set_project_member_role). The user must already belong to the
        project's tenant."""
        return self._api.request(
            "POST", "/project_user/",
            {"project_user": {"project_id": project_id, "user_id": user_id}},
            project_id,
        )

    def set_project_member_role(self, project_id: str, project_user_id: str,
                                project_role_id: str) -> Any:
        return self._api.request(
            "PUT", f"/project_user/{project_user_id}/role",
            {"project_role_id": project_role_id}, project_id,
        )

    def remove_project_member(self, project_id: str,
                              project_user_id: str) -> Any:
        return self._api.request(
            "DELETE", f"/project_user/{project_user_id}", project_id=project_id
        )

    # --- API keys ---------------------------------------------------------
    def create_api_key(self, project_id: str, name: str,
                       permissions: list | None = None,
                       expires_at: str | None = None) -> dict:
        """Generate a project API key (for /v1/api + /v1/public). The token is
        created here (the backend stores only its hash), so it is returned ONCE.
        permissions default to ["*"]; narrow them for least privilege."""
        token = f"kcms_{secrets.token_urlsafe(24)}"
        perms = permissions if permissions is not None else ["*"]
        self._api.request(
            "POST", "/api_key/",
            {"api_keys": [{
                "name": name,
                "key": token,
                "expires_at": expires_at,
                "permissions": perms,
            }]},
            project_id,
        )
        return {"name": name, "key": token, "permissions": perms}

    # --- project env vars / secrets (the build vault) ---------------------
    def list_env_vars(self, project_id: str) -> Any:
        """List the project's env vars (secret values are write-only)."""
        return self._api.request("GET", "/vault/", project_id=project_id)

    def set_env_var(self, project_id: str, key: str, value: str,
                    secret: bool = False) -> Any:
        """Set a project env var the build injects (secret=True stores it
        write-only). key: letters/digits/underscore, starting letter/underscore."""
        kind = "secret" if secret else "env"
        return self._api.request(
            "PUT", f"/vault/{key}", {"kind": kind, "value": value}, project_id
        )

    def delete_env_var(self, project_id: str, key: str) -> Any:
        return self._api.request(
            "DELETE", f"/vault/{key}", project_id=project_id
        )

    def configure_site_env(self, project_id: str,
                           key_name: str = "website-build",
                           permissions: list | None = None) -> dict:
        """One-shot setup so a built site (website-base-astro) can read the CMS:
        create an API key and store it + the project id in the build vault as
        CMS_API_KEY (secret) and PROJECT_ID. The builder injects these at build
        time (GET /v1/api/build/env). Returns the API key ONCE. (CMS_BASE_URL is
        not set — the site defaults it; add it with set_env_var if needed.)"""
        created = self.create_api_key(project_id, key_name, permissions)
        self.set_env_var(project_id, "CMS_API_KEY", created["key"], secret=True)
        self.set_env_var(project_id, "PROJECT_ID", project_id, secret=False)
        return {
            "ok": True,
            "api_key_name": key_name,
            "api_key": created["key"],
            "vars_set": ["CMS_API_KEY (secret)", "PROJECT_ID"],
        }

    # --- build from the Repository bundle ---------------------------------
    def build_from_repository(self, project_id: str, bundle: str,
                             runtime: str = "node22",
                             script_file: str = "build.sh") -> Any:
        """Trigger a Kantan Builder build from a Repository-app zip bundle.
        Requires the Repository app active; `bundle` is the stored zip name."""
        return self._api.request(
            "POST", "/hosting/build/repository/",
            {"bundle": bundle, "runtime": runtime, "script_file": script_file},
            project_id,
        )

    # --- apps -------------------------------------------------------------
    def list_apps(self, project_id: str) -> Any:
        """The installable app catalog."""
        return self._api.request("GET", "/apps/", project_id=project_id)

    def list_installed_apps(self, project_id: str) -> Any:
        return self._api.request("GET", "/installations/", project_id=project_id)

    def install_app(self, project_id: str, app_id: str,
                    config: dict | None = None) -> Any:
        resp = self._api.request(
            "POST", "/installations/", {"app_id": app_id}, project_id
        )
        # Optionally set the installation's config in the same step (e.g. the
        # Website Editor's mode), so activation lands fully configured.
        if config:
            inst_id = (resp or {}).get("installation", {}).get("id")
            if inst_id:
                self.configure_app(project_id, inst_id, config)
                resp = self._api.request(
                    "GET", f"/installations/{inst_id}", project_id=project_id
                )
        return resp

    def activate_website_app(self, project_id: str, mode: str) -> dict:
        """Install (if needed) the Website Editor app and set its mode, so it's
        activated via MCP in the chosen mode with no in-app chooser. mode is
        'generator' (Created by Website Generator) or 'editor' (Designed by
        Website Editor). Idempotent — reuses an existing install."""
        norm = (mode or "").strip().lower()
        if norm not in ("generator", "editor"):
            return {"ok": False, "detail": "mode must be 'generator' or 'editor'"}
        installed = self._api.request(
            "GET", "/installations/", project_id=project_id
        )
        rows = (installed or {}).get("installations") or []
        inst_id, existing = None, {}
        for r in rows:
            if r.get("app_id") == "web-baker":
                inst_id, existing = r.get("id"), (r.get("config") or {})
                break
        if not inst_id:
            resp = self._api.request(
                "POST", "/installations/", {"app_id": "web-baker"}, project_id
            )
            inst_id = (resp or {}).get("installation", {}).get("id")
        if not inst_id:
            return {
                "ok": False,
                "detail": "Could not install or find the Website Editor app",
            }
        self.configure_app(project_id, inst_id, {**existing, "mode": norm})
        return {
            "ok": True,
            "app_id": "web-baker",
            "installation_id": inst_id,
            "mode": norm,
        }

    def configure_app(self, project_id: str, installation_id: str,
                      config: dict) -> Any:
        return self._api.request(
            "PATCH", f"/installations/{installation_id}", {"config": config},
            project_id,
        )

    def uninstall_app(self, project_id: str, installation_id: str) -> Any:
        return self._api.request(
            "DELETE", f"/installations/{installation_id}", project_id=project_id
        )
