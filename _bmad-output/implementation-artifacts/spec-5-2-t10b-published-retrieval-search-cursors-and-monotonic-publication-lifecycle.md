---
title: 'T10b Published retrieval, search cursors and monotonic publication lifecycle'
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
  - _bmad-output/implementation-artifacts/spec-5-1-t10a-exact-sha-ci-index-build-and-validated-preflight-artifact.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that the preflight→published lifecycle creates a distinct validated non-preflight artifact, that pointer publication is fenced/CAS per `(space_id, profile_id)`, that per-Space exact/semantic retrieval reauthorizes candidates and cites exact revisions, and that cursor bindings reject stale snapshots/profiles/policies with explicit errors.

**Approach:** Create a T10b harness that exercises synthetic YAML fixtures for publication pairing, pointer CAS/fencing, per-Space retrieval with citations, cursor binding/stale detection, and explicit `INDEX_NOT_READY` / `LIMIT_EXCEEDED` behavior.

## Boundaries & Constraints

**Always:**
- Published lifecycle creates new request/run/snapshot IDs while preserving the same exact SHA, dependency closure, policy triple, and exact/semantic hashes; full validation is repeated.
- The preflight artifact remains `serving_allowed=false` and is never activated or searched.
- Pointer publication uses one fence/CAS register per `(space_id, profile_id)` across all generations; a stale owner updates zero rows.
- Search fan-out is limited to active published snapshots; every candidate and payload is reauthorized; citations include Space, stable document ID, full revision SHA, and section/range.
- Cursors bind the complete ordered per-Space snapshot, profile, policy/group/revocation, and actor-epoch set; stale bindings stop with explicit errors.
- `INDEX_NOT_READY`, `STALE_INDEX_CANDIDATE`, and `LIMIT_EXCEEDED` are returned explicitly; truncation is never silent.

**Never:**
- Do not use real GitLab/PostgreSQL/retrieval credentials or production corpus.
- Do not allow late/old-generation jobs to roll back the active pointer.
- Do not let UI, agents, connectors, webhooks, or GO write the active pointer directly.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Publication lifecycle | Validated inactive preflight artifact | New non-preflight IDs, same SHA/closure/policy/hashes, full validation repeated | Preflight activated or IDs reused → FAIL |
| Pointer CAS/fencing | Concurrent old/new publishers for same `(space_id, profile_id)` | Single writer CAS succeeds; stale job marked superseded, zero rows changed | Stale writer overwrites pointer → FAIL |
| Per-Space retrieval | Active published snapshots and authorized scopes | Reauthorized candidates with citations; exclusions return no payload | Stale/revoked/inactive/cross-space content returned → FAIL |
| Cursor binding | Cursor with snapshot/profile/policy/group/revocation/actor-epoch bindings | Continuation while bindings unchanged; stale binding rejected | Missing/stale epoch silently ignored → FAIL |
| Index not ready | No active snapshot, inactive preflight, bounded page, upstream failure | Explicit `INDEX_NOT_READY` / `STALE_INDEX_CANDIDATE`; `LIMIT_EXCEEDED` with next cursor | Optimistic success or silent truncation → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t10b/run_t10b_tests.py` — main harness.
- `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml` — synthetic publication/retrieval/cursor/error fixtures.
- `specs/corporate-kb/contracts/index-snapshot.schema.json` — canonical `index-snapshot-v1` contract.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t10b/run_t10b_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t10b/retrieval-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t10b/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `5-2-t10b-...` → `done`.

**Acceptance Criteria:**
- [x] Given a validated inactive preflight artifact, the published lifecycle creates separate IDs with the same SHA/closure/policy/hashes and repeats full validation.
- [x] Given concurrent publishers, one fence/CAS register per `(space_id, profile_id)` ensures stale jobs update zero rows and cannot roll back the active pointer.
- [x] Given typed search requests, retrieval fans out only over active published snapshots, reauthorizes every candidate/payload, and returns exact citations.
- [x] Given a cursor, it binds the complete per-Space snapshot/profile/policy/group/revocation/actor-epoch set and stops on stale bindings.
- [x] Given missing active snapshot or inactive preflight, explicit `INDEX_NOT_READY` / stale errors are returned; `LIMIT_EXCEEDED` includes bounds and a next cursor.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes

Harness reuses T01–T09 reporter/sanitize patterns; validators operate on synthetic YAML fixtures. Live PostgreSQL/retrieval/hoster.ai checks remain BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the pointer register as an in-memory CAS comparing `(fence, generation_id, snapshot_sha)` and rejects updates where the expected fence does not match the current fence, the snapshot is not the latest validated published descriptor, or the publisher is not the single CI/index writer. Real object-store ACL and live retrieval quality checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t10b/run_t10b_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t10b/run_t10b_tests.py` -- expected: writes `retrieval-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t10b/retrieval-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t10b/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
