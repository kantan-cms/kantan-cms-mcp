"""Concrete KantanApi: a thin httpx client over the backend's /v1/app surface,
authenticating with a per-user MCP key (`X-MCP-Key`). No Supabase SDK and no
direct database access — web_baker create/status go through backend routes."""
from __future__ import annotations

import base64
from typing import Any

import httpx

from kantan_cms_mcp.config import Config

ZIP_CONTENT_TYPE = "application/zip"


class KantanHttpClient:
    def __init__(self, config: Config):
        self._config = config
        self._mcp_key = config.mcp_key
        self._http = httpx.Client(base_url=config.app_base, timeout=60.0)

    def _headers(self, project_id: str | None = None) -> dict:
        h = {
            "X-MCP-Key": self._mcp_key,
            "Content-Type": "application/json",
        }
        if project_id:
            h["X-Project-Id"] = project_id
        return h

    def _request(self, method: str, path: str, *, json: dict | None = None,
                 project_id: str | None = None) -> httpx.Response:
        # An MCP key is long-lived; a 401 means revoked/expired/invalid, which is
        # terminal — surface it rather than retrying.
        resp = self._http.request(
            method, path, json=json, headers=self._headers(project_id)
        )
        resp.raise_for_status()
        return resp

    # --- generic access (any /v1/app endpoint) -------------------------------
    def request(self, method: str, path: str, body: dict | None = None,
                project_id: str | None = None) -> Any:
        """Call any /v1/app endpoint as the user. `path` is relative to
        /v1/app (e.g. "/collections"); add a query string inline if needed.
        Returns parsed JSON, or {ok, status} for an empty/non-JSON response."""
        resp = self._request(
            method.upper(), path, json=body, project_id=project_id
        )
        if resp.status_code == 204 or not resp.content:
            return {"ok": True, "status": resp.status_code}
        try:
            return resp.json()
        except ValueError:
            return {"ok": True, "status": resp.status_code, "text": resp.text[:2000]}

    def get_openapi(self) -> dict:
        """The /v1/app OpenAPI document (for endpoint discovery)."""
        resp = self._http.get("/openapi.json")
        resp.raise_for_status()
        return resp.json()

    # --- operations (map to /v1/app) -----------------------------------------
    def create_tenant(self, name: str) -> str:
        resp = self._request("POST", "/tenant", json={"tenant": {"name": name}})
        return resp.json()["tenant_id"]

    def create_project(
        self, name: str, description: str | None = None, tenant_id: str | None = None
    ) -> dict:
        project: dict = {"name": name, "description": description}
        if tenant_id:
            project["tenant_id"] = tenant_id
        return self._request("POST", "/project", json={"project": project}).json()

    def move_project(self, project_id: str, destination_tenant_id: str) -> dict:
        return self._request(
            "POST",
            f"/project/{project_id}/move",
            json={"destination_tenant_id": destination_tenant_id},
        ).json()

    def invite_tenant_member(self, tenant_id: str, email: str, role: str) -> None:
        self._request(
            "POST",
            "/tenant_user/invite",
            json={"tenant_id": tenant_id, "email": email, "role": role},
        )

    # --- website generation (web-baker) --------------------------------------
    def generate_baker_instruction(self, project_id: str, title: str,
                                   description: str | None) -> dict:
        """Ask the backend to turn a title + brief into a baker instruction."""
        resp = self._request(
            "POST",
            "/ai/baker_instruction",
            json={"title": title, "description": description or ""},
            project_id=project_id,
        )
        data = resp.json()
        return data.get("instruction", data)

    def create_web_baker(self, project_id: str, instruction: dict) -> str:
        """Create the project's web_baker row via the backend (one per project)."""
        resp = self._request(
            "POST",
            "/web_baker/",
            json={"instruction": instruction},
            project_id=project_id,
        )
        return resp.json()["id"]

    def run_web_baker(self, project_id: str, web_baker_id: str, version: str = "v2") -> None:
        self._request(
            "POST",
            f"/web_baker/{web_baker_id}/run",
            json={"version": version},
            project_id=project_id,
        )

    def get_web_baker_status(self, project_id: str, web_baker_id: str) -> str:
        resp = self._request(
            "GET", f"/web_baker/{web_baker_id}", project_id=project_id
        )
        return (resp.json() or {}).get("status", "unknown")

    def set_web_baker_instruction(
        self, project_id: str, web_baker_id: str, instruction: dict
    ) -> None:
        self._request(
            "PUT",
            f"/web_baker/{web_baker_id}/instruction",
            json={"instruction": instruction},
            project_id=project_id,
        )

    def reset_web_baker(self, project_id: str, web_baker_id: str) -> None:
        self._request(
            "POST", f"/web_baker/{web_baker_id}/reset", project_id=project_id
        )

    # --- website source download / repository upload -------------------------
    def latest_web_baker_id(self, project_id: str) -> str | None:
        resp = self._request("GET", "/web_baker/", project_id=project_id)
        rows = (resp.json() or {}).get("web_baker") or []
        return rows[0]["id"] if rows else None

    def download_website_zip(self, project_id: str, web_baker_id: str) -> bytes:
        # Ask the backend for a presigned GET, then pull the bytes from GCS.
        resp = self._request(
            "GET",
            f"/web_baker/{web_baker_id}/presigned_url",
            project_id=project_id,
        )
        url = resp.json()["presigned_url"]
        with httpx.Client(timeout=120.0) as raw:
            got = raw.get(url)
            got.raise_for_status()
            return got.content

    def overwrite_website_zip(
        self, project_id: str, web_baker_id: str, zip_bytes: bytes
    ) -> None:
        self._request(
            "POST",
            f"/web_baker/{web_baker_id}/website_zip",
            json={"zip_base64": base64.b64encode(zip_bytes).decode("ascii")},
            project_id=project_id,
        )

    def upload_repository_zip(
        self, project_id: str, name: str, zip_bytes: bytes
    ) -> None:
        # Presigned PUT bound to application/zip — the uploader must match it.
        resp = self._request(
            "POST",
            "/repository/upload_url/",
            json={"name": name},
            project_id=project_id,
        )
        url = resp.json()["url"]
        with httpx.Client(timeout=120.0) as raw:
            put = raw.put(
                url, content=zip_bytes, headers={"Content-Type": ZIP_CONTENT_TYPE}
            )
            put.raise_for_status()

    def import_website_to_repository(self, project_id: str, name: str) -> dict:
        return self._request(
            "POST",
            "/repository/import_web_baker/",
            json={"name": name},
            project_id=project_id,
        ).json()
