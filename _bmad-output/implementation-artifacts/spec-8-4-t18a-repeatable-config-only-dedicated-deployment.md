---
title: 'T18a Repeatable config-only dedicated deployment'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/operations.md
  - specs/corporate-kb/database.md
  - specs/corporate-kb/components/git-orchestrator.md
  - specs/corporate-kb/adr/ADR-016-repository-per-space.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-8-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that a second isolated client can be reproduced from the same pinned core and configuration without client code forks or shared security boundaries.

**Approach:** Create a T18a harness that exercises synthetic YAML fixtures for second-client resource isolation, config-only delivery, `ENABLE_DB_MIGRATIONS=False` runtime roles, external migrator ownership, cold startup checks, credential/egress separation and readiness state distinction. Live second-client environment, object store, CI and network perimeter remain BLOCKED.

## Boundaries & Constraints

**Always:**
- Each client receives its own repositories=Spaces, Open WebUI/GO/Identity configuration and adapters, PostgreSQL/index/CI/object storage, immutable assets, secret references, backups, mirrors, network perimeter and egress allowlist, without code edits or a client branch.
- The second client cannot read or write the first client's repositories, history, grants, objects, caches, logs or backups. Personal Notes and ordinary chats retain upstream behavior; branding/notices remain preserved.
- Runtime workers use `ENABLE_DB_MIGRATIONS=False` and non-DDL roles; only the authorized external migrator for each owning component applies and verifies expected migration heads before traffic.
- Cross-schema writes and runtime DDL are denied; empty database is never treated as proof of no merge or external operation.
- Cold startup and isolation smoke checks separate proposal/merge, connector, CI/index and retrieval credentials; default egress is closed except approved routes; startup performs no unapproved download or provider fallback; readiness distinguishes published, indexed and unavailable states.

**Never:**
- Do not create a real second-client environment, object store, CI or network perimeter without separate owner authorization.
- Do not treat config-only repeatability as full T18/G3 acceptance (Epic 8.5 scope).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Resource isolation | Second-client Spaces, DB, index, objects, secrets, backups, egress | All resources isolated from first client; no cross-client read/write | Shared resource / cross-client access → FAIL |
| Config-only delivery | Same pinned core + client config/adapters | Second client deployed without code edits or client branch | Code fork / client branch required → FAIL |
| Migration ownership | Runtime `ENABLE_DB_MIGRATIONS=False`, non-DDL roles | Only authorized external migrator applies/verifies migration heads | Runtime DDL / non-owner migration → FAIL |
| Cold startup | Offline assets, SBOM, config, credential separation | No unapproved downloads; readiness distinguishes published/indexed/unavailable | Unapproved fallback / readiness lie → FAIL |
| Credential/egress separation | Proposal/merge, connector, CI/index, retrieval credentials | Credentials separated; default egress closed except approved routes | Leaked merge credential / open default egress → FAIL |
| Readiness states | published / indexed / unavailable | States reported distinctly; unavailable not masked as published | Inactive preflight / missing index reported as published → FAIL |

</frozen-after-approval>

## Open Questions

- Second-client environment, object store, CI, secrets and network perimeter unavailable until owner authorization.

## Code Map

- `_bmad-output/test-artifacts/t18a/run_t18a_tests.py` — main harness.
- `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml` — synthetic dedicated deployment fixtures.
- `specs/corporate-kb/operations.md` — deployment runbook design.
- `specs/corporate-kb/database.md` — schema ownership and migration rules.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t18a/run_t18a_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t18a/deployment-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t18a/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `8-4-t18a-...` → `done`.

**Acceptance Criteria:**
- [x] Given resource-isolation fixtures, the second client has separate repositories=Spaces, PostgreSQL/index/object storage, secrets, backups, mirrors, network perimeter and egress allowlist and cannot access the first client's resources.
- [x] Given config-only delivery fixtures, the second client is deployed from the same pinned core and configuration without code edits or a client branch.
- [x] Given migration-ownership fixtures, runtime workers have `ENABLE_DB_MIGRATIONS=False` and non-DDL roles, and only authorized external migrators apply/verify expected migration heads before traffic.
- [x] Given cold-startup fixtures, startup performs no unapproved download or provider fallback and verifies offline assets/SBOM/config before readiness.
- [x] Given credential/egress fixtures, proposal/merge, connector, CI/index and retrieval credentials are separated and default egress is closed except approved routes.
- [x] Given readiness fixtures, `published`, `indexed` and `unavailable` states are distinguished and inactive preflight is not reported as published.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths and live second-client deployment is recorded as BLOCKED.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns via `harness_common.py`; validators operate on synthetic YAML fixtures. Live second-client environment/object-store/CI/perimeter remains BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the configuration and isolation invariants required for a repeatable dedicated client deployment. It validates resource separation, migration ownership and cold-startup behavior on synthetic fixtures but does not create or claim PASS for a real second-client environment.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t18a/run_t18a_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t18a/run_t18a_tests.py` -- expected: writes `deployment-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t18a/deployment-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t18a/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
