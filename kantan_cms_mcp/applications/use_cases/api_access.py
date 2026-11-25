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

    def create_record(self, project_id: str, collection_id: str,
                      data: dict) -> Any:
        # `data` is a flat map of field custom_key -> value.
        return self._api.request(
            "POST", f"/collections/{collection_id}/records/", data, project_id
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
