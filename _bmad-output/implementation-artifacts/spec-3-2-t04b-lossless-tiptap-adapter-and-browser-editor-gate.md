---
title: 'T04b Lossless TipTap adapter and browser editor gate'
type: 'feature'
created: '2026-11-08'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'd2c0d072a757808ea891fbf6414f00147679f7a7'
context:
  - specs/corporate-kb/contracts/front-matter.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-3-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для lossless TipTap canonical round-trip и browser editor gate (IME, accessibility, XSS rejection).

**Approach:** Создать T04b harness, который проверяет parse → edit → serialize → parse round-trip для canonical Markdown/front-matter fixtures и валидирует browser gate vectors (IME ordering, screen-reader labels, executable content rejection) на synthetic fixtures.

## Boundaries & Constraints

**Always:**
- Round-trip сохраняет front-matter boundary, stable IDs/links, tables, Cyrillic, ownership/origin, `valid_until`, archive metadata, attachment tuples.
- Source diff содержит только user-intended changes.
- Browser gate: Russian IME ordering preserved, focus/labels exposed, XSS/executable HTML/MDX rejected.
- Evidence в `_bmad-output/test-artifacts/t04b/` и `specs/corporate-kb/evidence/t04b/`.

**Never:**
- Не добавлять realtime collaboration/CRDT в MVP.
- Не использовать real browser automation без sandbox.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Round-trip | Canonical Markdown fixture | LOSSLESS PASS | Construct loss → FAIL |
| Front-matter boundary | Document with front matter | Front matter preserved PASS | Boundary lost → FAIL |
| Cyrillic IME | Composition sequence | Ordering preserved PASS | Reordered → FAIL |
| XSS gate | `<script>`/MDX in content | Rejected before exposure PASS | Allowed → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t04a/run_draft_tests.py` — reference harness pattern.
- `specs/corporate-kb/contracts/front-matter.schema.json` — canonical document constructs.
- `_bmad-output/implementation-artifacts/epic-3-context.md` — TipTap/browser gate decisions.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t04b/run_editor_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t04b/fixtures/` — canonical Markdown round-trip fixtures and browser gate vectors.
- [x] `_bmad-output/test-artifacts/t04b/validators/` — round-trip, front-matter boundary, IME, accessibility, XSS validators.
- [x] `_bmad-output/test-artifacts/t04b/editor-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t04b/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `3-2-t04b-...` → `done`.

**Acceptance Criteria:**
- [x] Given canonical Markdown/front-matter fixture, when parse → edit → serialize → parse round-trip runs, then every required construct is preserved and source diff contains only intended changes.
- [x] Given front-matter boundary fixture, when round-trip runs, then front matter remains closed and intact.
- [x] Given Russian IME composition sequence, when validated, then ordering is preserved.
- [x] Given executable HTML/MDX/XSS payload, when browser gate runs, then it is rejected before exposure/preview/save.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

T04b harness reuse T01-T04a reporters/sanitize. Round-trip validator uses a minimal Python Markdown ↔ front-matter state machine (no real TipTap dependency in T00/T01 toolchain); browser gate vectors are synthetic structural checks. Real browser automation remains BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py` -- expected: write reports.
- `python -m json.tool _bmad-output/test-artifacts/t04b/editor-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t04b/` -- expected: no matches.
