# 09 — ERD

ไม่มี database (`service.yaml` `writes: []`, `PRODUCT.md` "No database") — persisted data คือไฟล์ทะเบียนที่ bake เข้า image ภาพนี้คือ data model ของไฟล์ + snapshot in-memory + payload

```mermaid
erDiagram
  REGISTRY_FILE ||--o{ SECTION : "// comment headings"
  SECTION ||--o{ APP_RECORD : groups
  APP_RECORD |o--o| GUIDE : "integrations/id or id-prefix/README.md"
  APP_RECORD }o--|| STATUS_DEFINITION : status
  REGISTRY_FILE ||--|| SNAPSHOT_METADATA : "parsed into"
  REGISTRY_FILE {
    string path "data/external_app_registry.ts"
    float mtime "reload key"
  }
  SECTION {
    string label "max 80 chars, default Other"
  }
  APP_RECORD {
    string id PK "kebab-case, unique"
    string name "max 80"
    string category "max 40"
    string status "live mcp_only paused planned"
    string api_docs "https only, max 300"
    string note "optional, max 300"
    string section
    string guide "nullable path"
  }
  GUIDE {
    string path "integrations/name/README.md"
  }
  STATUS_DEFINITION {
    string value PK
    string description
  }
  SNAPSHOT_METADATA {
    string path
    string revision "SHA-256 of file text"
    string modified_at "UTC from mtime"
  }
```

Sources: `data/external_app_registry.ts` (`ExternalAppRecord`), `server.py` (`parse_registry`, `guide_path`, `RegistryStore.snapshot`, `STATUS_DEFINITIONS`, `SAFE_ID_RE`), `contracts/integrations.v1.md`

ค่าจริง ณ `75d28a4`: 106 records — `live` 26, `mcp_only` 3, `paused` 2, `planned` 75 (`grep -c "status: '<s>'" data/external_app_registry.ts`); guide 8 โฟลเดอร์ใน `integrations/` (brave-bookmarks, discord, google, line, microsoft-graph, monday, whatsapp-business, zoom)

นอก service: MCP อ่านไฟล์ owner `~/.config/solo-web/service-private.pem`, `owner-subjects.txt`, `~/.config/empire-platform/client.env` (`integrations_mcp.py`) — ไม่ได้เก็บใน repo
