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

Provisioning is a clean one-hop: `create tenant` → `create project` **in that
tenant** (the backend's create-project takes an optional owner-gated
`tenant_id`). It is **idempotent/resumable** via a local JSON ledger keyed by
each lead's `external_key` (else name): re-runs skip finished leads and resume
partial ones, so a batch never duplicates tenants. Handover invites the client,
who accepts and is then an owner. (`move_project` remains available as its own
tool for relocating an existing project between tenants.)

## Tools

- `read_lead_clients(path)` — parse an `.xlsx` into rows (review before creating).
- `provision_lead_client(name, project_name?, description?, client_email?, external_key?)` — one lead (tenant + project, no generation).
- `provision_from_excel(path)` — every row; one result each, failures isolated.
- `provision_and_generate(name, brief, project_name?, description?, external_key?)` — provision **and** generate the site: build + generate in your (subscribed) tenant, then move the finished project into the lead's tenant. Blocks until generation finishes (minutes) or times out; resumable.
- `move_project(project_id, destination_tenant_id)` — relocate a project (backend enforces the rules).
- `hand_over_client(tenant_id, client_email, role="owner")` — invite the client.

### Why generation builds in *your* tenant

A brand-new lead tenant has no subscription, so it can't run the generator
(`no active subscription`). `provision_and_generate` therefore creates + generates
the project in the **operator's** subscribed tenant (billing the build to you)
and then **moves** the finished project into the lead's tenant via the
owner-gated, single-member move.

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

The ledger file defaults to `kantan_mcp_ledger.json` in the working directory;
override with `KANTAN_MCP_LEDGER`.

## Known follow-ups

- **Content seeding** (create collections/records from the brief or sheet) before
  generation, for richer sites.
- Not runtime-tested against live credentials yet — smoke-test the operator
  sign-in + a single `provision_lead_client`, then one `provision_and_generate`,
  before batch use. Generation consumes the operator's AI credits.

The previous API-key content MCP is preserved under [`archive/`](archive/).
