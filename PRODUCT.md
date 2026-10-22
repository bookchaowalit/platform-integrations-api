# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through the `/integrations` module of Solo Web
  (`bookchaowalit/life-dashboard-web`), which calls this API through its BFF with a short-lived
  service JWT.
- The owner's agents, through this repository's read-only MCP server (`integrations-mcp`,
  tool `integrations.list`).
- solo-empire tooling (Tools Hub `tools_hub.py`, the building-block guard) reads
  `data/external_app_registry.ts` from a sibling checkout; it does not call the API.

## Product Purpose

One list of the external apps worth connecting to Solo Empire, each with a status (`live`,
`mcp_only`, `paused`, `planned`), category, API docs link and, when one exists, the setup guide
under `integrations/<id>/README.md`. The service turns the TypeScript registry into JSON with
summary counts so the owner can see what is connected and what is only planned.

Success: the `/integrations` page shows every registry record, the counts match the registry file,
and a broken registry edit shows as `503 registry_unavailable` instead of a partial list.

## Positioning

A small, read-only projection, not a connector: it never reads provider credentials or calls a
provider, and every payload says a listed app is not proof of a working connector. The registry
file in this repository is the single canonical copy. No database; the registry and guides are
baked into the image.

## Operating Context

- Production: `https://solo-integrations-production.up.railway.app` (`/health`; Railway health
  check `/ready`), Railway project `platform-integrations-api`, service `solo-integrations`,
  Singapore, serverless (the first read after idle is slower). Deployed when `main` changes, after
  CI and security checks pass.
- Monitored by `platform-uptime-worker` (`integrations-api`); errors go to Sentry when
  `SENTRY_DSN` is set, without personal data.
- Registry today: 106 apps in 34 categories (26 live, 3 mcp_only, 2 paused, 75 planned), and 8
  setup guides.

## Capabilities and Constraints

- `GET /health`: public liveness. `GET /ready`: 200 only when the registry parses and the JWT
  configuration is valid.
- `GET /api/v1/integrations?status=&category=&q=`: summary (total, matched, categories,
  connected = live + mcp_only, per status, with guide), status/category/section signals, source
  metadata (SHA-256 revision, modified time, status definitions) and the matched apps. Filters
  combine with AND; `q` matches id, name, category and note, case-insensitive. `status` and
  `category` are at most 40 characters, `q` at most 80 (400 `invalid_field`).
- Reads need an RS256 JWT from Solo Web: `aud=integrations-api`, `scope=integrations:read`,
  `tenant_id=owner`, an allowlisted `sub`, at most 120 seconds. Missing configuration is 503
  `reads_disabled`, a bad token 401, another owner, tenant or scope 403. A static token is never
  accepted in production; a non-loopback bind refuses to start without valid auth configuration.
- Read-only: other methods on the route are 405; unknown routes 404; unexpected errors are a
  generic 500 reported to Sentry. CORS is limited to `INTEGRATIONS_API_CORS_ORIGINS`.
- Strict parsing: one record per line; an unknown status, a non-HTTPS docs link, an unsafe id, a
  missing field or a duplicate id rejects the whole registry. Names are cut to 80 characters,
  categories to 40, docs links and notes to 300. The registry reloads when its file changes.
- Out of scope: provider health, credentials, syncing data from providers, and editing the
  registry through the API.

## Measures

- Registry parse failures in production (503 `registry_unavailable`; target: 0).
- 5xx rate and uptime on `/health` (Sentry and `platform-uptime-worker`).
- Share of registry apps that are `live` or `mcp_only`, and of apps with a setup guide
  [ต้องยืนยัน: no target set].
