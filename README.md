# Kantan CMS MCP

An MCP server for managing your Kantan CMS tenants and projects and generating
websites — straight from an MCP client (Claude Desktop, claude.ai, Claude Code).
It authenticates with a **per-user MCP key** and acts as **you**, so everything
it creates is owned and billed to your account.

## How it works

Every tool call hits the backend user surface (`/v1/app`) with your MCP key in
an `X-MCP-Key` header. The key resolves to your user, so the same
ownership/quota/subscription rules apply as when you're signed in to the
console. No Supabase credentials, no shared operator account, no direct database
access.

Create your key in the console: **Account → MCP → New key** (shown once).

Provisioning is a clean one-hop — `create tenant` → `create project` **in that
tenant** — and is **idempotent/resumable** via a local JSON ledger keyed by each
lead's `external_key` (else name): re-runs skip finished leads and resume
partial ones, so a batch never duplicates tenants/projects.

## Tools

- `read_lead_clients(path)` — parse an `.xlsx` into rows (review before creating).
- `provision_lead_client(name, project_name?, description?, client_email?, external_key?)` — one lead (tenant + project, no generation).
- `provision_from_excel(path)` — every row; one result each, failures isolated.
- `provision_and_generate(name, brief, project_name?, description?, external_key?)` — create a tenant + project and generate the site **in place**. Blocks until generation finishes (minutes) or times out; resumable. The tenant must have an active subscription to generate (see below).
- `move_project(project_id, destination_tenant_id)` — relocate a project (backend enforces owner-of-both, single-member).
- `hand_over_client(tenant_id, client_email, role="owner")` — invite someone to a tenant.
- `download_website(project_id, out_path, web_baker_id?)` — download the generated website.zip source.
- `upload_website_to_repository(project_id, zip_path, name?, set_as_source?)` — upload an edited zip into the project's Repository store.
- `import_generated_website_to_repository(project_id, name?)` — server-side copy of the generated site into the Repository store.

### Content & apps

- `list_collections(project_id)` / `create_collection(project_id, name, type, description?, icon?)` — `type` is `blog|form|media|dict|custom`; default fields are seeded, so it's usable immediately (e.g. for generation). (Collections have no update/delete on `/v1/app`; `duplicate` is reachable via `kantan_request`.)
- Records CRUD: `list_records(project_id, collection_id, page_size?, page_num?)`, `get_record(…, record_id)`, `create_record(project_id, collection_id, data)`, `update_record(…, record_id, data)`, `delete_record(…, record_id)` — `data` maps field `custom_key` → value.
- `list_apps(project_id)` (catalog) / `list_installed_apps(project_id)` / `install_app(project_id, app_id)` / `configure_app(project_id, installation_id, config)` / `uninstall_app(project_id, installation_id)`.

### Flexible access (escape hatch)

- `list_api_endpoints()` — every `/v1/app` endpoint as `{method, path, summary}` (OpenAPI discovery).
- `kantan_request(method, path, body?, project_id?)` — call **any** `/v1/app` endpoint as the user. `path` is relative to `/v1/app`; pass `project_id` for project-scoped endpoints. Use this for anything without a dedicated tool. The key acts as your full account, so its reach is whatever you can do in the console.

### Generation needs a subscription

`run`/`provision_and_generate` bill the **project's own tenant**. A brand-new
tenant has no subscription, so generation returns `no active subscription` —
subscribe the tenant (or generate in one that's already subscribed) first.

## Architecture (mirrors the backend)

```
kantan_cms_mcp/
  interfaces/tools.py          MCP tools (entrypoints; like views)
  applications/use_cases/      orchestration (provision, hand_over, move, batch)
  domains/                     entities + the KantanApi port
  infras/                      HTTP client (X-MCP-Key + /v1/app) + Excel reader
```

## Run

### With [uv](https://docs.astral.sh/uv/) (recommended — no manual venv)

```
export CMS_BASE_URL=https://api.kantan-cms.dev
export KANTAN_MCP_KEY=mcp_...        # Account → MCP → New key
uv run kantan-cms-mcp
```

Or run it `npx`-style straight from a checkout:

```
uvx --from <absolute path to kantan-cms-mcp> kantan-cms-mcp
```

### With pip

```
pip install -r requirements.txt      # or: pip install .
export CMS_BASE_URL=... KANTAN_MCP_KEY=mcp_...
python main.py                        # or: python -m kantan_cms_mcp
```

### Add to an MCP client

With `uv` (Claude Code example):

```
claude mcp add kantan-cms \
  -e CMS_BASE_URL=https://api.kantan-cms.dev \
  -e KANTAN_MCP_KEY=mcp_... \
  -- uv run --directory <absolute path to kantan-cms-mcp> kantan-cms-mcp
```

Raw config (Claude Desktop etc.):

```json
{
  "mcpServers": {
    "kantan-cms": {
      "command": "uv",
      "args": ["run", "--directory", "<absolute path to kantan-cms-mcp>", "kantan-cms-mcp"],
      "env": {
        "CMS_BASE_URL": "https://api.kantan-cms.dev",
        "KANTAN_MCP_KEY": "mcp_..."
      }
    }
  }
}
```

Plain-Python equivalent: `"command": "python", "args": ["<path>/main.py"]` with
the same `env`. The ledger file defaults to `kantan_mcp_ledger.json` in the
working directory; override with `KANTAN_MCP_LEDGER`.

## Notes

- **Keep your MCP key secret** — it acts as your full account. Revoke it any time
  in the console (Account → MCP).
- Not yet runtime-tested against live credentials — smoke-test key auth, then one
  `provision_lead_client`, then one `provision_and_generate` before batch use.

The previous API-key content MCP is preserved under [`archive/`](archive/).
