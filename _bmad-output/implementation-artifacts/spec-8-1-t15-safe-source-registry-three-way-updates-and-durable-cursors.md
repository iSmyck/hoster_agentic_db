---
title: 'T15 Safe source registry, three-way updates and durable cursors'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/components/ingestion-connectors.md
  - specs/corporate-kb/components/git-orchestrator.md
  - specs/corporate-kb/contracts/proposal-record.schema.json
  - specs/corporate-kb/contracts/decision-record.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-8-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that source bindings advance cursors durably, that three-way curated updates preserve independent source and human changes, that ownership modes are enforced, and that crash replay reconstructs cursor transitions without fabricated state.

**Approach:** Create a T15 harness that exercises synthetic YAML fixtures for the source registry contract, `seen`/`proposed`/`merged` cursor durability, same-hash no-op behavior, at most one outstanding proposal, ownership-mode enforcement (migrated/source_managed/curated/live_operational), source deletion tombstones, and crash replay from durable evidence.

## Boundaries & Constraints

**Always:**
- Source observations advance `seen` only after durable metadata, `proposed` only after a durable MR plus ProposalRecord, and `merged` only after verified Git merge and source-mapping reconciliation.
- Same hash/version is a no-op or returns the existing proposal; at most one outstanding proposal exists per source object.
- `migrated` ignores the old source; `source_managed` denies local edits; `curated` produces a three-way reviewable proposal preserving previous imported base, current human changes and incoming source changes; `live_operational` remains a typed read-only snapshot.
- Source deletion, stale ACL/owner or inaccessible object creates a tombstone/obsolete review through the normal MR path; silent deletion is forbidden.
- Crash replay reconstructs each transition from durable evidence; no fabricated cursor state.

**Never:**
- Do not claim real source connector integration PASS without owner-selected source, sandbox and credentials.
- Do not fabricate cursor state or merge outcomes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Source registry | `space_id`, `source_id`, `repository_id`, ownership mode, origin | Stable binding recorded; mode-appropriate rules enforced | Missing origin / mode mismatch → FAIL |
| Cursor durability | `seen` metadata, `proposed` MR+ProposalRecord, `merged` verified Git merge | Cursor advances only after durable evidence; crash replay reconstructs | Advance without durable evidence → FAIL |
| Same hash no-op | Same `source_version`/`hash` observed twice | No new proposal; returns existing proposal if open | Duplicate proposal created → FAIL |
| One outstanding proposal | New observation while proposal open | `seen` updated; current proposal unchanged until terminates | Second outstanding proposal created → FAIL |
| Ownership modes | `migrated`/`source_managed`/`curated`/`live_operational` | Mode-appropriate edit rights and proposal behavior | Local edit on source_managed / write on live_operational → FAIL |
| Source deletion tombstone | Source object removed or inaccessible | Tombstone/obsolete review MR created; silent delete forbidden | Silent deletion / missing review → FAIL |
| Crash replay | Partial durable evidence after crash | Transition reconstructed from available evidence; unknown stays quarantined | Fabricated state / auto-clear → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t15/run_t15_tests.py` — main harness.
- `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml` — synthetic source registry/cursor scenarios.
- `specs/corporate-kb/contracts/proposal-record.schema.json` — proposal contract.
- `specs/corporate-kb/contracts/decision-record.schema.json` — decision contract.
- `specs/corporate-kb/components/ingestion-connectors.md` — source mode design.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t15/run_t15_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t15/source-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t15/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `8-1-t15-...` → `done`.

**Acceptance Criteria:**
- [x] Given source observations, `seen` advances only after durable metadata, `proposed` only after durable MR+ProposalRecord and `merged` only after verified Git merge and source-mapping reconciliation.
- [x] Given the same source hash/version, the harness returns the existing proposal or no-op and does not create a duplicate.
- [x] Given an open proposal, newer observations update only `seen` until the current proposal terminates; at most one outstanding proposal exists per source object.
- [x] Given ownership modes, `migrated` ignores old source, `source_managed` denies local edits, `curated` produces a three-way reviewable proposal and `live_operational` stays read-only.
- [x] Given source deletion, stale ACL/owner or inaccessible object, a tombstone/obsolete review is created through the MR path and silent deletion is forbidden.
- [x] Given crash replay, each transition is reconstructed from durable evidence and no fabricated cursor state is introduced.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths and live source connector runtime is recorded as BLOCKED.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns via `harness_common.py`; validators operate on synthetic YAML fixtures. Real source connector integration remains BLOCKED pending owner selection.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the Git Orchestrator cursor protocol and source registry contract. It validates that cursor transitions are evidence-gated and reconstructable, that ownership modes constrain edits and that source deletion produces a reviewable tombstone rather than silent removal. Real connector behavior is out of scope for T15.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t15/run_t15_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t15/run_t15_tests.py` -- expected: writes `source-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t15/source-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t15/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
