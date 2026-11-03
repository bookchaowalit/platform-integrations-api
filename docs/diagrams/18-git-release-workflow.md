# 18 — Git & release workflow

```mermaid
gitGraph
  commit id: "87ed80a add integrations-api"
  commit id: "9fc72f8 standalone repo"
  commit id: "7f4923f MCP server"
  branch ci/devsecops-phase1
  commit id: "cefbd30"
  checkout main
  merge ci/devsecops-phase1 id: "1b47219 PR 2"
  branch feat/sentry
  commit id: "a41d4f9"
  checkout main
  merge feat/sentry id: "ff5e3b3 PR 3"
  branch fix/sentry-no-tracing
  commit id: "10f5434"
  checkout main
  merge fix/sentry-no-tracing id: "4f9c8db PR 4"
  branch docs/cd-github-wait-for-ci
  commit id: "3ac4afc"
  checkout main
  merge docs/cd-github-wait-for-ci id: "9a1e09b PR 5"
  branch chore/iac-github-source
  commit id: "fc7f1a1"
  checkout main
  merge chore/iac-github-source id: "eaed646 PR 6"
  commit id: "2280bfc L2 baseline direct"
  commit id: "b38d8e9 certifi fix direct"
  commit id: "75d28a4 SPEC review direct"
```

Sources: `git log origin/main` (31 commits 2026-10-04 → 2026-10-24), `gh pr list -R bookchaowalit/platform-integrations-api --state all` (PR #2–#6 merged, #1 open)

gitGraph แสดง commit ตัวแทนบางตัว ไม่ใช่ทุก commit (PR #3, #4 squash/merge ลง main เป็น commit เดียว)

## How a change reaches production

```mermaid
flowchart LR
  A["Change"] --> B{"Path"}
  B -->|"PR branch"| C["CI on pull_request"]
  C --> D["Merge to main"]
  B -->|"direct commit to main, SPEC-001 main-only"| E["push main"]
  D --> F["CI on push main"]
  E --> F
  F -->|"green"| G["Railway Wait for CI deploys"]
  F -->|"red"| H["No deploy"]
  G --> I["/ready healthcheck, then live"]
```

Sources: `.github/workflows/ci.yml`, `.railway/railway.ts`, `specs/001-l2-baseline/spec.md` ("Main-only: yes"), `README.md` Deploy

- ไม่มี tag / GitHub release; version ใน `pyproject.toml` ยังเป็น `0.1.0`; Sentry `release` = `RAILWAY_GIT_COMMIT_SHA` (`_sentry.py`)
- rollback: redeploy deployment เก่าใน Railway (README)

## Open questions

- นโยบายหลักคือ PR หรือ main-only? ทั้งสองแบบมีใน history
