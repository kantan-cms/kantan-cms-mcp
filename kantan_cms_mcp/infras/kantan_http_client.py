"""Concrete KantanApi: authenticates as the operator against Supabase's REST
auth API (GoTrue) and calls the backend's user-JWT surface (/v1/app). The few
direct `web_baker` reads/writes go through Supabase's REST database API
(PostgREST) with the operator's token (RLS limits rows to ones it owns). One
instance per MCP process; no Supabase Python SDK — just httpx."""
from __future__ import annotations

import base64

import httpx

from kantan_cms_mcp.config import Config

ZIP_CONTENT_TYPE = "application/zip"


def _auth_error(resp: httpx.Response) -> str:
    """Best-effort error text from a GoTrue response — never the password."""
    try:
        data = resp.json()
    except ValueError:
        return f"HTTP {resp.status_code}"
    for key in ("error_description", "msg", "message", "error"):
        val = data.get(key)
        if val:
            return str(val)
    return f"HTTP {resp.status_code}"


class KantanHttpClient:
    def __init__(self, config: Config):
        self._config = config
        base = config.supabase_url.rstrip("/")
        self._anon_key = config.supabase_anon_key
        # Backend user-JWT surface (/v1/app).
        self._http = httpx.Client(base_url=config.app_base, timeout=60.0)
        # Supabase GoTrue auth + PostgREST database, same host, different prefix.
        self._auth = httpx.Client(base_url=f"{base}/auth/v1", timeout=30.0)
        self._db = httpx.Client(base_url=f"{base}/rest/v1", timeout=60.0)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_in: int | None = None
        self._sign_in()

    # --- auth -----------------------------------------------------------------
    def _store_session(self, data: dict) -> None:
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token")
        self._expires_in = data.get("expires_in")

    def _sign_in(self) -> None:
        resp = self._auth.post(
            "/token",
            params={"grant_type": "password"},
            headers={"apikey": self._anon_key},
            json={
                "email": self._config.operator_email,
                "password": self._config.operator_password,
            },
        )
        if resp.status_code != 200 or "access_token" not in (resp.json() or {}):
            raise RuntimeError(f"Operator sign-in failed: {_auth_error(resp)}")
        self._store_session(resp.json())

    def _refresh(self) -> bool:
        """Refresh the access token; return False if it didn't work."""
        if not self._refresh_token:
            return False
        resp = self._auth.post(
            "/token",
            params={"grant_type": "refresh_token"},
            headers={"apikey": self._anon_key},
            json={"refresh_token": self._refresh_token},
        )
        if resp.status_code != 200 or "access_token" not in (resp.json() or {}):
            return False
        self._store_session(resp.json())
        return True

    def _reauth(self) -> None:
        """On a 401: try the refresh token first, else a password sign-in."""
        if not self._refresh():
            self._sign_in()

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
            self._reauth()
            resp = self._http.request(method, path, json=json, headers=self._headers(project_id))
        resp.raise_for_status()
        return resp

    # --- Supabase PostgREST (web_baker, operator-owned via RLS) ---------------
    def _db_headers(self, extra: dict | None = None) -> dict:
        h = {
            "apikey": self._anon_key,
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        if extra:
            h.update(extra)
        return h

    def _db_request(self, method: str, path: str, *, json: object | None = None,
                    params: dict | None = None, headers: dict | None = None) -> httpx.Response:
        resp = self._db.request(method, path, json=json, params=params,
                                headers=self._db_headers(headers))
        if resp.status_code == 401:
            # Generation polling can run for minutes — re-auth once and retry.
            self._reauth()
            resp = self._db.request(method, path, json=json, params=params,
                                    headers=self._db_headers(headers))
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
        """Create the web_baker row (PostgREST; RLS = operator owns it)."""
        resp = self._db_request(
            "POST",
            "/web_baker",
            json={"project_id": project_id, "instruction": instruction, "status": "new"},
            headers={"Prefer": "return=representation"},
        )
        return resp.json()[0]["id"]

    def run_web_baker(self, project_id: str, web_baker_id: str, version: str = "v2") -> None:
        self._request(
            "POST",
            f"/web_baker/{web_baker_id}/run",
            json={"version": version},
            project_id=project_id,
        )

    def get_web_baker_status(self, web_baker_id: str) -> str:
        resp = self._db_request(
            "GET",
            "/web_baker",
            params={"id": f"eq.{web_baker_id}", "select": "status"},
            headers={"Accept": "application/vnd.pgrst.object+json"},
        )
        return (resp.json() or {}).get("status", "unknown")

    # --- website source download / repository upload -------------------------
    def latest_web_baker_id(self, project_id: str) -> str | None:
        resp = self._db_request(
            "GET",
            "/web_baker",
            params={
                "project_id": f"eq.{project_id}",
                "select": "id",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        rows = resp.json() or []
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
