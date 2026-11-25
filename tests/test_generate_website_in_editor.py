"""GenerateWebsiteInEditorUseCase, against a fake KantanApi (no HTTP)."""
from __future__ import annotations

from kantan_cms_mcp.applications.use_cases.generate_website_in_editor import (
    GenerateWebsiteInEditorUseCase,
)


class FakeApi:
    def __init__(self, result=None):
        self.calls = []
        self._result = result or {"ok": True, "changed": [], "pages": []}

    def generate_website_in_editor(
        self, project_id, specification, media_collection_id=None
    ):
        self.calls.append((project_id, specification, media_collection_id))
        return self._result


def test_passes_spec_and_media_collection():
    api = FakeApi(result={"ok": True, "pages": [{"path": "/", "title": "Home"}]})
    out = GenerateWebsiteInEditorUseCase(api).execute(
        "p-1", "  A bakery in Kyoto  ", "media-1"
    )
    assert out["ok"] is True
    # specification is trimmed before being sent
    assert api.calls == [("p-1", "A bakery in Kyoto", "media-1")]


def test_media_collection_optional():
    api = FakeApi()
    GenerateWebsiteInEditorUseCase(api).execute("p-1", "A site")
    assert api.calls == [("p-1", "A site", None)]


def test_empty_specification_rejected_without_calling_api():
    api = FakeApi()
    out = GenerateWebsiteInEditorUseCase(api).execute("p-1", "   ")
    assert out["ok"] is False
    assert api.calls == []
