# Core 22 SDLC diagram pack — platform-integrations-api

ชุดภาพ Core 22 ตาม SDLC Diagram Catalog v2 วาดจากโค้ดและ config ใน repo นี้ (ณ `origin/main` `75d28a4`, 2026-10-24; วัดค่า live/Railway/gh เมื่อ 2026-11-04)
repo นี้คือ **read-only Integrations API**: Python stdlib HTTP server บน Railway (Singapore, serverless) ที่แปลง `data/external_app_registry.ts` (106 apps) เป็น JSON ให้ Solo Web `/integrations` และ MCP `integrations.list`; ไม่มี database ไม่เรียก provider

ทุกไฟล์มี `Sources:` ใต้ภาพ และ "Open questions" สำหรับสิ่งที่ยืนยันจากโค้ดไม่ได้

| # | Item | Status | File | Sources read |
|---|---|---|---|---|
| 01 | Business process As-Is / To-Be | done (To-Be = open question) | [01-business-process.md](01-business-process.md) | `README.md`, `PRODUCT.md`, `server.py`, SPEC-001, `DOCPACK/00-product-card.md` |
| 02 | Use cases | done | [02-use-cases.md](02-use-cases.md) | `server.py`, `vendor/service-auth`, `integrations_mcp.py`, uptime `targets.ts` |
| 03 | User flows | done | [03-user-flows.md](03-user-flows.md) | `server.py`, `integrations_mcp.py`, life-dashboard-web `lib/backends.ts`, `modules/integrations/client.tsx` |
| 04 | Traceability (RTM) | done | [04-traceability.md](04-traceability.md) | `PRODUCT.md`, SPEC-001, `tests/*.py`, `ci.yml` |
| 05 | C4 Context | done | [05-c4-context.md](05-c4-context.md) | `PRODUCT.md`, `.railway/railway.ts`, consumer repos |
| 06 | C4 Container | done | [06-c4-container.md](06-c4-container.md) | `Dockerfile`, `.railway/railway.ts`, `service.yaml`, `.mcp.json` |
| 07 | C4 Component | done | [07-c4-component.md](07-c4-component.md) | `server.py`, `integrations_mcp.py`, `_sentry.py` |
| 08 | ADRs | done (5) | [08-adr/](08-adr/) | `service.yaml`, `Dockerfile`, `.railway/railway.ts`, `service_auth`, `integrations_mcp.py`, `_sentry.py` |
| 09 | ERD | done (file + in-memory model; no DB) | [09-erd.md](09-erd.md) | `data/external_app_registry.ts`, `server.py`, contract |
| 10 | Sequences | done (3) | [10-sequences.md](10-sequences.md) | `server.py`, `service_auth`, `integrations_mcp.py` |
| 11 | State machines | done (3) | [11-state-machines.md](11-state-machines.md) | `server.py`, `docs/EXTERNAL-APP-REGISTRY.md`, `service_auth` |
| 12 | API & integrations | reused + extended | [12-api-integration.md](12-api-integration.md) → [`contracts/integrations.v1.md`](../../contracts/integrations.v1.md) | contract, `server.py`, tests |
| 13 | Threat model | done | [13-threat-model.md](13-threat-model.md) | `server.py`, `service_auth`, `integrations_mcp.py`, `_sentry.py`, `Dockerfile` |
| 14 | Backup & DR | done (no data store; RTO/RPO not defined) | [14-backup-dr.md](14-backup-dr.md) | `service.yaml`, `README.md`, Railway variable names |
| 15 | CI/CD pipeline | done | [15-cicd-pipeline.md](15-cicd-pipeline.md) | `ci.yml`, platform-ci-workflows @ `87dc5e1c`, `.railway/railway.ts`, `gh run list` |
| 16 | Deployment | done | [16-deployment.md](16-deployment.md) | `.railway/railway.ts`, `Dockerfile`, `PRODUCT.md`, Railway CLI, live probe |
| 17 | Test coverage matrix | done | [17-test-coverage-matrix.md](17-test-coverage-matrix.md) | `tests/*.py`, `pyproject.toml`, `ci.yml` |
| 18 | Git & release workflow | done | [18-git-release-workflow.md](18-git-release-workflow.md) | `git log`, `gh pr list`, `ci.yml`, SPEC-001 |
| 19 | Service dependency map | done | [19-service-dependency-map.md](19-service-dependency-map.md) | `Dockerfile`, `pyproject.toml`, consumer repos |
| 20 | Observability | done | [20-observability.md](20-observability.md) | `server.py`, `_sentry.py`, uptime worker `monitor.ts`/`targets.ts` |
| 21 | Incident response | done | [21-incident-response.md](21-incident-response.md) | uptime worker, `_sentry.py`, `server.py`, `README.md` |
| 22 | DORA | done (4/5 computed; production recovery time not measurable) | [22-dora.md](22-dora.md) | `git log`, `gh run list`, `railway deployment list` |

## ADR list

- [ADR-0001](08-adr/ADR-0001-registry-file-baked-no-database.md) ทะเบียนเป็นไฟล์ใน repo, bake เข้า image, ไม่มี DB
- [ADR-0002](08-adr/ADR-0002-stdlib-http-server-on-railway-serverless.md) stdlib HTTP server บน Railway serverless + Wait for CI
- [ADR-0003](08-adr/ADR-0003-owner-scoped-rs256-service-jwt.md) Owner-scoped RS256 service JWT (vendored service-auth)
- [ADR-0004](08-adr/ADR-0004-mcp-self-mints-service-token.md) MCP mint token เองต่อ call
- [ADR-0005](08-adr/ADR-0005-opt-in-scrubbed-sentry.md) Sentry opt-in, scrubbed

External repos read (read-only, cited with commit): `bookchaowalit/life-dashboard-web` @ `17159a9`, `platform-uptime-worker` @ `57f0afb`, `platform-api-gateway` @ `1f02c2a`, `platform-ci-workflows` @ `87dc5e1c`
