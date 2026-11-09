---
title: 'T07b DocOps review projections, correction tasks and UX telemetry'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/docops-correction-task.schema.json
  - specs/corporate-kb/contracts/docops-review-metadata.schema.json
  - specs/corporate-kb/contracts/docops-correction-api.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-4-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для DocOps review projections, correction-task lifecycle и UX telemetry redaction.

**Approach:** Создать T07b harness на synthetic fixtures: valid_until-driven projections, correction-task open/in_review/resolved/cancelled transitions, telemetry redaction.

## Boundaries & Constraints

**Always:**
- DocOps review metadata projection derives from canonical document-front-matter-v2 valid_until и exact revision SHA.
- Correction task — GO-owned kb_ops record с lifecycle open/in_review/resolved/cancelled, exact document_revision_sha, evidence hash, optional linked MR.
- Invalid transitions (open→resolved without MR/evidence) rejected.
- UX telemetry не содержит raw documents/chunks/queries/tokens/PII.

**Never:**
- Не использовать real GO/kb_ops runtime.
- Correction task не редактирует canonical content напрямую.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid projection | review_required + valid_until + canonical match | PASS | Mismatch → FAIL |
| Removed projection | review_required=false, valid_until=null | PASS | Invalid state → FAIL |
| Create task | open state | PASS | Missing revision → FAIL |
| Open→in_review | linked MR | PASS | Without MR → FAIL |
| Resolve | evidence hash | PASS | No evidence → FAIL |
| Telemetry redaction | no raw doc/query/token | PASS | Leak → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t07b/run_t07b_tests.py` — main harness.
- `_bmad-output/test-artifacts/t07b/fixtures/scenarios.yaml` — DocOps fixtures.
- `specs/corporate-kb/contracts/docops-correction-task.schema.json` — correction task schema.
- `specs/corporate-kb/contracts/docops-review-metadata.schema.json` — review metadata schema.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t07b/run_t07b_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t07b/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t07b/docops-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t07b/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `4-7-t07b-...` → `done`.

**Acceptance Criteria:**
- [x] Given canonical front matter with valid_until, when projection built, then review metadata matches exact revision and state rules.
- [x] Given correction task, when transitioned open→in_review→resolved/cancelled, then each transition validated with revision SHA and evidence/MR.
- [x] Given invalid transition open→resolved without MR/evidence, when attempted, then INVALID_STATE rejected.
- [x] Given UX telemetry event, when inspected, then no raw documents, queries, tokens, or PII present.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

Harness reuses T01–T04 reporter/sanitize patterns. Live GO/kb_ops checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t07b/run_t07b_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t07b/run_t07b_tests.py` -- expected: writes docops-results.json and summary.md.
- `python -m json.tool _bmad-output/test-artifacts/t07b/docops-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t07b/` -- expected: no matches.
