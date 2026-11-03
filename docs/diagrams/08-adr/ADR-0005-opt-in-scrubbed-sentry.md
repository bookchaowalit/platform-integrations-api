# ADR-0005 Sentry แบบ opt-in, errors only, scrub secrets/PII

- Status: accepted (retro-documented)
- Date: 2026-11-04 (`ff5e3b3`, `4f9c8db`, 2026-10-18)

## Decision
`init_sentry()` ทำงานเมื่อมี `SENTRY_DSN` เท่านั้น; `traces_sample_rate=None`, `send_default_pii=False`, `include_local_variables=False`, ไม่ส่ง request body/header/query, logging integration ปิด, `before_send` scrub URL password, bearer, JWT; รายงานเฉพาะ 500 ที่ไม่คาดคิดผ่าน `capture()`

## Evidence
- `_sentry.py`, `server.py` (`init_sentry()` at import, `capture(exc)` in `handle`)
- `tests/test_sentry.py`
- Railway variable names (2026-11-04) มี `SENTRY_DSN`, `SENTRY_ENVIRONMENT`

## Consequences
- ไม่มี tracing/performance data; 503 registry และ 4xx ไม่ถูกส่ง Sentry
