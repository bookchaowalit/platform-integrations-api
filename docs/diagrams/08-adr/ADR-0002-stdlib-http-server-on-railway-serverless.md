# ADR-0002 Python stdlib HTTP server ใน Docker บน Railway serverless, deploy ด้วย Wait for CI

- Status: accepted (retro-documented)
- Date: 2026-11-04 (serverless `d0a5824` 2026-10-12; CD `3ac4afc` 2026-10-18)

## Context
API เล็ก read-only, traffic ต่ำ (owner คนเดียว)

## Decision
ใช้ `http.server.ThreadingHTTPServer` (ไม่มี web framework); runtime dependency มีแค่ `solo-empire-service-auth` (vendored) และ `sentry-sdk`; build ด้วย `Dockerfile` (`python:3.12-slim`, `uv sync --frozen`), รันบน Railway service `solo-integrations` ที่ `sleepApplication: true`; deploy จาก GitHub `main` เมื่อ check suites ผ่าน

## Evidence
- `server.py` imports; `pyproject.toml` `dependencies`
- `Dockerfile`, `.railway/railway.ts` (`builder = "DOCKERFILE"`, `healthcheckPath = "/ready"`)
- `.railway/railway.ts` (`sleepApplication: true`, `checkSuites: true`, branch `main`)
- `README.md` Deploy section

## Consequences
- request แรกหลัง idle ช้า (`PRODUCT.md`); uptime worker probe ทุกชั่วโมงเพื่อไม่ปลุก service (platform-uptime-worker `SLEEPS`)
- CI แดง = production อยู่ที่ deployment เดิม
