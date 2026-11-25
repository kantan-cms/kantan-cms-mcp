"""Generate images from prompts and store them as records in a media collection.

The backend reuses its own image generator (Gemini), uploads each image to the
content store, and creates a media record pointing at it — so the images show up
in the collection like any uploaded media. Billed per image to the project's
tenant. Blocks until all images are generated (seconds each).
"""
from __future__ import annotations

from kantan_cms_mcp.domains.kantan_api import KantanApi

# Matches the backend cap (keeps one call bounded in cost and time).
MAX_PROMPTS = 10


class GenerateImagesToCollectionUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def execute(
        self,
        project_id: str,
        collection_id: str,
        prompts: list[str],
        aspect_ratio: str = "1:1",
    ) -> dict:
        cleaned = [p.strip() for p in (prompts or []) if p and p.strip()]
        if not cleaned:
            return {"ok": False, "detail": "At least one prompt is required"}
        if len(cleaned) > MAX_PROMPTS:
            return {
                "ok": False,
                "detail": f"Too many prompts (max {MAX_PROMPTS} per call)",
            }
        return self._api.generate_images_to_collection(
            project_id, collection_id, cleaned, aspect_ratio
        )
