"""Download a project's generated-website SOURCE (website.zip) to a local file
so it can be edited with external tools, then re-uploaded (see
publish_website_to_repository)."""
from __future__ import annotations

from pathlib import Path

from kantan_cms_mcp.domains.kantan_api import KantanApi


class DownloadWebsiteUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def execute(
        self, project_id: str, out_path: str, web_baker_id: str | None = None
    ) -> dict:
        wb_id = web_baker_id or self._api.latest_web_baker_id(project_id)
        if not wb_id:
            return {
                "ok": False,
                "detail": "This project has no generated website yet.",
            }
        data = self._api.download_website_zip(project_id, wb_id)
        dest = Path(out_path).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {
            "ok": True,
            "web_baker_id": wb_id,
            "path": str(dest),
            "bytes": len(data),
        }
