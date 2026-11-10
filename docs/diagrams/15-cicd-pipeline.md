# 15 — CI/CD pipeline

workflow เดียว: `.github/workflows/ci.yml` (`CI`) เรียก reusable workflows ของ `bookchaowalit/platform-ci-workflows` pin ที่ SHA `87dc5e1c` (v1.1.1); runner GitHub-hosted (repo public)

```mermaid
flowchart TD
  P["push to main"] --> CI["workflow CI"]
  PR["pull_request"] --> CI
  WD["workflow_dispatch"] --> CI
  CI --> API["job api: ci-python.yml"]
  CI --> SEC["job security: security.yml"]
  subgraph apijob["api / python (.)"]
    A1["Checkout"] --> A2["setup-uv, Python 3.12"] --> A3["uv sync --frozen --all-extras"] --> A4["Ruff lint"] --> A5["mypy typecheck"] --> A6["pytest"] --> A7["Coverage gate 87%"]
  end
  subgraph secjob["security"]
    S1["gitleaks"]
    S2["semgrep"]
    S3["osv-scanner"]
    S4["trivy-fs"]
  end
  API --> apijob
  SEC --> secjob
  apijob --> GATE{"All check suites green on main?"}
  secjob --> GATE
  GATE -->|"yes"| RW["Railway Wait for CI: build Dockerfile, deploy solo-integrations"]
  GATE -->|"no"| HOLD["No deploy, previous deployment stays"]
  RW --> HC["Healthcheck GET /ready, 30 s, restart ON_FAILURE max 3"]
```

Sources: `.github/workflows/ci.yml`, platform-ci-workflows @ `87dc5e1c` `.github/workflows/ci-python.yml` (steps Checkout, Set up uv and Python, Install dependencies, Lint (Ruff), Typecheck, Test, Coverage gate; Postgres steps not used here) and `security.yml` (jobs `gitleaks`, `semgrep`, `osv-scanner`, `trivy-fs`), `.railway/railway.ts` (`checkSuites: true`), `.railway/railway.ts`, `renovate.json`

อื่น ๆ: concurrency `ci-${{ github.ref }}` cancel-in-progress; `permissions: contents: read`; Renovate จันทร์ก่อน 9 โมง (Asia/Bangkok), group `platform-ci-workflows`

ตัวอย่างจริง: run บน `2280bfc` (2026-10-22) `security / osv-scanner` failure → แก้ด้วย `b38d8e9` (certifi, PYSEC-2026-4320) 16 นาทีต่อมา (`gh run list`)
