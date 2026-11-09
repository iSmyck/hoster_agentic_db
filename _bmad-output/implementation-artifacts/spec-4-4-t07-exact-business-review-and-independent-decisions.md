---
title: 'T07 Exact business review and independent decisions'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/decision-record.schema.json
  - specs/corporate-kb/components/open-webui-fork.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-4-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для business review UI: exact diff, CSRF/Origin, independent decisions, lifecycle views, preview reliability.

**Approach:** Создать T07 harness на synthetic fixtures, моделирующий review UI, browser security controls, lifecycle states, stale base и unreliable preview blocker.

## Boundaries & Constraints

**Always:**
- Review UI показывает exact base_sha/proposal_sha, full diff, rationale/evidence, machine-significant changes.
- Human decision path требует matching Origin header и valid CSRF token.
- Independent approvers решают per exact ProposalVersion; self-approval denied.
- UI явно различает draft/in_review/published/indexed/archived/conflicted/recovery_required.
- Unreliable preview blocks apply/merge.

**Never:**
- Не использовать real browser/credentials.
- Не маскировать recovery_required/conflicted под published/indexed.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Complete review | exact diff + reliable preview | review renders PASS | Missing SHA/diff → FAIL |
| CSRF/Origin valid | matching Origin + CSRF | decision accepted PASS | Missing/mismatch → SECURITY_REJECTED |
| Independent decision | different approver per version | decision allowed PASS | Self-approval → FAIL |
| Lifecycle views | state labels | correct state shown PASS | Masked → FAIL |
| Unreliable preview | preview_reliable=false | apply/merge blocked FAIL | Applied → FAIL |
| Stale base | HEAD advanced | STALE_BASE message FAIL | Silent overwrite → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t07/run_t07_tests.py` — main harness.
- `_bmad-output/test-artifacts/t07/fixtures/scenarios.yaml` — review/csrf/lifecycle fixtures.
- `specs/corporate-kb/contracts/decision-record.schema.json` — canonical decision.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t07/run_t07_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t07/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t07/review-ui-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t07/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `4-4-t07-...` → `done`.

**Acceptance Criteria:**
- [x] Given review request, when UI rendered, then exact base/proposal SHA, full diff, rationale/evidence, and reliable preview shown.
- [x] Given decision request without matching Origin or valid CSRF, when submitted, then SECURITY_REJECTED.
- [x] Given lifecycle state recovery_required or conflicted, when UI rendered, then not masked as published/indexed.
- [x] Given unreliable preview, when apply/merge attempted, then blocked.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

Harness reuses T01–T04 reporter/sanitize patterns. Live browser checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t07/run_t07_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t07/run_t07_tests.py` -- expected: writes review-ui-results.json and summary.md.
- `python -m json.tool _bmad-output/test-artifacts/t07/review-ui-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t07/` -- expected: no matches.
