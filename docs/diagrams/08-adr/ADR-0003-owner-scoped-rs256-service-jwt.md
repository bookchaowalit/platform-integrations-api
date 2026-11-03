# ADR-0003 อ่านได้เฉพาะ owner-scoped RS256 service JWT ที่ Solo Web เซ็น (vendored service-auth)

- Status: accepted (retro-documented)
- Date: 2026-11-04 (visible since `f480a7a`, 2026-10-04)

## Context
API ไม่มีข้อมูลลับ แต่เป็น internal inventory ของ owner และต้องใช้ auth แบบเดียวกับ cell อื่นของ Solo Web

## Decision
`/api/v1/integrations` ต้องมี RS256 JWT: `iss` = `INTEGRATIONS_API_AUTH_ISSUER`, `aud=integrations-api`, `scope=integrations:read`, `tenant_id=owner`, `sub` ใน `INTEGRATIONS_API_AUTH_SUBJECTS`, อายุ ≤ 120 s; ใช้ public key ที่ config ไว้เท่านั้น; config ไม่ครบ = fail closed (503 `reads_disabled`); bind non-loopback โดยไม่มี auth = ไม่ start; static token ใช้ได้เฉพาะ development; `/health`, `/ready` public

## Evidence
- `vendor/service-auth/` (copy ของ `bookchaowalit/platform-auth-sdk`), `pyproject.toml` `[tool.uv.sources]`
- `server.py` `_check_read_auth`, `main()` (`parser.error(... requires valid INTEGRATIONS_API_AUTH_*)`)
- `contracts/integrations.v1.md`, `README.md` "Scoped authorization and readiness"
- `tests/test_server.py::test_scoped_production_auth_and_safe_errors`, `::test_static_token_is_never_production_authorization`

## Consequences
- key rotation = เปลี่ยน public key + restart; token เก่าใช้ไม่ได้
- vendored copy ต้อง re-copy เองเมื่อ platform-auth-sdk เปลี่ยน
