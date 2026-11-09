---
title: 'T05a Exact ProposalRecord and ProposalVersion lifecycle'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/proposal-record.schema.json
  - specs/corporate-kb/contracts/front-matter.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-4-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для точного ProposalRecord/ProposalVersion lifecycle, exact base/proposal SHA, idempotency, archive/restore invariants и LIMIT_EXCEEDED errors.

**Approach:** Создать T05a harness, который на synthetic YAML fixtures валидирует proposal lifecycle, idempotency replay/collision, archive/restore invariants и documented limits.

## Boundaries & Constraints

**Always:**
- ProposalRecord содержит exact base_sha/proposal_sha, author/version-author/requester stable IDs, actor_type, run_id для agent.
- Новый commit/rebase создаёт новый ProposalVersion и инвалидирует предыдущий approval.
- Idempotency-Key == payload binding; изменённый payload под тем же ключом → IDEMPOTENCY_KEY_REUSED с нулём writes.
- archived=true iff присутствует archive; restore создаёт новую reviewed версию без archive.
- Evidence count ≤64, rationale ≤10000, idempotency_key ≤255; превышение → LIMIT_EXCEEDED.

**Never:**
- Не использовать real GitLab/GO credentials.
- Не допускать base_sha == proposal_sha или отсутствие run_id для agent actor.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid human proposal | exact base/proposal SHA + principals | ProposalVersion created PASS | Missing field → FAIL |
| Agent proposal | agent actor + run_id | ProposalVersion created PASS | Missing run_id → FAIL |
| Version evolution | supersedes prior version_id | new ProposalVersion, prior approval invalidated PASS | Reuse old version → FAIL |
| Idempotency replay | same key + same payload | existing version returned PASS | Different payload → IDEMPOTENCY_KEY_REUSED |
| Archive invariant | archived flag vs archive object | consistency PASS | Mismatch → FAIL |
| Limits | evidence >64 / rationale >10k / key >255 | LIMIT_EXCEEDED PASS | Silent truncation → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t05a/run_t05a_tests.py` — main harness.
- `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml` — synthetic proposal/idempotency/archive/limits fixtures.
- `specs/corporate-kb/contracts/proposal-record.schema.json` — canonical ProposalRecord.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t05a/run_t05a_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t05a/proposal-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t05a/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `4-1-t05a-...` → `done`.

**Acceptance Criteria:**
- [x] Given exact base/proposal SHA and principals, when proposal created, then new ProposalVersion accepted and main unchanged.
- [x] Given same idempotency key and same payload, when replayed, then existing ProposalVersion returned with no duplicate.
- [x] Given archived flag without archive object or active document with archive, when validated, then invariant violation FAIL.
- [x] Given evidence count >64 or rationale >10000 or key >255, when proposal created, then LIMIT_EXCEEDED with zero writes FAIL.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

Harness reuses T01–T04 reporter/sanitize patterns; validators operate on synthetic YAML fixtures. Live GitLab/GO checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t05a/run_t05a_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t05a/run_t05a_tests.py` -- expected: writes proposal-results.json and summary.md.
- `python -m json.tool _bmad-output/test-artifacts/t05a/proposal-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t05a/` -- expected: no matches.
