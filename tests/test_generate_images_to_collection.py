"""GenerateImagesToCollectionUseCase, against a fake KantanApi (no HTTP)."""
from __future__ import annotations

from kantan_cms_mcp.applications.use_cases.generate_images_to_collection import (
    MAX_PROMPTS,
    GenerateImagesToCollectionUseCase,
)


class FakeApi:
    def __init__(self, result=None):
        self.calls = []
        self._result = result or {"images": []}

    def generate_images_to_collection(
        self, project_id, collection_id, prompts, aspect_ratio="1:1"
    ):
        self.calls.append((project_id, collection_id, prompts, aspect_ratio))
        return self._result


def test_trims_and_forwards_prompts():
    api = FakeApi(result={"images": [{"id": "r1"}]})
    out = GenerateImagesToCollectionUseCase(api).execute(
        "p-1", "c-1", ["  a cat  ", "", "  "], "16:9"
    )
    assert out == {"images": [{"id": "r1"}]}
    assert api.calls == [("p-1", "c-1", ["a cat"], "16:9")]


def test_empty_prompts_rejected_without_calling_api():
    api = FakeApi()
    out = GenerateImagesToCollectionUseCase(api).execute("p-1", "c-1", ["   "])
    assert out["ok"] is False
    assert api.calls == []


def test_too_many_prompts_rejected():
    api = FakeApi()
    out = GenerateImagesToCollectionUseCase(api).execute(
        "p-1", "c-1", [f"p{i}" for i in range(MAX_PROMPTS + 1)]
    )
    assert out["ok"] is False
    assert api.calls == []
