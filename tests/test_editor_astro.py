"""Editor Astro export/upload use cases, against a fake KantanApi (no HTTP)."""
from __future__ import annotations

from kantan_cms_mcp.applications.use_cases.editor_astro import (
    ExportEditorSiteToAstroUseCase,
    UploadEditorSiteToRepositoryUseCase,
)


class FakeApi:
    def __init__(self, zip_bytes=b"PK\x03\x04", upload=None):
        self.calls = []
        self._zip = zip_bytes
        self._upload = upload or {"ok": True}

    def export_editor_site_to_astro(self, project_id):
        self.calls.append(("export", project_id))
        return self._zip

    def upload_editor_site_to_repository(self, project_id):
        self.calls.append(("upload", project_id))
        return self._upload


def test_export_writes_zip_to_path(tmp_path):
    api = FakeApi(zip_bytes=b"PK\x03\x04data")
    dest = tmp_path / "nested" / "site.zip"
    out = ExportEditorSiteToAstroUseCase(api).execute("p-1", str(dest))
    assert out["ok"] is True
    assert out["bytes"] == len(b"PK\x03\x04data")
    assert dest.read_bytes() == b"PK\x03\x04data"
    assert api.calls == [("export", "p-1")]


def test_upload_passthrough():
    api = FakeApi(upload={"ok": True, "repo": "website.zip"})
    out = UploadEditorSiteToRepositoryUseCase(api).execute("p-1")
    assert out == {"ok": True, "repo": "website.zip"}
    assert api.calls == [("upload", "p-1")]
