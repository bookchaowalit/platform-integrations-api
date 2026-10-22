# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | in review (implemented; owner approval pending) |
| Repository / path | bookchaowalit/platform-integrations-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | Owner (bookchaowalit): pending, see the Wave 2 report owner actions |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / pending owner |

## 1. Problem and intent

- **Problem:** The read-only integrations API projects data/external_app_registry.ts into JSON for Solo Web /integrations; its parsing, overview and routing rules had one combined unittest file, no lockfile, no type check and no coverage gate.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| Lock file and frozen install, CI caller bump, Ruff/mypy config and fixes, rule tests, `PRODUCT.md` | New endpoints or fields; schema changes |

## 3. Behaviour — scenarios

### AC-01 — One bad record rejects the whole registry

- **Given** a registry with one valid record and one record with a missing field, bad id, unknown status, non-https docs link, double-quoted value or unreadable line
- **When** the registry is parsed
- **Then** ValueError is raised and no partial list is returned
- **Test:** `tests/test_registry_parsing.py::test_one_bad_record_rejects_the_whole_registry` · level: unit / API with local fakes

### AC-02 — Duplicate ids reject the registry

- **Given** two records with the same id
- **When** the registry is parsed
- **Then** ValueError duplicate registry id
- **Test:** `tests/test_registry_parsing.py::test_duplicate_ids_reject_the_whole_registry` · level: unit / API with local fakes

### AC-03 — Long values are cut to public limits

- **Given** a record with a 120-char name, 60-char category, 400-char note and docs link
- **When** parsed
- **Then** name 80, category 40, docs and note 300 characters
- **Test:** `tests/test_registry_parsing.py::test_long_values_are_cut_to_their_public_limits` · level: unit / API with local fakes

### AC-04 — Connected counts live plus mcp_only

- **Given** a registry with 2 live, 1 mcp_only, 1 paused, 1 planned
- **When** GET /api/v1/integrations
- **Then** summary.connected is 3 and the counts describe the whole registry
- **Test:** `tests/test_overview_filters.py::test_summary_counts_connected_as_live_plus_mcp_only` · level: unit / API with local fakes

### AC-05 — Filters combine with AND

- **Given** apps in two categories
- **When** category and status are both set
- **Then** only apps matching both are returned
- **Test:** `tests/test_overview_filters.py::test_filters_combine_with_and` · level: unit / API with local fakes

### AC-06 — Over-long filter is a 400

- **Given** a status or category longer than 40 or q longer than 80 characters
- **When** GET /api/v1/integrations
- **Then** 400 invalid_field
- **Test:** `tests/test_overview_filters.py::test_a_filter_longer_than_its_limit_is_a_400` · level: unit / API with local fakes

### AC-07 — Guide found by id or id prefix

- **Given** integrations/gmail and integrations/google guides
- **When** the overview is built
- **Then** gmail and google-calendar get a guide path, zoom gets none
- **Test:** `tests/test_overview_filters.py::test_a_guide_is_found_by_full_id_or_by_the_id_prefix` · level: unit / API with local fakes

### AC-08 — Registry reloads only on mtime change

- **Given** a served registry
- **When** the file changes with the same mtime, then with a new mtime
- **Then** the cached snapshot is served first, the new records after
- **Test:** `tests/test_routes_and_reload.py::test_the_registry_reloads_only_when_its_mtime_changes` · level: unit / API with local fakes

### AC-09 — Unexpected error is a generic 500 sent to Sentry

- **Given** an internal error carrying a database URL
- **When** GET /api/v1/integrations
- **Then** 500 internal_error without the error text; capture() receives the exception
- **Test:** `tests/test_routes_and_reload.py::test_an_unexpected_error_is_a_generic_500_reported_to_sentry` · level: unit / API with local fakes

### AC-10 — Unlisted origin refused

- **Given** the HTTP server with one allowed origin
- **When** a request carries another Origin
- **Then** 403 origin_not_allowed without CORS headers
- **Test:** `tests/test_routes_and_reload.py::test_an_unlisted_origin_is_refused_before_routing` · level: unit / API with local fakes

### AC-11 — Write methods refused

- **Given** the API
- **When** POST, PUT, PATCH or DELETE on /api/v1/integrations
- **Then** 405 method_not_allowed
- **Test:** `tests/test_routes_and_reload.py::test_every_write_method_is_refused_as_read_only` · level: unit / API with local fakes

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| G | E | T |
| G | E | T |
| G | E | T |
| M | C | P |

- **Data model / migration:** N/A — no schema change.
- **Backward compatibility:** same routes and payloads; only tooling, locks, typing fixes and tests changed unless a scenario above says otherwise.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Authorization unchanged; Sentry sends no PII and scrubs tokens/URLs | existing auth tests, Sentry tests |
| Reliability / observability | Reproducible install from the lock file; opt-in Sentry error reporting | image rehearsal before push; Sentry tests |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** unit and API tests with local fakes; no hosted service is called.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "87"` (measured 89.96% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_registry_parsing.py::test_one_bad_record_rejects_the_whole_registry` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-02 | `tests/test_registry_parsing.py::test_duplicate_ids_reject_the_whole_registry` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-03 | `tests/test_registry_parsing.py::test_long_values_are_cut_to_their_public_limits` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-04 | `tests/test_overview_filters.py::test_summary_counts_connected_as_live_plus_mcp_only` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_overview_filters.py::test_filters_combine_with_and` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_overview_filters.py::test_a_filter_longer_than_its_limit_is_a_400` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_overview_filters.py::test_a_guide_is_found_by_full_id_or_by_the_id_prefix` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_routes_and_reload.py::test_the_registry_reloads_only_when_its_mtime_changes` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-09 | `tests/test_routes_and_reload.py::test_an_unexpected_error_is_a_generic_500_reported_to_sentry` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-10 | `tests/test_routes_and_reload.py::test_an_unlisted_origin_is_refused_before_routing` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-11 | `tests/test_routes_and_reload.py::test_every_write_method_is_refused_as_read_only` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |
