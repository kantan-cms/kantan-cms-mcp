"""Web Editor Astro actions, exposed to the MCP.

Both run the editor's site→Astro conversion (the editor's "Export to Astro" and
"Upload to Repository" toolbar actions) against the project's stored editor site:
- export writes the Astro zip to a local file,
- upload pushes it into the project's Repository store (needs the Repository app).
"""
from __future__ import annotations

from pathlib import Path

from kantan_cms_mcp.domains.kantan_api import KantanApi


class ExportEditorSiteToAstroUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def execute(self, project_id: str, out_path: str) -> dict:
        data = self._api.export_editor_site_to_astro(project_id)
        dest = Path(out_path).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {"ok": True, "path": str(dest), "bytes": len(data)}


class UploadEditorSiteToRepositoryUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def execute(self, project_id: str) -> dict:
        return self._api.upload_editor_site_to_repository(project_id)
