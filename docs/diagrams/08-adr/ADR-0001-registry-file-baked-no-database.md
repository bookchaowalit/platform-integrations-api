# ADR-0001 ทะเบียนเป็นไฟล์ TypeScript ใน repo, bake เข้า image, ไม่มี database

- Status: accepted (retro-documented)
- Date: 2026-11-04 (decision visible since `9fc72f8`, 2026-10-11)

## Context
ทะเบียนแอปภายนอกเคยอยู่ใน solo-empire (`infra/api/`, แล้ว `integrations/`) และถูกอ่านทั้งจาก dashboard, Tools Hub และ agent; ต้องมีสำเนาเดียว

## Decision
`data/external_app_registry.ts` ใน repo นี้คือ canonical copy (หนึ่ง record ต่อบรรทัด); service parse ไฟล์นี้ตรง ๆ, ไม่มี database, `Dockerfile` copy ไฟล์และ `integrations/` เข้า image; parse แบบ strict — record เสียหนึ่งบรรทัด = 503 `registry_unavailable` ทั้งก้อน

## Evidence
- `README.md` ("Source of truth: this repository"), `PRODUCT.md` Positioning ("No database; the registry and guides are baked into the image")
- `service.yaml`: `data.reads: [data/external_app_registry.ts, integrations/]`, `writes: []`
- `Dockerfile`: `COPY data/external_app_registry.ts ...`, `COPY integrations ...`
- `server.py`: `parse_registry`, `RegistryStore`, `except (OSError, ValueError, TypeError)` → 503

## Consequences
- แก้ทะเบียน = commit + deploy ใหม่; ไม่มี write API
- ไม่มีข้อมูล runtime ให้ backup (ดู 14-backup-dr)
- parser แบบ regex ผูกกับรูปแบบบรรทัด: format ผิดทำให้ทั้ง API ใช้ไม่ได้ (ตั้งใจ)
