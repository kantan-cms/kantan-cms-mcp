"""Flexible access to the Kantan /v1/app surface.

A generic `call` (the escape hatch to any endpoint) + `endpoints` discovery, plus
thin convenience wrappers for the common content/app operations so the AI
doesn't have to hand-build those calls. Everything runs as the key's user, so
reach == that user's own account."""
from __future__ import annotations

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

    # --- apps -------------------------------------------------------------
    def list_apps(self, project_id: str) -> Any:
        """The installable app catalog."""
        return self._api.request("GET", "/apps/", project_id=project_id)

    def list_installed_apps(self, project_id: str) -> Any:
        return self._api.request("GET", "/installations/", project_id=project_id)

    def install_app(self, project_id: str, app_id: str) -> Any:
        return self._api.request(
            "POST", "/installations/", {"app_id": app_id}, project_id
        )

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
