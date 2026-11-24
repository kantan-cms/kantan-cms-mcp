"""Push a website zip into a project's Repository store.

Two modes:
- from a local zip (edited externally) — upload its bytes, and optionally make
  it the project's source so a rebuild picks up the edits;
- server-side import of the current generated website.zip (no local file).

The Repository app must be active on the project (the backend enforces this)."""
from __future__ import annotations

from pathlib import Path

from kantan_cms_mcp.domains.kantan_api import KantanApi


class PublishWebsiteToRepositoryUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def from_local_zip(
        self,
        project_id: str,
        zip_path: str,
        name: str = "website.zip",
        set_as_source: bool = False,
    ) -> dict:
        src = Path(zip_path).expanduser()
        if not src.is_file():
            return {"ok": False, "detail": f"No such file: {src}"}
        data = src.read_bytes()
        self._api.upload_repository_zip(project_id, name, data)
        result = {"ok": True, "name": name, "bytes": len(data)}
        if set_as_source:
            wb_id = self._api.latest_web_baker_id(project_id)
            if wb_id:
                self._api.overwrite_website_zip(project_id, wb_id, data)
                result["source_updated_web_baker_id"] = wb_id
            else:
                result["source_updated_web_baker_id"] = None
        return result

    def import_generated(
        self, project_id: str, name: str = "website.zip"
    ) -> dict:
        entry = self._api.import_website_to_repository(project_id, name)
        return {"ok": True, "entry": entry}
