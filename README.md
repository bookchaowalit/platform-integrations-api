# platform-integrations-api
Moved out of solo-empire `services/integrations-api` on 2026-10-11 with its history
(subtree split). Owns the external app registry (`data/external_app_registry.ts`, moved
from `infra/api/` and then from solo-empire `integrations/`) and the read-only `/api/v1/integrations` API.
**Source of truth: this repository.** `data/external_app_registry.ts` is the single canonical copy;
edit it here (keep each record on one line). solo-empire reads it from the sibling checkout
(Tools Hub `tools_hub.py`, building-block guard `building_block_services.py`) via the
`bookchaowalit/platform-integrations-api:data/external_app_registry.ts` reference; set
`SOLO_INTEGRATIONS_ROOT` to override the default Book Dev path. Both skip with a warning when the
checkout is absent (CI). After editing, run `task tools-hub:write` in solo-empire to refresh the hub counts.
`vendor/service-auth` is a vendored copy of `bookchaowalit/platform-auth-sdk`.

Docs: `docs/OVERVIEW.md` (integration overview), `docs/INTEGRATION-GUIDE.md`, `docs/EXTERNAL-APP-REGISTRY.md`, `docs/landing-page-integration.md`; per-provider guides live in `integrations/<id>/README.md`; `integrations/google/` also holds the Calendar OAuth setup script (`setup_calendar.py`).

