---
title: 'T09 Restricted single-page agent proposal tools'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/agent-tools.yaml
  - specs/corporate-kb/contracts/proposal-record.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-4-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для ограниченных single-page agent proposals, AgentAnchoredPatchChange, forbidden diff/channel negatives, prompt injection data treatment.

**Approach:** Создать T09 harness на synthetic fixtures: propose_create_document, propose_edit_document, forbidden capabilities, prompt injection invariants.

## Boundaries & Constraints

**Always:**
- Agent может только read/search и propose single-page body create или AgentAnchoredPatchChange с required body section.
- Запрещены whole-document replacement, front-matter change, attachments, archive/restore, bulk/subtree, merge/approve/grants/shell/SQL/Git.
- Ambiguous patch rejected с PATCH_AMBIGUOUS.
- Rationale/evidence — untrusted data; они не меняют actor, scope, tools, policy, credentials.

**Never:**
- Не использовать real agent/GO runtime.
- Не допускать channel-specific исключений из deny-by-default.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Single-page create | body-only, no origin/archive | accepted PASS | With origin/archive → FAIL |
| Anchored patch | required body section | accepted PASS | Missing anchor → FAIL |
| Whole-doc replacement | whole_document=true | SECURITY_REJECTED FAIL | Accepted → FAIL |
| Front-matter change | front_matter_change=true | SECURITY_REJECTED FAIL | Accepted → FAIL |
| Ambiguous patch | ambiguous patch | PATCH_AMBIGUOUS FAIL | Accepted → FAIL |
| Forbidden capability | merge/accept/bulk/subtree/... | SECURITY_REJECTED FAIL | Allowed → FAIL |
| Prompt injection | attempt to change actor/scope/tools | rejected PASS | Authority changed → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t09/run_t09_tests.py` — main harness.
- `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml` — agent proposal/ forbidden/ injection fixtures.
- `specs/corporate-kb/contracts/agent-tools.yaml` — agent-tools-v2.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t09/run_t09_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t09/agent-proposal-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t09/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `4-6-t09-...` → `done`.

**Acceptance Criteria:**
- [x] Given body-only single-page create, when proposed, then accepted.
- [x] Given AgentAnchoredPatchChange with required body section, when proposed, then accepted.
- [x] Given whole-document replacement, front-matter change, attachment, archive, bulk/subtree, or merge/approve/grants, when attempted, then rejected.
- [x] Given ambiguous patch, when proposed, then PATCH_AMBIGUOUS rejected.
- [x] Given prompt injection in rationale/evidence attempting actor/scope/tools change, when processed, then authority unchanged and request rejected.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

Harness reuses T01–T04 reporter/sanitize patterns. Live agent/GO checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t09/run_t09_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t09/run_t09_tests.py` -- expected: writes agent-proposal-results.json and summary.md.
- `python -m json.tool _bmad-output/test-artifacts/t09/agent-proposal-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t09/` -- expected: no matches.
