"""Hand a provisioned tenant to the paying client: invite them (they accept
asynchronously, then an owner can promote them). Promotion to owner happens
once they've accepted — kept as a separate step because acceptance is async."""
from __future__ import annotations

from kantan_cms_mcp.domains.kantan_api import KantanApi


class HandOverClientUseCase:
    def __init__(self, api: KantanApi):
        self._api = api

    def execute(self, tenant_id: str, client_email: str, role: str = "owner") -> dict:
        self._api.invite_tenant_member(tenant_id, client_email, role)
        return {
            "status": "invited",
            "tenant_id": tenant_id,
            "email": client_email,
            "role": role,
            "note": "The client must accept the invitation before the role takes effect.",
        }
