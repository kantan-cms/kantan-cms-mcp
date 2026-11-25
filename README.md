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
- `regenerate_website(project_id, title, description?, web_baker_id?)` — regenerate an **existing** project's site against its **current** collections (rebuilds the instruction, resets, re-runs, waits). Use this instead of a second `POST /web_baker/`, which 400s (one per project). Granular: `reset_website`, `run_website`.
- `move_project(project_id, destination_tenant_id)` — relocate a project (backend enforces owner-of-both, single-member).
- `hand_over_client(tenant_id, client_email, role="owner")` — invite someone to a tenant.
- `download_website(project_id, out_path, web_baker_id?)` — download the generated website.zip source.
- `upload_website_to_repository(project_id, zip_path, name?, set_as_source?)` — upload an edited zip into the project's Repository store.
- `import_generated_website_to_repository(project_id, name?)` — server-side copy of the generated site into the Repository store.

### Content & apps

- Collections: `list_collections(project_id)`, `create_collection(project_id, name, type, description?, icon?)` (`type` is `blog|form|media|dict|custom`; default fields are seeded, so it's usable immediately), `update_collection(…, name?, description?, icon?)` (type is immutable), `delete_collection(project_id, collection_id)` (cascades fields + records).
- Collection schema (fields): `list_fields(project_id, collection_id)`, `add_field(…, name, type, key?, required?, order?, default_value?, attr?)`, `update_field(…, field_id, …)`, `delete_field(…, field_id)` — shape a collection's fields per site (`type` is a CMS field type; select/tag options go in `attr`).
- Records CRUD: `list_records(project_id, collection_id, page_size?, page_num?)`, `get_record(…, record_id)`, `create_record(project_id, collection_id, data)`, `update_record(…, record_id, data)`, `delete_record(…, record_id)` — `data` maps field `custom_key` → value.
- Records bulk (no per-record app events): `bulk_create_records(project_id, collection_id, records)`, `bulk_update_records(…, records=[{id, data}])`, `bulk_delete_records(…, ids)`.
- `generate_images_to_collection(project_id, collection_id, prompts, aspect_ratio?)` — generate images from `prompts` (one each, max 10/call) with the backend's own image model (Gemini) and store them as records in a **media** collection, so they appear like uploaded media and can seed the site generator's reference images. Billed per image; the collection must be type `media`. Returns `{images:[{id,url,prompt}]}`.
- `list_apps(project_id)` (catalog) / `list_installed_apps(project_id)` / `install_app(project_id, app_id, config?)` (pass `config` to set settings at install) / `configure_app(project_id, installation_id, config)` / `uninstall_app(project_id, installation_id)`.
- `activate_website_app(project_id, mode)` — activate the Website Editor in a mode via MCP (no in-app chooser): `mode` = `generator` (Created by Website Generator) or `editor` (Designed by Website Editor). Installs if needed, idempotent.

### Hosting, deploy & domains

- `enable_hosting(project_id, enabled=True, url?)` — flip the project's hosting-enabled setting (and optionally its URL), i.e. the console's Hosting Settings toggle. `enabled=False` disables.
- `deploy_to_preview(project_id, web_baker_id)` / `deploy_to_live(project_id)` / `get_hosting_status(project_id, web_baker_id)`.
- `delete_preview(project_id)` / `delete_hosting(project_id)` (teardown; Cloudflare domain settings are kept on hosting delete).
- Custom domain: `set_custom_domain(project_id, hostname)` (returns TXT validation records), `list_custom_hostnames(project_id)`, `get_domain_status(project_id, hostname_id)` (TXT ownership + SSL validation records to add to DNS). Note: the fixed CNAME *target* the customer points at isn't surfaced by the backend yet.

### API keys, build env & building a site

- `create_api_key(project_id, name, permissions?, expires_at?)` — generate a project API key; returns the token **once** (permissions default `["*"]`).
- Build env vars (the per-project vault the builder injects at build time): `set_env_var(project_id, key, value, secret?)`, `list_env_vars(project_id)`, `delete_env_var(project_id, key)`.
- `configure_site_env(project_id, key_name?)` — one-shot: make an API key and store `CMS_API_KEY` (secret) + `PROJECT_ID` in the vault, so a built site (e.g. `website-base-astro`) can read the CMS. The builder injects these via `GET /v1/api/build/env` at build time. (`CMS_BASE_URL` is not set — the site defaults it; add it with `set_env_var` if a template needs it.)
- `build_from_repository(project_id, bundle, runtime?, script_file?)` — trigger a Kantan Builder build from a Repository-app zip bundle. Then `deploy_to_preview`/`deploy_to_live` to publish.

To stand up a repo-built site end to end: install the **Builder** and **Repository** apps (`install_app`) → `configure_site_env(...)` → upload the source (`upload_website_to_repository`) → `build_from_repository(...)` → `deploy_to_live(...)`. "Enable hosting" happens implicitly on deploy; enable the **Website Editor** / **Builder** via `install_app` (find ids with `list_apps`).

### Project settings

- `update_project(project_id, name?, description?)` — rename / edit description (members only).
- `get_notifications(project_id)` / `set_notifications(project_id, email?, form_submissions?)` — form-submission notification settings.
- `get_feature_toggles(project_id)` / `set_feature_toggles(project_id, disabled_categories)` — enable/disable app categories.

### Project membership (role-gated)

- `list_project_members(project_id)` / `list_project_roles(project_id)`.
- `connect_user_to_project(project_id, user_id)` — add an existing tenant member (as `member`), `set_project_member_role(project_id, project_user_id, project_role_id)`, `remove_project_member(project_id, project_user_id)`.

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
