"""Parse a lead-client spreadsheet (.xlsx) into LeadClient rows. The first row
is treated as a header; columns are matched case-insensitively by name, so the
operator's sheet can use friendly headers."""
from __future__ import annotations

from openpyxl import load_workbook

from kantan_cms_mcp.domains.entities import LeadClient

# Accepted header aliases → LeadClient field.
_ALIASES = {
    "name": "name",
    "tenant": "name",
    "company": "name",
    "project": "project_name",
    "project_name": "project_name",
    "description": "description",
    "brief": "brief",
    "email": "client_email",
    "client_email": "client_email",
    "key": "external_key",
    "external_key": "external_key",
    "id": "external_key",
}


def read_lead_clients(path: str) -> list[LeadClient]:
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header = next(rows)
    except StopIteration:
        return []
    cols = [str(c).strip().lower() if c is not None else "" for c in header]

    leads: list[LeadClient] = []
    for raw in rows:
        values = list(raw) + [None] * (len(cols) - len(raw))
        mapped: dict = {}
        extra: dict = {}
        for col, value in zip(cols, values):
            if value is None or col == "":
                continue
            field = _ALIASES.get(col)
            if field:
                mapped[field] = str(value).strip()
            else:
                extra[col] = value
        if not mapped.get("name"):
            continue  # skip rows without a tenant/company name
        leads.append(LeadClient(extra=extra, **mapped))
    return leads
