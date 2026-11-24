"""Concrete KantanApi: authenticates as the operator via Supabase and calls the
backend's user-JWT surface (/v1/app). One instance per MCP process."""
from __future__ import annotations

import base64

import httpx
from supabase import create_client

from kantan_cms_mcp.config import Config

ZIP_CONTENT_TYPE = "application/zip"


class KantanHttpClient:
    def __init__(self, config: Config):
        self._config = config
        self._supabase = create_client(config.supabase_url, config.supabase_anon_key)
        self._http = httpx.Client(base_url=config.app_base, timeout=60.0)
        self._sign_in()

    # --- auth -----------------------------------------------------------------
    def _sign_in(self) -> None:
        res = self._supabase.auth.sign_in_with_password(
            {"email": self._config.operator_email, "password": self._config.operator_password}
        )
        if not res.session:
            raise RuntimeError("Operator sign-in failed")
        self._access_token = res.session.access_token
        # Make direct DB reads/writes (web_baker) run as the operator (RLS).
        self._supabase.postgrest.auth(self._access_token)

    def _headers(self, project_id: str | None = None) -> dict:
        h = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        if project_id:
            h["X-Project-Id"] = project_id
        return h

    def _request(self, method: str, path: str, *, json: dict | None = None,
                 project_id: str | None = None) -> httpx.Response:
        resp = self._http.request(method, path, json=json, headers=self._headers(project_id))
        if resp.status_code == 401:
            # Token likely expired — re-auth once and retry.
            self._sign_in()
            resp = self._http.request(method, path, json=json, headers=self._headers(project_id))
        resp.raise_for_status()
        return resp

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
        """Create the web_baker row (Supabase-direct; RLS = operator owns it)."""
        res = (
            self._supabase.table("web_baker")
            .insert({"project_id": project_id, "instruction": instruction, "status": "new"})
            .execute()
        )
        return res.data[0]["id"]

    def run_web_baker(self, project_id: str, web_baker_id: str, version: str = "v2") -> None:
        self._request(
            "POST",
            f"/web_baker/{web_baker_id}/run",
            json={"version": version},
            project_id=project_id,
        )

    def get_web_baker_status(self, web_baker_id: str) -> str:
        res = (
            self._supabase.table("web_baker")
            .select("status")
            .eq("id", web_baker_id)
            .single()
            .execute()
        )
        return (res.data or {}).get("status", "unknown")

    # --- website source download / repository upload -------------------------
    def latest_web_baker_id(self, project_id: str) -> str | None:
        res = (
            self._supabase.table("web_baker")
            .select("id")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
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
