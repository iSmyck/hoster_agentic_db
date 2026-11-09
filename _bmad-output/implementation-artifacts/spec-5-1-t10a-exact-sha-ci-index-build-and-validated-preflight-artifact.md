---
title: 'T10a Exact-SHA CI index build and validated preflight artifact'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/index-snapshot.schema.json
  - specs/corporate-kb/components/retrieval-indexing.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-5-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that CI builds deterministic index artifacts from exact published `main` SHAs, produces validated inactive preflight artifacts, enforces full/incremental closure equivalence, excludes ineligible content, and rebuilds idempotently without touching canonical Git.

**Approach:** Create a T10a harness that exercises the `index-snapshot-v1` contract on synthetic YAML fixtures: exact-SHA resolution, inactive preflight invariants, snapshot/closure/hash fields, full/incremental equivalence, eligible-content exclusion, and idempotent rebuild under webhook duplication and `kb_index` loss.

## Boundaries & Constraints

**Always:**
- CI resolves and reads exact `main` SHA via read-only credentials; webhook payloads are hints only.
- Preflight artifact has `snapshot_sha == cutover_sha`, `run_type=full`, `purpose=cutover_preflight`, `serving_allowed=false`, and never serves retrieval or activates user access.
- `index-snapshot-v1` separates `snapshot_sha`, `document_revision_sha`, content/dependency hashes, `main_generation`, `index_profile_version`, and the per-Space policy triple.
- Incremental runs become ready only with complete closure, empty `missing_inputs`, matching perimeter/generation/profile/policy, and evidence of an independently validated full run on the same `main_sha`.
- Ineligible content (pending/rejected branches, `inbox`, templates, service files, archived/deleted pages, unverified critical/handwritten media) is excluded from the projection.
- Retry, reconciliation, and rebuild from Git + immutable assets are idempotent and do not roll back canonical merges or create active artifacts.

**Never:**
- Do not use real GitLab/PostgreSQL/CI credentials or production corpus.
- Do not activate a preflight artifact or allow it to serve answers.
- Do not treat SHA lexicographic ordering as generation ordering.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Exact-SHA build | GitLab event or periodic reconciliation with exact `main_sha` and read-only credential | CI resolves exact SHA, builds inactive run | Missing/different SHA or write capability → FAIL |
| Inactive preflight | Frozen `cutover_sha` and valid inputs | Preflight request/run/snapshot with `snapshot_sha == cutover_sha`, `serving_allowed=false` | Activated/serving preflight → FAIL |
| Index-snapshot contract | Full or incremental descriptor with hashes/generation/profile/policy | All required fields present and consistent | Missing inputs / mismatched policy / incomplete closure → FAIL |
| Eligible content exclusion | Mix of eligible docs and inbox/template/service/archived/deleted/unverified/pending/rejected items | Only eligible canonical content in projection | Ineligible item included → FAIL |
| Idempotent rebuild | Duplicate webhook, `kb_index` loss, same SHA replay | No duplicate active snapshot; rebuild reproduces same validated inactive artifact | Rebuild mutates canonical Git or creates active artifact → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t10a/run_t10a_tests.py` — main harness.
- `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml` — synthetic exact-SHA/preflight/closure/exclusion/rebuild fixtures.
- `specs/corporate-kb/contracts/index-snapshot.schema.json` — canonical `index-snapshot-v1` contract.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t10a/run_t10a_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t10a/index-build-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t10a/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `5-1-t10a-...` → `done`.

**Acceptance Criteria:**
- [x] Given an exact published `main` SHA and read-only credential, CI resolves the SHA and builds an inactive run.
- [x] Given a frozen `cutover_sha`, CI produces a full inactive preflight with `snapshot_sha == cutover_sha` and `serving_allowed=false`.
- [x] Given full/incremental inputs, the snapshot records all required SHAs, hashes, generation, profile, and policy triple; incremental requires validated full equivalence.
- [x] Given ineligible content, only eligible canonical documents enter the projection.
- [x] Given lost/duplicate webhooks or `kb_index` loss, rebuild is idempotent and never rewinds canonical Git or activates a preflight.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes

Harness reuses T01–T09 reporter/sanitize patterns; validators operate on synthetic YAML fixtures against the `index-snapshot-v1` schema. Live GitLab/PostgreSQL/CI checks remain BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness enforces semantic cross-field invariants from the schema `x-contract-invariants` block (preflight SHA equality, inactive preflight, full/incremental equivalence evidence, no lexicographic generation ordering). Real object-store ACL verification remains BLOCKED per G0-D16.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t10a/run_t10a_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t10a/run_t10a_tests.py` -- expected: writes `index-build-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t10a/index-build-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t10a/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
