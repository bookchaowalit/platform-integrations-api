# 03 — User flows

ไม่มี UI ใน repo นี้; UI อยู่ที่ Solo Web (`bookchaowalit/life-dashboard-web` `modules/integrations/client.tsx`) flow ด้านล่างคือ journey ที่วิ่งผ่าน API นี้

## Flow A — Owner เปิดหน้า /integrations ใน Solo Web

```mermaid
flowchart TD
  A["Owner opens Solo Web /integrations"] --> B["Browser calls Solo Web /api/integrations/v1/integrations"]
  B --> C["BFF mints service JWT aud=integrations-api scope=integrations:read"]
  C --> D["GET INTEGRATIONS_API_ORIGIN/api/v1/integrations"]
  D --> E{"Response"}
  E -->|"200"| F["Show summary tiles, filters, app rows, guide links"]
  E -->|"401 / 403"| G["Page asks for access token (memory only)"]
  E -->|"503 registry_unavailable or reads_disabled"| H["Error panel with retry"]
  F --> I["Owner sets status / category / q filter"]
  I --> D
```

Sources: life-dashboard-web @ `17159a9`: `lib/backends.ts` (`integrations`, `INTEGRATIONS_API_ORIGIN`, route `^v1/integrations$`), `lib/auth.ts` (audience/scope), `app/api/[service]/[...path]/route.ts`, `modules/integrations/client.tsx`; this repo: `server.py`, `contracts/integrations.v1.md`

## Flow B — Agent ใช้ MCP tool `integrations.list`

```mermaid
flowchart TD
  A["Agent calls integrations.list {q, category, status}"] --> B{"Arguments valid for strict model?"}
  B -->|"no"| X["Tool error invalid_arguments (no echo)"]
  B -->|"yes"| C{"EMPIRE_TOKEN set?"}
  C -->|"yes"| D["Use ready token"]
  C -->|"no"| E["Read service key + owner subject files (mode 600), sign 60 s RS256 JWT"]
  D --> F["GET /api/v1/integrations with Bearer"]
  E --> F
  F --> G{"HTTP status"}
  G -->|"2xx"| H["Return JSON to agent"]
  G -->|">= 400"| I["Fixed message e.g. 403: forbidden"]
```

Sources: `integrations_mcp.py` (`StrictMCPServer.call_tool`, `Toolbox.call`, `mint`, `failure`), `.mcp.json`, `tests/test_mcp.py`

## Flow C — Owner แก้ทะเบียน

```mermaid
flowchart LR
  A["Edit one line in data/external_app_registry.ts"] --> B["pytest test_real_registry_parses_every_record"]
  B --> C["Push / PR to main"]
  C --> D["CI green"]
  D --> E["Railway deploys new image"]
  E --> F["/api/v1/integrations shows new source.revision"]
  A --> G["task tools-hub:write in solo-empire"]
```

Sources: `README.md`, `tests/test_server.py` (`test_real_registry_parses_every_record`), `.railway/railway.ts`

## Open questions

- ใน production Railway ไม่มี `INTEGRATIONS_API_CORS_ORIGINS` (ชื่อ variable จาก `railway variables`, 2026-11-04) จึงใช้ค่า default localhost:3600 — ยืนยันว่า Solo Web เรียกแบบ server-to-server เท่านั้น (ไม่มี `Origin`) ใช่หรือไม่
