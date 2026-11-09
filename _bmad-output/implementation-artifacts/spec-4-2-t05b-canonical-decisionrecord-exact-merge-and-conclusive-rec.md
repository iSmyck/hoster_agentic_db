---
title: 'T05b Canonical DecisionRecord, exact merge and conclusive recovery'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/decision-record.schema.json
  - specs/corporate-kb/contracts/proposal-record.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-4-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для canonical DecisionRecord note+tag, record_sha256, merge proof, self-approval denial, per-target serialization, merge recovery и guarded retry.

**Approach:** Создать T05b harness на synthetic fixtures: accept/reject/cancel, self-approval matrix, note/tag hash mismatch, merge commit parents/trailers, recovery_required, guarded retry.

## Boundaries & Constraints

**Always:**
- DecisionRecord — один JSON с record_sha256, идентичный в MR note и protected annotated tag `kb-decisions/<decision_id>` на exact proposal_sha.
- Author, version-author, requester не могут self-approve.
- Merge commit: first parent = base_sha, second parent = proposal_sha, trailers Decision-Id; один main write.
- Перед merge GO atomically фиксирует merge_attempted и durable per-target recovery_required.
- Retry только из conclusive failed с тем же decision_id и новым attempt_id.

**Never:**
- Не использовать real GitLab/GO credentials.
- Не считать timeout merged/failed; не разрешать retry из conflicted/invalid/timeout.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid accept/reject | canonical decision record | note+tag/hash consistent PASS | Missing field → FAIL |
| Self-approval | actor == author/version-author/requester | APPROVER_CONFLICT FAIL | Accepted → FAIL |
| Note/tag mismatch | different record_sha256 | DECISION_INVALID FAIL | Merged → FAIL |
| Merge proof | parents + trailers + main writes | proof valid PASS | Wrong parent/trailer → FAIL |
| Per-target serialization | concurrent apply | winner 1 write, loser 0 writes PASS | Both write → FAIL |
| Guarded retry | conclusive failed | retry allowed PASS | Retry from timeout/conflicted → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t05b/run_t05b_tests.py` — main harness.
- `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml` — decision/merge_proof/recovery fixtures.
- `specs/corporate-kb/contracts/decision-record.schema.json` — canonical DecisionRecord.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t05b/run_t05b_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t05b/decision-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t05b/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `4-2-t05b-...` → `done`.

**Acceptance Criteria:**
- [x] Given canonical accepted/rejected decision, when validated, then DecisionRecord note+tag/hash match and proposal_sha exact.
- [x] Given actor equals author/version-author/requester, when decision submitted, then APPROVER_CONFLICT with zero writes.
- [x] Given merge proof, when parents/trailers verified, then first-parent=base, second-parent=proposal, Decision-Id trailer, one main write.
- [x] Given conclusive failed with recovery_required, when guarded retry requested, then allowed with same decision_id and new attempt_id.
- [x] Given timeout or conflicted outcome, when retry requested, then retry denied.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

Harness reuses T01–T04 reporter/sanitize patterns. Live GitLab/GO checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t05b/run_t05b_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t05b/run_t05b_tests.py` -- expected: writes decision-results.json and summary.md.
- `python -m json.tool _bmad-output/test-artifacts/t05b/decision-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t05b/` -- expected: no matches.
