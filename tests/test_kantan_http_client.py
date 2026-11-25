"""Unit tests for the httpx-only, MCP-key client. All HTTP is mocked with
httpx.MockTransport — no live services. The client builds its own httpx.Client
in __init__, so we patch kantan_http_client.httpx.Client to inject a shared
MockTransport that routes by path."""
from __future__ import annotations

import json as _json

import httpx
import pytest

from kantan_cms_mcp.config import Config
from kantan_cms_mcp.infras import kantan_http_client as mod

CONFIG = Config(cms_base_url="https://api.example.test", mcp_key="mcp_testkey")


def build_client(monkeypatch, handler):
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(mod.httpx, "Client", factory)
    return mod.KantanHttpClient(CONFIG)


# --- auth headers ---------------------------------------------------------


def test_requests_carry_mcp_key_and_project(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["mcp_key"] = request.headers.get("X-MCP-Key")
        seen["project"] = request.headers.get("X-Project-Id")
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"status": "running"})

    client = build_client(monkeypatch, handler)
    client.get_web_baker_status("p-1", "wb-1")

    assert seen["mcp_key"] == "mcp_testkey"
    assert seen["project"] == "p-1"
    assert seen["auth"] is None  # no Bearer — key only


def test_create_tenant_omits_project_header(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["project"] = request.headers.get("X-Project-Id")
        return httpx.Response(200, json={"tenant_id": "t-9"})

    client = build_client(monkeypatch, handler)
    assert client.create_tenant("Acme") == "t-9"
    assert seen["project"] is None  # tenant creation is not project-scoped


# --- web_baker via backend routes (no Supabase) ---------------------------


def test_create_web_baker_posts_to_backend(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/web_baker/") and request.method == "POST":
            seen["project"] = request.headers.get("X-Project-Id")
            seen["body"] = _json.loads(request.content)
            return httpx.Response(200, json={"id": "wb-7", "status": "new"})
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    wb_id = client.create_web_baker("p-1", {"pages": []})

    assert wb_id == "wb-7"
    assert seen["project"] == "p-1"
    assert seen["body"] == {"instruction": {"pages": []}}


def test_get_web_baker_status(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/web_baker/wb-7") and request.method == "GET":
            return httpx.Response(200, json={"id": "wb-7", "status": "done"})
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    assert client.get_web_baker_status("p-1", "wb-7") == "done"


def test_latest_web_baker_id(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/web_baker/") and request.method == "GET":
            return httpx.Response(200, json={"web_baker": [{"id": "wb-7"}]})
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    assert client.latest_web_baker_id("p-1") == "wb-7"


def test_latest_web_baker_id_none_when_empty(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"web_baker": []})

    client = build_client(monkeypatch, handler)
    assert client.latest_web_baker_id("p-1") is None


def test_create_project_passes_tenant_id(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _json.loads(request.content)
        return httpx.Response(200, json={"id": "pr-1", "tenant_id": "t-1"})

    client = build_client(monkeypatch, handler)
    client.create_project("Site", description="d", tenant_id="t-1")
    assert seen["body"]["project"]["tenant_id"] == "t-1"


# --- a revoked/invalid key is terminal (no retry loop) --------------------


def test_401_is_terminal(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"detail": "Invalid MCP key"})

    client = build_client(monkeypatch, handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.create_tenant("Acme")
    assert calls["n"] == 1  # surfaced immediately, not retried


# --- generic request + discovery ------------------------------------------


def test_request_returns_json_and_sends_project(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["project"] = request.headers.get("X-Project-Id")
        seen["mcp_key"] = request.headers.get("X-MCP-Key")
        return httpx.Response(200, json={"data": [{"id": "c1"}]})

    client = build_client(monkeypatch, handler)
    out = client.request("GET", "/collections/", project_id="p-1")

    assert out == {"data": [{"id": "c1"}]}
    assert (seen["method"], seen["path"]) == ("GET", "/v1/app/collections/")
    assert seen["project"] == "p-1"
    assert seen["mcp_key"] == "mcp_testkey"


def test_request_empty_response_returns_ok(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    client = build_client(monkeypatch, handler)
    assert client.request("DELETE", "/installations/i1", project_id="p-1") == {
        "ok": True,
        "status": 204,
    }


def test_request_posts_body(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _json.loads(request.content)
        return httpx.Response(200, json={"app_installation": {"id": "i1"}})

    client = build_client(monkeypatch, handler)
    client.request("POST", "/installations/", {"app_id": "buffer"}, "p-1")
    assert seen["body"] == {"app_id": "buffer"}


def test_generate_website_in_editor_posts_spec(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/web_editor/generate/"):
            seen["method"] = request.method
            seen["project"] = request.headers.get("X-Project-Id")
            seen["mcp_key"] = request.headers.get("X-MCP-Key")
            seen["body"] = _json.loads(request.content)
            return httpx.Response(
                200, json={"ok": True, "changed": [{"path": "/", "title": "Home"}]}
            )
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    out = client.generate_website_in_editor("p-1", "A bakery site", "media-1")

    assert out["ok"] is True
    assert seen["method"] == "POST"
    assert seen["project"] == "p-1"
    assert seen["mcp_key"] == "mcp_testkey"
    assert seen["body"] == {
        "specification": "A bakery site",
        "media_collection_id": "media-1",
    }


def test_get_openapi(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/openapi.json"):
            return httpx.Response(200, json={"paths": {"/collections": {"post": {}}}})
        return httpx.Response(404)

    client = build_client(monkeypatch, handler)
    assert "paths" in client.get_openapi()
