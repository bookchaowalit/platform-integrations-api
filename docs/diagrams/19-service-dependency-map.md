# 19 — Service dependency map

```mermaid
flowchart LR
  subgraph callers["Callers (depend on this service)"]
    SW["Solo Web BFF life-dashboard-web"]
    MCP["integrations-mcp (owner machine)"]
    UP["platform-uptime-worker"]
    GW["platform-api-gateway route integrations"]
  end
  SVC["solo-integrations (Railway)"]
  subgraph runtime["Runtime dependencies"]
    RW["Railway: build, serverless, healthcheck"]
    SEN["Sentry (optional)"]
    FILE["Baked registry + guides"]
    SA["vendor/service-auth (in image)"]
  end
  subgraph trust["Trust dependency"]
    SWKEY["Solo Web signing key pair: public key in Railway variable"]
  end
  subgraph build["Build / CI"]
    GH["GitHub Actions + platform-ci-workflows @87dc5e1c"]
    PY["python:3.12-slim, ghcr.io/astral-sh/uv:0.13.1"]
  end
  subgraph fileReaders["File-level readers (no API call)"]
    HUB["solo-empire Tools Hub tools_hub.py"]
    BB["solo-empire building_block_services.py"]
  end
  SW --> SVC
  MCP --> SVC
  UP --> SVC
  GW -.-> SVC
  SVC --> RW
  SVC --> SEN
  SVC --> FILE
  SVC --> SA
  SA --> SWKEY
  GH --> RW
  PY --> RW
  HUB --> FILE
  BB --> FILE
```

Sources: `server.py`, `Dockerfile`, `pyproject.toml`, `_sentry.py`, `.railway/railway.ts`, `.github/workflows/ci.yml`, `README.md` (Tools Hub, building-block guard, `SOLO_INTEGRATIONS_ROOT`), `integrations_mcp.py`; life-dashboard-web @ `17159a9` `lib/backends.ts`; platform-uptime-worker @ `57f0afb` `src/targets.ts`; platform-api-gateway @ `1f02c2a` `routes.json`

ไม่มี DB, cache, queue หรือ CDN; ไม่มีการเรียก provider ภายนอก ถ้า Sentry ล่ม service ยังทำงาน (capture เป็น best effort)

## Open questions

- gateway route เป็น dependency จริงหรือแค่ registry entry (เส้นประ)
