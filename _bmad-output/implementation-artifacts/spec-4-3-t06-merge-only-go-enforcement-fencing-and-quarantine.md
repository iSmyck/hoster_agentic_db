---
title: 'T06 Merge-only GO enforcement, fencing and quarantine'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/decision-record.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-4-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для запрета direct push/merge, merge-only GO identity, fencing token и recovery_required/quarantine.

**Approach:** Создать T06 harness, который на synthetic fixtures проверяет denial всех non-GO merge/push попыток, GO merge after canonical decision, fencing token validity, recovery/quarantine.

## Boundaries & Constraints

**Always:**
- Only `go-merge-service` identity может merge после canonical accepted decision.
- Direct push/direct merge от human/bot/CI/connector/source denied с нулём writes.
- Per-target fencing token сериализует merge critical section.
- recovery_required/quarantine блокируют новые merges до reconciliation.

**Never:**
- Не использовать real GitLab credentials.
- Не считать privileged Owner bypass за approved managed path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| GO merge after decision | go-merge-service + canonical decision | merge allowed PASS | Without decision → FAIL |
| Direct push human | human push to main | SECURITY_REJECTED FAIL | Applied → FAIL |
| Direct merge human | human merge button | SECURITY_REJECTED FAIL | Merged → FAIL |
| CI/bot merge | ci-bot merge | SECURITY_REJECTED FAIL | Merged → FAIL |
| Owner bypass | gitlab-owner push/merge | INTEGRITY_INCIDENT + quarantine FAIL | Treated as normal → FAIL |
| Invalid fencing token | stale/mismatched token | RECOVERY_REQUIRED FAIL | Merge proceeds → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t06/run_t06_tests.py` — main harness.
- `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml` — enforcement/fencing fixtures.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t06/run_t06_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t06/merge-enforcement-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t06/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `4-3-t06-...` → `done`.

**Acceptance Criteria:**
- [x] Given go-merge-service with canonical accepted decision, when merge requested, then merge allowed.
- [x] Given human/CI/connector direct push or merge, when attempted, then SECURITY_REJECTED with zero main writes.
- [x] Given gitlab-owner bypass, when detected, then integrity incident + target quarantine.
- [x] Given invalid/stale fencing token or recovery_required/quarantine, when merge requested, then blocked.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

Harness reuses T01–T04 reporter/sanitize patterns. Live GitLab/GO checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t06/run_t06_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t06/run_t06_tests.py` -- expected: writes merge-enforcement-results.json and summary.md.
- `python -m json.tool _bmad-output/test-artifacts/t06/merge-enforcement-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t06/` -- expected: no matches.
