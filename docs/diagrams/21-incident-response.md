# 21 — Incident response

ไม่มี runbook ใน repo; flow นี้ประกอบจากช่องทางที่มีจริง (uptime Telegram, Sentry, Railway healthcheck/rollback, CI gate)

```mermaid
flowchart TD
  A1["uptime worker: integrations-api down (2 failed checks)"] --> TG["Telegram alert to owner"]
  A2["Sentry issue: unexpected 500"] --> SN["Sentry notification (rules not in repo)"]
  A3["Solo Web /integrations shows error panel"] --> OWN["Owner notices"]
  A4["Railway deploy healthcheck /ready fails"] --> RWF["Deploy not promoted, old deployment keeps serving"]
  TG --> T["Triage"]
  SN --> T
  OWN --> T
  T --> Q1{"GET /ready"}
  Q1 -->|"source unavailable"| F1["Registry parse error: fix line in data/external_app_registry.ts"]
  Q1 -->|"auth disabled"| F2["Check Railway variables INTEGRATIONS_API_AUTH_*"]
  Q1 -->|"no answer"| F3["Railway logs / service status, cold start or crash"]
  Q1 -->|"ready but 401/403"| F4["Issuer, subject or key rotation mismatch with Solo Web"]
  F1 --> FIX["Commit to main, CI green, auto deploy"]
  F2 --> RED["Set variable, redeploy"]
  F3 --> RB["Redeploy earlier deployment in Railway"]
  F4 --> RED
  FIX --> V["Verify /health, /ready, uptime recovered message"]
  RED --> V
  RB --> V
  V --> PM["Postmortem: not defined in repo"]
```

Sources: platform-uptime-worker @ `57f0afb` `src/monitor.ts`, `src/worker.ts`; `_sentry.py`; `server.py` error codes; `vendor/service-auth/service_auth/__init__.py` `readiness`; `.railway/railway.ts`; `README.md` (rollback, key rotation)

## Open questions

- ไม่มี postmortem template / severity นิยามสำหรับ service นี้
- Sentry alert rule และผู้รับ notification ไม่อยู่ใน repo
