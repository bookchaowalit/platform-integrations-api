# ADR-0004 MCP server mint service JWT เองต่อ call แทน credential อายุยาว

- Status: accepted (retro-documented)
- Date: 2026-11-04 (`7f4923f`, `9edc89d`, 2026-10-12)

## Context
agent ของ owner ต้องอ่าน catalog โดยไม่ผ่อน backend auth

## Decision
`integrations_mcp.py` (stdio) อ่าน signing key ของ Solo Web และ owner subject จากไฟล์ mode 600 ทุกครั้งที่ mint, เซ็น token 60 s fixed `aud`/`scope`; มี `EMPIRE_TOKEN` เป็นทางเลือก; tool ไม่รับ identity argument, argument ที่ไม่รู้จักถูกปฏิเสธก่อนเรียก HTTP, error เป็นข้อความคงที่จาก status

## Evidence
- `integrations_mcp.py` (`mint`, `TOKEN_LIFETIME = 60`, `FORBIDDEN_ARGUMENTS`, `failure`)
- `README.md` "MCP server" (trade-off: key mint ได้ทุก service)
- `tests/test_mcp.py::test_minted_token_is_accepted_by_the_backends_own_verifier`

## Consequences
- key ที่ mint ได้ทุก Solo Web service อยู่บนเครื่อง owner — ใช้เฉพาะเครื่องที่ถือ key อยู่แล้ว (README trade-off)
