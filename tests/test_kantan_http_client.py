"""Unit tests for KantanHttpClient's httpx-only Supabase auth + PostgREST.

All HTTP is mocked with httpx.MockTransport — no live services. The client
builds its own httpx.Client instances in __init__ (and calls _sign_in there),
so we patch kantan_http_client.httpx.Client to inject a shared MockTransport
that routes by URL path."""
from __future__ import annotations

import httpx
import pytest

from kantan_cms_mcp.config import Config
from kantan_cms_mcp.infras import kantan_http_client as mod

OPERATOR_PASSWORD = "sup3r-secret-pw"

CONFIG = Config(
    cms_base_url="https://api.example.test",
    supabase_url="https://db.example.test",
    supabase_anon_key="anon-key",
    operator_email="ops@example.test",
    operator_password=OPERATOR_PASSWORD,
)


def build_client(monkeypatch, handler):
    """Construct a KantanHttpClient whose httpx.Clients use MockTransport."""
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(mod.httpx, "Client", factory)
    return mod.KantanHttpClient(CONFIG)


def _ok_session(token="access-1", refresh="refresh-1", expires=3600):
    return {"access_token": token, "refresh_token": refresh, "expires_in": expires}


# --- sign-in --------------------------------------------------------------


def test_sign_in_success_stores_session(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/v1/token"):
            seen["grant_type"] = request.url.params.get("grant_type")
            seen["apikey"] = request.headers.get("apikey")
            return httpx.Response(200, json=_ok_session())
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)

    assert client._access_token == "access-1"
    assert client._refresh_token == "refresh-1"
    assert client._expires_in == 3600
    assert seen["grant_type"] == "password"
    assert seen["apikey"] == "anon-key"


def test_sign_in_failure_raises_without_password(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error_description": "Invalid login credentials"})

    with pytest.raises(RuntimeError) as exc:
        build_client(monkeypatch, handler)

    msg = str(exc.value)
    assert "Operator sign-in failed" in msg
    assert "Invalid login credentials" in msg
    assert OPERATOR_PASSWORD not in msg


# --- refresh + 401 retry --------------------------------------------------


def test_reauth_prefers_refresh_token(monkeypatch):
    calls = {"password": 0, "refresh": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/v1/token"):
            grant = request.url.params.get("grant_type")
            if grant == "password":
                calls["password"] += 1
                return httpx.Response(200, json=_ok_session())
            if grant == "refresh_token":
                calls["refresh"] += 1
                return httpx.Response(200, json=_ok_session(token="access-2"))
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    assert calls == {"password": 1, "refresh": 0}

    client._reauth()
    # Refresh succeeded, so no new password sign-in; token rotated.
    assert calls == {"password": 1, "refresh": 1}
    assert client._access_token == "access-2"


def test_reauth_falls_back_to_password_when_refresh_fails(monkeypatch):
    calls = {"password": 0, "refresh": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/v1/token"):
            grant = request.url.params.get("grant_type")
            if grant == "password":
                calls["password"] += 1
                return httpx.Response(200, json=_ok_session(token=f"pw-{calls['password']}"))
            if grant == "refresh_token":
                calls["refresh"] += 1
                return httpx.Response(401, json={"error": "invalid refresh"})
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    client._reauth()

    assert calls["refresh"] == 1  # tried refresh first
    assert calls["password"] == 2  # then fell back to password
    assert client._access_token == "pw-2"


def test_backend_401_triggers_reauth_and_retry(monkeypatch):
    state = {"tenant_attempts": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/v1/token"):
            grant = request.url.params.get("grant_type")
            if grant == "refresh_token":
                return httpx.Response(200, json=_ok_session(token="access-2"))
            return httpx.Response(200, json=_ok_session())
        if path.endswith("/v1/app/tenant"):
            state["tenant_attempts"] += 1
            if state["tenant_attempts"] == 1:
                return httpx.Response(401, json={"detail": "expired"})
            return httpx.Response(200, json={"tenant_id": "t-123"})
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    tenant_id = client.create_tenant("Acme")

    assert tenant_id == "t-123"
    assert state["tenant_attempts"] == 2  # 401 then retried
    assert client._access_token == "access-2"  # reauthed via refresh


# --- web_baker PostgREST --------------------------------------------------


def test_create_web_baker_inserts_and_returns_id(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/v1/token"):
            return httpx.Response(200, json=_ok_session())
        if path.endswith("/rest/v1/web_baker") and request.method == "POST":
            import json as _json

            seen["prefer"] = request.headers.get("Prefer")
            seen["apikey"] = request.headers.get("apikey")
            seen["auth"] = request.headers.get("Authorization")
            seen["body"] = _json.loads(request.content)
            return httpx.Response(201, json=[{"id": "wb-9"}])
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    wb_id = client.create_web_baker("p-1", {"pages": []})

    assert wb_id == "wb-9"
    assert seen["prefer"] == "return=representation"
    assert seen["apikey"] == "anon-key"
    assert seen["auth"] == "Bearer access-1"
    assert seen["body"] == {"project_id": "p-1", "instruction": {"pages": []}, "status": "new"}


def test_get_web_baker_status_single_object(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/v1/token"):
            return httpx.Response(200, json=_ok_session())
        if path.endswith("/rest/v1/web_baker") and request.method == "GET":
            seen["accept"] = request.headers.get("Accept")
            seen["id"] = request.url.params.get("id")
            seen["select"] = request.url.params.get("select")
            return httpx.Response(200, json={"status": "running"})
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    status = client.get_web_baker_status("wb-9")

    assert status == "running"
    assert seen["accept"] == "application/vnd.pgrst.object+json"
    assert seen["id"] == "eq.wb-9"
    assert seen["select"] == "status"


def test_get_web_baker_status_defaults_to_unknown(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/v1/token"):
            return httpx.Response(200, json=_ok_session())
        if request.url.path.endswith("/rest/v1/web_baker"):
            return httpx.Response(200, json={})  # no status field
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    assert client.get_web_baker_status("wb-9") == "unknown"


def test_db_401_triggers_reauth_and_retry(monkeypatch):
    state = {"attempts": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/v1/token"):
            grant = request.url.params.get("grant_type")
            if grant == "refresh_token":
                return httpx.Response(200, json=_ok_session(token="access-2"))
            return httpx.Response(200, json=_ok_session())
        if path.endswith("/rest/v1/web_baker"):
            state["attempts"] += 1
            if state["attempts"] == 1:
                return httpx.Response(401, json={"message": "JWT expired"})
            return httpx.Response(200, json={"status": "done"})
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    assert client.get_web_baker_status("wb-9") == "done"
    assert state["attempts"] == 2
    assert client._access_token == "access-2"
