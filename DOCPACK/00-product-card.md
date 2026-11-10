---
title: solo-integrations — Product Card
doc_id: CARD-solo-integrations
doc_type: product-card
verdict: invest
version: 0.1
date: 2026-10-11
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
---

# solo-integrations — Product Card

## 1. สรุปคุณค่าในหนึ่งประโยค

เป็นแหล่งจริงของทะเบียนแอป external (`data/external_app_registry.ts`) พร้อม API อ่านอย่างเดียวให้ Tools Hub และตัวตรวจ building-block ใช้

## 2. ปัญหาและผู้ใช้เป้าหมาย

ต้องรู้ว่าระบบเชื่อมกับแอปภายนอกใดบ้างแบบเดียวทั้งระบบ ผู้ใช้คือ solo-empire (Tools Hub) และ agent

## 3. สิ่งที่ทำได้จริงตอนนี้

- `integrations-api` (`server.py`) อ่านอย่างเดียว ตามสัญญาใน `contracts/`
- ไฟล์ทะเบียนหนึ่งบรรทัดต่อ record ใช้โดย solo-empire ผ่าน `SOLO_INTEGRATIONS_ROOT`
- เทสต์ unittest 2 ไฟล์

## 4. หลักฐานสถานะ

| รายการ | ค่า |
|---|---|
| Stack | Python (stdlib server), TypeScript registry |
| Commit | 8 ครั้ง (2026-10-04 ถึง 2026-10-11) |
| ซอร์สโค้ด | 5 ไฟล์ / 902 บรรทัด |
| เทสต์ | 2 ไฟล์ (ไม่ได้รันในงานนี้) |
| CI | ไม่มี workflow |
| Deploy config | `.railway/railway.ts` + `Dockerfile` (ทะเบียนระบุ staged คือยังไม่ deploy) |
| Live URL | ไม่มี |

## 5. คุณค่าและจุดต่าง

- ลดสำเนาทะเบียนซ้ำใน monorepo
- **[สมมติฐาน]** ไม่มีมูลค่าขาย

## 6. ช่องว่างสำคัญ

- ยังไม่ได้ deploy (staged)
- คนอ่านยังพึ่ง checkout พี่น้องบนดิสก์; CI ข้ามเมื่อไม่มี repo

## 7. คำตัดสิน

**`invest`** — เป็นแหล่งจริงของข้อมูลที่ solo-empire ใช้จริงและแก้ได้ที่เดียว จะเปลี่ยนเป็น `showcase` หากทะเบียนถูกย้ายเข้า cell อื่น

## 8. ขั้นต่อไป

1. ตัดสินใจ deploy หรือคงเป็นไฟล์ทะเบียน
2. เพิ่ม CI รัน unittest

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `data/external_app_registry.ts`, `server.py`, `contracts/`