Test: `uv sync --frozen --all-extras && uv run pytest -q` (see [Test](#test))

---

# Solo Empire Integrations API

`integrations-api` is a small read-only backend that turns
[`data/external_app_registry.ts`](data/external_app_registry.ts)
into JSON for the `/integrations` module of `solo-web` (`bookchaowalit/life-dashboard-web`).
The TypeScript registry (canonical in this repository); the service parses its
one-record-per-line literal, adds the matching `integrations/<id>/README.md`
guide when one exists, and reloads when the file changes.

Parsing is strict: an unreadable line, unknown status, non-HTTPS docs link, or
duplicate id makes the route answer `503 registry_unavailable` instead of a
partial list. Keep each record on one line when editing the registry.

## Run

From this repository root:

```bash
uv sync --frozen --no-dev   # installs from uv.lock, including vendor/service-auth
uv run python server.py
```

The default listener is `http://127.0.0.1:3480`. Configure
`INTEGRATIONS_API_HOST`, `INTEGRATIONS_API_PORT`,
`INTEGRATIONS_API_REGISTRY_PATH`, and `INTEGRATIONS_API_CORS_ORIGINS` as
needed. A non-loopback host requires valid scoped JWT configuration and enforces production authorization.

```text
GET /health
GET /api/v1/integrations?status=&category=&q=
```

See the [Integrations API v1 contract](contracts/integrations.v1.md).

## Deploy

This folder is an independent deploy unit described by [`service.yaml`](service.yaml).

Deploys (CD, since 2026-10-18): the Railway service is connected to this repository's `main` with
Railway's Wait for CI (`checkSuites`). A merge to `main` deploys only after the CI and security
checks pass; a failing check leaves production on the previous deployment. Roll back by
redeploying an earlier deployment in Railway. `railway up` is no longer used.
The repository root is the Docker build context; it contains the service, the
vendored `service-auth` dependency (`vendor/service-auth`) and the registry
(`data/external_app_registry.ts`, canonical). The `integrations/<app>/README.md` guides are a snapshot
copied from solo-empire `integrations/` (only the per-app guides; the guides stay owned by solo-empire).

```bash
docker build -t solo-integrations .
```

The image enforces scoped JWT authorization and binds `0.0.0.0`.
`deploy.target` stays `unassigned` until the parent deployment configuration selects a target. See the decentralized services spec in solo-empire (`docs/superpowers/specs/2026-10-04-decentralized-services-and-storage-design.md`).

## Test

```bash
uv sync --frozen --all-extras          # dependencies from uv.lock (vendor/service-auth is a path source)
uvx ruff@0.17.1 check . && uvx ruff@0.17.1 format --check .
uv run mypy .                           # strict on server.py, _sentry.py, integrations_mcp.py
uv run pytest -q --cov                  # CI gates total coverage (see .github/workflows/ci.yml)
```

## Scoped authorization and readiness

[Railway configuration](railway.toml) selects the Dockerfile and `/ready`
health check (30 seconds), with at most 3 restarts after failure. It declares
no region, resources, runtime secret values, or existing cloud deployment.

Railway variable `SENTRY_DSN` turns on error reporting (unset = off, see [_sentry.py](_sentry.py)).

Configure `INTEGRATIONS_API_AUTH_ISSUER` with the exact HTTPS origin of Solo Web,
`INTEGRATIONS_API_AUTH_PUBLIC_KEY` with its PEM RSA public key (at least 2048 bits),
and `INTEGRATIONS_API_AUTH_SUBJECTS` with the comma-separated allowed OIDC owner
subjects. See [.env.example](.env.example); provide configuration at runtime.
The signing private key belongs only to Solo Web and is never copied to this image.

Reads require an RS256 JWT: `iss` matches that origin, `aud=integrations-api`,
`sub` is allowed, `tenant_id=owner`, `scope=integrations:read`, and
`iat`, `nbf`, `exp`, `jti` are required. Lifetime is at most 120 seconds
with 5 seconds clock leeway. The verifier uses only the configured local key
and rejects remote key headers. Key rotation replaces the configured public
key and restarts the service; old signatures then fail. Missing configuration
returns `503 reads_disabled`; invalid tokens return `401 unauthorized`;
a valid token for another owner/tenant/scope returns `403 forbidden`.
Production never accepts `INTEGRATIONS_API_TOKEN`. Partial JWT configuration
fails closed even in development.

`GET /health` is public liveness. `GET /ready` returns 200 only when the
source snapshot parses and JWT configuration is valid; otherwise it returns
503 with safe source/auth states. A local fixture with auth disabled reports
`auth=development`, not deployment readiness. Metadata contains a SHA-256
`revision` of its source snapshot and preserves its original dates.
Atomic source replacement triggers reload. This does not assert provider
freshness or a live deployment.

The listener accepts PaaS `PORT`; explicit `INTEGRATIONS_API_PORT` or `--port`
takes precedence. Package installation is required; no sibling source-path
injection is used at runtime.

## MCP server (`integrations-mcp`)

`integrations_mcp.py` is this service's MCP server (stdio). It is read-only: `integrations.list` (status, category, text). Every tool is one HTTP call to the
deployed or local API; there is no file or database access, no tool takes an identity argument (actor, workspace,
tenant, token, ...), unknown arguments are rejected before any HTTP call, and errors are a fixed message from the HTTP
status (for example `403: forbidden`), never upstream text.

**Auth (backend auth is unchanged).** The API accepts only a 120-second RS256 service JWT from Solo Web
(`aud=integrations-api`, `scope=integrations:read`, `tenant_id=owner`, allowlisted owner `sub`). For local use the MCP mints that same
token itself, per call, as the Solo Web BFF does: it reads Solo Web's signing key and the owner subject from files
(never printed or returned), signs a 60-second token fixed to this service's audience and scope, and sends it as the
bearer. No tool argument can change the subject, audience or scope.

| Variable | Meaning |
|---|---|
| `EMPIRE_INTEGRATIONS_API` | API base URL (env, else `~/.config/empire-platform/client.env`); https, http only on loopback |
| `SOLO_WEB_PUBLIC_ORIGIN` | the JWT issuer: Solo Web's public https origin (not a secret) |
| `SOLO_WEB_SERVICE_KEY_FILE` | default `~/.config/solo-web/service-private.pem`, mode 600 |
| `SOLO_WEB_OWNER_SUBJECTS_FILE` | default `~/.config/solo-web/owner-subjects.txt`, mode 600; the first subject is used |
| `EMPIRE_TOKEN` | optional ready service JWT; used instead of minting (the key is then not read) |

Trade-off: the signing key can mint tokens for every Solo Web service, so only run this MCP as the owner on a machine
that already holds that key. A narrower alternative, if the key must not sit beside agents, is a Solo Web owner-session
endpoint that issues a per-service token; set `EMPIRE_TOKEN` from it and the key is never read.

Run: `uv sync --frozen --all-extras`, then `.venv/bin/integrations-mcp` (see `.mcp.json`).
Tests: `.venv/bin/pytest tests/test_mcp.py` (fake HTTP transport and a throwaway key; the minted token is checked with
the vendored `service_auth` verifier the API uses).
