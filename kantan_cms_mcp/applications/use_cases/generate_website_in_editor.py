"""Generate a website from scratch in the Web Editor.

The Web Editor (an external Puck + React Router service) can build a whole
multi-page, themed site from a plain-language specification — the same flow as
its in-app "AI generate site" dialog. The backend proxies this request to the
editor, forwarding the user's MCP key, so the generation runs as the user
against their project's stored site and is billed to their account.

This blocks until the editor finishes (minutes). The project's tenant needs an
active subscription / AI credits, like any generation.
"""
from __future__ import annotations

from kantan_cms_mcp.domains.kantan_api import KantanApi


class GenerateWebsiteInEditorUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def execute(
        self,
        project_id: str,
        specification: str,
        media_collection_id: str | None = None,
        blog_collection_id: str | None = None,
        form_collection_id: str | None = None,
    ) -> dict:
        spec = (specification or "").strip()
        if not spec:
            return {"ok": False, "detail": "specification is required"}
        return self._api.generate_website_in_editor(
            project_id,
            spec,
            media_collection_id,
            blog_collection_id,
            form_collection_id,
        )
