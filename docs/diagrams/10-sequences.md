# 10 — Sequences

## 1. Owner อ่าน catalog ผ่าน Solo Web BFF

```mermaid
sequenceDiagram
  participant B as Browser
  participant W as Solo Web BFF
  participant H as IntegrationsRequestHandler
  participant A as IntegrationsApi
  participant S as service_auth
  participant R as RegistryStore
  B->>W: GET /api/integrations/v1/integrations?status=live
  W->>W: sign RS256 JWT aud=integrations-api scope=integrations:read
  W->>H: GET /api/v1/integrations?status=live (Bearer)
  H->>H: Origin header absent or allowlisted
  H->>A: handle(GET, path, headers)
  A->>S: check_read_auth(policy, headers)
  alt invalid or wrong scope
    S-->>A: AuthError 401 / 403 / 503
    A-->>H: error envelope
  else valid
    A->>R: snapshot()
    R->>R: stat mtime, parse if changed
    R-->>A: records, metadata
    A-->>H: 200 summary, signals, apps
  end
  H-->>W: JSON, Cache-Control no-store, nosniff
  W-->>B: JSON
```

Sources: `server.py`, `vendor/service-auth/service_auth/__init__.py`; life-dashboard-web @ `17159a9` `lib/backends.ts`, `lib/auth.ts`

## 2. Agent ผ่าน integrations-mcp

```mermaid
sequenceDiagram
  participant AG as Agent
  participant M as StrictMCPServer
  participant T as Toolbox.call
  participant K as mint()
  participant API as solo-integrations
  AG->>M: call_tool integrations.list {q}
  M->>M: model_validate (extra=forbid)
  M->>T: GET /api/v1/integrations params
  T->>K: token()
  K->>K: read key + subject files (mode 600), sign 60 s JWT
  K-->>T: JWT
  T->>API: GET with Bearer
  API-->>T: 200 JSON or 4xx/5xx
  T-->>AG: JSON or fixed "status: reason"
```

Sources: `integrations_mcp.py`, `tests/test_mcp.py`

## 3. Railway deploy healthcheck (/ready)

```mermaid
sequenceDiagram
  participant RW as Railway
  participant A as IntegrationsApi
  participant S as service_auth.readiness
  participant R as RegistryStore
  RW->>A: GET /ready
  A->>S: readiness(policy, environment, store)
  S->>R: snapshot()
  R-->>S: ok or exception
  S-->>A: 200 ready or 503 not_ready (source, auth states)
  A-->>RW: JSON
```

Sources: `railway.toml`, `server.py` `_ready`, `vendor/service-auth/service_auth/__init__.py` `readiness`
