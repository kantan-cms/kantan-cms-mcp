# Kantan CMS — Operator Provisioning MCP

An **operator-only** MCP server that automates agency-style lead provisioning on
Kantan CMS: read a spreadsheet of lead clients and, for each, create a tenant +
project (you become the owner), then hand finished tenants to paying clients.

> ⚠️ This MCP acts as **one operator account** and can create tenants and
> memberships. It is **not** a per-user integration and must **never** be exposed
> to end users. For a user-facing, per-project content integration, use the
> API-key `/v1/api` surface instead (the previous MCP, kept under `archive/`).

## How it works

It authenticates as the operator via Supabase and calls the backend user-JWT
surface (`/v1/app`). Because **creating a tenant makes the caller its owner**,
every tenant the operator creates is already owned by the operator — no special
"attach my account" step is needed.

Provisioning composes existing endpoints: `create tenant` → `create project` →
`move project` into the new tenant (the backend's create-project lands a project
in the operator's default tenant, so we relocate it with the owner-gated,
single-member move). Handover invites the client, who accepts and is then an
owner.

## Tools

- `read_lead_clients(path)` — parse an `.xlsx` into rows (review before creating).
- `provision_lead_client(name, project_name?, description?, client_email?)` — one lead.
- `provision_from_excel(path)` — every row; one result each, failures isolated.
- `move_project(project_id, destination_tenant_id)` — relocate a project (backend enforces the rules).
- `hand_over_client(tenant_id, client_email, role="owner")` — invite the client.

## Architecture (mirrors the backend)

```
kantan_cms_mcp/
  interfaces/tools.py          MCP tools (entrypoints; like views)
  applications/use_cases/      orchestration (provision, hand_over, move, batch)
  domains/                     entities + the KantanApi port
  infras/                      HTTP client (Supabase auth + /v1/app) + Excel reader
```

## Run

```
pip install -r requirements.txt
export CMS_BASE_URL=https://api.kantan-cms.dev
export SUPABASE_URL=... SUPABASE_ANON_KEY=...
export KANTAN_OPERATOR_EMAIL=... KANTAN_OPERATOR_PASSWORD=...
python main.py
```

MCP client config:

```json
{
  "mcpServers": {
    "kantan-cms-operator": {
      "command": "python",
      "args": ["<absolute path to kantan-cms-mcp>/main.py"],
      "env": {
        "CMS_BASE_URL": "https://api.kantan-cms.dev",
        "SUPABASE_URL": "<supabase url>",
        "SUPABASE_ANON_KEY": "<anon key>",
        "KANTAN_OPERATOR_EMAIL": "<operator email>",
        "KANTAN_OPERATOR_PASSWORD": "<operator password>"
      }
    }
  }
}
```

## Known follow-ups

- **Idempotency:** re-running provisioning currently re-creates tenants. Planned:
  dedupe by `external_key` (or a tenant-name lookup) so batches are resumable.
- **Direct tenant-scoped project creation:** add an optional `tenant_id` to the
  backend create-project so we can skip the create-then-move hop.
- **Content seeding / site generation** (collections, records, web-baker run) as
  further provisioning steps.
- Not runtime-tested against live credentials yet — smoke-test the operator
  sign-in + a single `provision_lead_client` before batch use.

The previous API-key content MCP is preserved under [`archive/`](archive/).
