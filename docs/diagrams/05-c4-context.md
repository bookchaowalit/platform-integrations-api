# 05 — C4 Context

```mermaid
C4Context
  title System Context - platform-integrations-api
  Person(owner, "Owner", "Solo Empire owner")
  System(integ, "Integrations API", "Read-only JSON projection of the external app registry")
  System_Ext(soloweb, "Solo Web", "life-dashboard-web, /integrations module and BFF")
  System_Ext(agent, "Owner agent", "Claude Code with integrations-mcp stdio")
  System_Ext(uptime, "platform-uptime-worker", "Cloudflare Worker health probe")
  System_Ext(sentry, "Sentry", "Error reporting when SENTRY_DSN is set")
  System_Ext(railway, "Railway", "Build, deploy, healthcheck")
  System_Ext(github, "GitHub", "Repo, Actions CI, Wait for CI source")
  System_Ext(hub, "solo-empire tooling", "Tools Hub, building-block guard")
  Rel(owner, soloweb, "Opens /integrations")
  Rel(soloweb, integ, "GET /api/v1/integrations", "HTTPS + RS256 JWT")
  Rel(owner, agent, "Asks")
  Rel(agent, integ, "GET /api/v1/integrations", "HTTPS + self-minted JWT")
  Rel(uptime, integ, "GET /health hourly", "HTTPS")
  Rel(integ, sentry, "Unexpected errors", "HTTPS")
  Rel(github, railway, "main after CI passes")
  Rel(railway, integ, "Runs container, probes /ready")
  Rel(hub, github, "Reads data/external_app_registry.ts from sibling checkout")
```

Sources: `PRODUCT.md`, `README.md`, `server.py`, `_sentry.py`, `integrations_mcp.py`, `.railway/railway.ts`, `railway.toml`; life-dashboard-web @ `17159a9` `lib/backends.ts`; platform-uptime-worker @ `57f0afb` `src/targets.ts` (`integrations-api`, `SLEEPS`)

หมายเหตุ: API **ไม่** เรียก provider ภายนอกใด ๆ (Google, GitHub ฯลฯ) — ลิงก์ `apiDocs` เป็นแค่ข้อความ; ตัวเดียวที่มีการเรียก Google คือ `integrations/google/setup_calendar.py` ซึ่งเป็น owner script local ไม่ได้อยู่ใน image

## Open questions

- gateway (`gateway.bookchaowalit.com`) มี route `integrations` แต่ไม่ได้วาดเป็น caller เพราะยังไม่เห็น caller จริง
