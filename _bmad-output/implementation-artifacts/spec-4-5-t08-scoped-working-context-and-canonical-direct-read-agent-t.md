---
title: 'T08 Scoped working context and canonical direct-read agent tools'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/agent-tools.yaml
  - specs/corporate-kb/contracts/front-matter.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-4-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для scoped agent context, canonical direct reads, citations, cursor revocation.

**Approach:** Создать T08 harness на synthetic fixtures: page/subtree/Space scope narrowing, exact revision SHA, GO-mediated direct read, citations, revoked cursor rejection.

## Boundaries & Constraints

**Always:**
- Agent scope carries stable page ID + exact revision SHA + explicit bounds.
- Model-supplied scope может только сужать server effective scope.
- Direct reads идут через GO at exact revision с bounds/cursor/truncation.
- Read/search results включают citations (revision_sha + document_id).
- Revoked cursor возвращает stale/authz error вместо content.

**Never:**
- Не использовать real agent credentials/GO runtime.
- Не позволять scope widening или прямой не-GO read.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Page scope | server page, model page, exact SHA | valid PASS | Missing SHA → FAIL |
| Scope narrowing | server space, model subtree | valid PASS | Widening → SECURITY_REJECTED |
| Direct read | via GO + bounds + cursor | canonical PASS | Non-GO read → FAIL |
| Citations | read/search with revision/document refs | citations present PASS | Missing citations → FAIL |
| Revoked cursor | cursor after revocation | rejected PASS | Content returned → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t08/run_t08_tests.py` — main harness.
- `_bmad-output/test-artifacts/t08/fixtures/scenarios.yaml` — scope/direct-read/citation fixtures.
- `specs/corporate-kb/contracts/agent-tools.yaml` — agent-tools-v2 catalog.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t08/run_t08_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t08/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t08/agent-context-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t08/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `4-5-t08-...` → `done`.

**Acceptance Criteria:**
- [x] Given server scope and model scope, when compared, then model scope narrows server scope and exact revision SHA present.
- [x] Given direct read request, when routed through GO, then exact revision, bounds, cursor, and explicit truncation returned.
- [x] Given read/search result, when citations checked, then each citation includes revision_sha and document_id.
- [x] Given revoked cursor, when used, then request rejected without returning stale content.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

Harness reuses T01–T04 reporter/sanitize patterns. Live agent/GO checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t08/run_t08_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t08/run_t08_tests.py` -- expected: writes agent-context-results.json and summary.md.
- `python -m json.tool _bmad-output/test-artifacts/t08/agent-context-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t08/` -- expected: no matches.
