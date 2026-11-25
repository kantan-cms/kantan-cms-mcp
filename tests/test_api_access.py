"""ApiAccessUseCase: discovery parsing + convenience routing, against a fake
KantanApi (no HTTP)."""
from __future__ import annotations

from kantan_cms_mcp.applications.use_cases.api_access import ApiAccessUseCase


class FakeApi:
    def __init__(self, openapi=None):
        self.calls = []
        self._openapi = openapi or {}

    def request(self, method, path, body=None, project_id=None):
        self.calls.append((method, path, body, project_id))
        return {"ok": True}

    def get_openapi(self):
        return self._openapi


def test_endpoints_flattens_openapi():
    api = FakeApi(
        {
            "paths": {
                "/collections": {
                    "post": {"summary": "Create collection"},
                    "get": {"summary": "List collections"},
                },
                "/installations/": {"post": {"operationId": "install_app"}},
                "/ignored": {"parameters": []},  # non-method key skipped
            }
        }
    )
    eps = ApiAccessUseCase(api).endpoints()

    assert {"method": "POST", "path": "/collections", "summary": "Create collection"} in eps
    assert {"method": "GET", "path": "/collections", "summary": "List collections"} in eps
    # operationId used when summary absent
    assert {"method": "POST", "path": "/installations/", "summary": "install_app"} in eps
    # non-HTTP keys ("parameters") are not treated as operations
    assert all(e["path"] != "/ignored" for e in eps)
    # sorted by (path, method)
    assert eps == sorted(eps, key=lambda e: (e["path"], e["method"]))


def test_create_collection_routing():
    api = FakeApi()
    ApiAccessUseCase(api).create_collection("p-1", "Blog", "blog", description="d")
    method, path, body, project_id = api.calls[-1]
    assert (method, path, project_id) == ("POST", "/collections", "p-1")
    assert body == {"name": "Blog", "type": "blog", "description": "d", "icon": None}


def test_install_and_configure_routing():
    api = FakeApi()
    uc = ApiAccessUseCase(api)
    uc.install_app("p-1", "buffer")
    assert api.calls[-1] == ("POST", "/installations/", {"app_id": "buffer"}, "p-1")
    uc.configure_app("p-1", "i1", {"token": "x"})
    assert api.calls[-1] == (
        "PATCH",
        "/installations/i1",
        {"config": {"token": "x"}},
        "p-1",
    )


def test_create_record_routing():
    api = FakeApi()
    ApiAccessUseCase(api).create_record("p-1", "c1", {"title": "Hello"})
    assert api.calls[-1] == (
        "POST",
        "/collections/c1/records/",
        {"title": "Hello"},
        "p-1",
    )
