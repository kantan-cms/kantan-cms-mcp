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


def test_record_crud_routing():
    api = FakeApi()
    uc = ApiAccessUseCase(api)

    uc.list_records("p-1", "c1", page_size=10, page_num=2)
    assert api.calls[-1] == (
        "GET", "/collections/c1/records/?page_size=10&page_num=2", None, "p-1",
    )

    uc.get_record("p-1", "c1", "r9")
    assert api.calls[-1] == ("GET", "/collections/c1/records/r9", None, "p-1")

    uc.update_record("p-1", "c1", "r9", {"title": "New"})
    assert api.calls[-1] == (
        "PATCH", "/collections/c1/records/r9", {"title": "New"}, "p-1",
    )

    uc.delete_record("p-1", "c1", "r9")
    assert api.calls[-1] == ("DELETE", "/collections/c1/records/r9", None, "p-1")


def test_collection_update_delete_routing():
    api = FakeApi()
    uc = ApiAccessUseCase(api)
    uc.update_collection("p-1", "c1", name="New", icon=None)
    assert api.calls[-1] == ("PATCH", "/collections/c1", {"name": "New"}, "p-1")
    uc.delete_collection("p-1", "c1")
    assert api.calls[-1] == ("DELETE", "/collections/c1", None, "p-1")


def test_bulk_records_routing():
    api = FakeApi()
    uc = ApiAccessUseCase(api)
    uc.bulk_create_records("p-1", "c1", [{"t": 1}])
    assert api.calls[-1] == (
        "POST", "/collections/c1/records/bulk", {"records": [{"t": 1}]}, "p-1",
    )
    uc.bulk_update_records("p-1", "c1", [{"id": "r1", "data": {"t": 2}}])
    assert api.calls[-1][:2] == ("PATCH", "/collections/c1/records/bulk")
    uc.bulk_delete_records("p-1", "c1", ["r1", "r2"])
    assert api.calls[-1] == (
        "POST", "/collections/c1/records/bulk/delete", {"ids": ["r1", "r2"]}, "p-1",
    )


def test_hosting_routing():
    api = FakeApi()
    uc = ApiAccessUseCase(api)
    uc.deploy_to_preview("p-1", "wb1")
    assert api.calls[-1] == ("POST", "/web_baker/wb1/deploy", None, "p-1")
    uc.deploy_to_live("p-1")
    assert api.calls[-1] == ("POST", "/hosting/deploy/", None, "p-1")
    uc.delete_preview("p-1")
    assert api.calls[-1] == ("DELETE", "/preview/", None, "p-1")
    uc.delete_hosting("p-1")
    assert api.calls[-1] == ("DELETE", "/hosting/", None, "p-1")


def test_domain_and_membership_routing():
    api = FakeApi()
    uc = ApiAccessUseCase(api)
    uc.set_custom_domain("p-1", "www.example.com")
    assert api.calls[-1] == (
        "POST", "/hosting/domain/", {"hostname": "www.example.com"}, "p-1",
    )
    uc.get_domain_status("p-1", "h1")
    assert api.calls[-1] == ("GET", "/hosting/hostnames/h1", None, "p-1")
    uc.connect_user_to_project("p-1", "u9")
    assert api.calls[-1] == (
        "POST", "/project_user/",
        {"project_user": {"project_id": "p-1", "user_id": "u9"}}, "p-1",
    )
    uc.set_project_member_role("p-1", "pu1", "role1")
    assert api.calls[-1] == (
        "PUT", "/project_user/pu1/role", {"project_role_id": "role1"}, "p-1",
    )
    uc.remove_project_member("p-1", "pu1")
    assert api.calls[-1] == ("DELETE", "/project_user/pu1", None, "p-1")


def test_api_key_vault_build_routing():
    api = FakeApi()
    uc = ApiAccessUseCase(api)

    created = uc.create_api_key("p-1", "ci", permissions=["records:read"])
    method, path, body, pid = api.calls[-1]
    assert (method, path, pid) == ("POST", "/api_key/", "p-1")
    key = body["api_keys"][0]
    assert key["name"] == "ci" and key["permissions"] == ["records:read"]
    assert key["key"].startswith("kcms_") and created["key"] == key["key"]

    uc.set_env_var("p-1", "CMS_API_KEY", "secret-val", secret=True)
    assert api.calls[-1] == (
        "PUT", "/vault/CMS_API_KEY", {"kind": "secret", "value": "secret-val"}, "p-1",
    )
    uc.set_env_var("p-1", "PROJECT_ID", "p-1")
    assert api.calls[-1] == (
        "PUT", "/vault/PROJECT_ID", {"kind": "env", "value": "p-1"}, "p-1",
    )
    uc.delete_env_var("p-1", "PROJECT_ID")
    assert api.calls[-1] == ("DELETE", "/vault/PROJECT_ID", None, "p-1")

    uc.build_from_repository("p-1", "site.zip")
    assert api.calls[-1] == (
        "POST", "/hosting/build/repository/",
        {"bundle": "site.zip", "runtime": "node22", "script_file": "build.sh"}, "p-1",
    )


def test_configure_site_env_sets_three_vars():
    api = FakeApi()
    out = ApiAccessUseCase(api).configure_site_env("p-1", "https://api.kantan-cms.dev")
    # api_key create + 3 vault PUTs = 4 calls
    assert [c[:2] for c in api.calls] == [
        ("POST", "/api_key/"),
        ("PUT", "/vault/CMS_API_KEY"),
        ("PUT", "/vault/PROJECT_ID"),
        ("PUT", "/vault/CMS_BASE_URL"),
    ]
    assert api.calls[1][2] == {"kind": "secret", "value": out["api_key"]}
    assert api.calls[2][2] == {"kind": "env", "value": "p-1"}
    assert api.calls[3][2] == {"kind": "env", "value": "https://api.kantan-cms.dev"}
