---
title: 'T02 Git-backed document tree and canonical direct read'
type: 'feature'
created: '2026-11-08'
status: 'in-progress'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '788e299a5316c7d5df685a8f11b043ff36135a10'
context:
  - specs/corporate-kb/contracts/front-matter.schema.json
  - specs/corporate-kb/contracts/source-origin.schema.json
  - specs/corporate-kb/contracts/proposal-record.schema.json
  - specs/corporate-kb/contracts/decision-record.schema.json
  - specs/corporate-kb/contracts/index-snapshot.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-2-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для Git-backed document tree и canonical direct read: stable IDs, breadcrumbs, section reads, attachment tuples, archive invariants и path normalization.

**Approach:** Расширить T01 harness новым validator-набором T02, который строит синтетическое дерево Markdown-документов в двух Space-фикстурах и проверяет tree navigation, exact-revision direct read, section anchors, attachment tuples, archive invariants и Unicode/path нормализацию.

## Boundaries & Constraints

**Always:**
- Оставаться thin QA adapter над contracts; не вводить canonical write path.
- Использовать stable opaque `document_id` (UUID) и full Git SHA как revision.
- Проверять whole/section direct read с exact revision SHA, bounds, cursor и explicit `truncated`.
- Проверять attachment tuple `{object_id, version, sha256, size, media_type, source_ref}`.
- Хранить machine output в `_bmad-output/test-artifacts/t02/` и sanitized evidence в `specs/corporate-kb/evidence/t02/`.

**Never:**
- Не реализовывать full AuthZ/ACL enforcement (это E02.2/E02.3/E04.3).
- Не вводить production corpus, migration или real endpoints.
- Не отмечать structural negative checks как `PASS`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path — tree read | Valid Space fixture with 3 Markdown docs | PASS with parent/child, breadcrumbs, stable IDs | Missing fixture → BLOCKED |
| Section direct read | Document with repeated headings | PASS with occurrence index and anchor | Malformed heading → FAIL |
| Attachment tuple | Attachment reference in front matter | PASS with full immutable tuple | Missing sha256/size/media_type → FAIL |
| Archive invariant | `archived=true` with/without archive object | `archived=true` without archive → FAIL; restore without archive → FAIL | Schema error → FAIL |
| Path normalization | `/pricing`, `pricing`, `/pricing/`, `..` | `/pricing` ↔ `pricing` PASS; `/pricing/` and `..` FAIL | — |
| Stable ID after rename | Same `document_id` in moved file | PASS: UUID preserved | UUID changes → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов: scope определён epic context и E02.1 AC._

## Code Map

- `_bmad-output/test-artifacts/t01/run_contract_tests.py` — reference harness pattern.
- `_bmad-output/test-artifacts/t01/validators/` — reference validators (schemas, openapi, links, projection).
- `specs/corporate-kb/contracts/front-matter.schema.json` — document identity, archive, links, attachments.
- `specs/corporate-kb/contracts/source-origin.schema.json` — source ID and ownership modes.
- `specs/corporate-kb/contracts/index-snapshot.schema.json` — index snapshot and cutover semantics.
- `specs/corporate-kb/architecture-spine.md` — Git-native canonical storage, Space ACL, attachment model.
- `_bmad-output/implementation-artifacts/epic-2-context.md` — epic scope and dependencies.

## Tasks & Acceptance

**Execution:**
- [ ] `_bmad-output/test-artifacts/t02/run_document_tests.py` — main harness.
- [ ] `_bmad-output/test-artifacts/t02/fixtures/` — synthetic two-Space Git tree fixtures (`sales/`, `sales-pricing/`) with Markdown + front matter.
- [ ] `_bmad-output/test-artifacts/t02/validators/tree.py` — tree navigation validator (parent/child, breadcrumbs, stable IDs).
- [ ] `_bmad-output/test-artifacts/t02/validators/read.py` — direct read validator (whole/section, revision SHA, bounds, cursor, truncation).
- [ ] `_bmad-output/test-artifacts/t02/validators/attachments.py` — attachment tuple validator.
- [ ] `_bmad-output/test-artifacts/t02/validators/archive.py` — archive invariant validator.
- [ ] `_bmad-output/test-artifacts/t02/validators/paths.py` — path normalization validator (NFC, `..`, separators).
- [ ] `_bmad-output/test-artifacts/t02/document-results.json` + `summary.md` — machine output.
- [ ] `specs/corporate-kb/evidence/t02/summary.md` + `document-results.json` — sanitized evidence.
- [ ] `_bmad-output/implementation-artifacts/sprint-status.yaml` — обновить `2-1-t02-...` → `done` после review.

**Acceptance Criteria:**
- Given two repository-per-Space fixtures with Markdown/front matter documents, when harness runs, then it returns tree with parent/child relationships, stable opaque document IDs, breadcrumbs and stable-ID deep links.
- Given exact canonical document revision, when user reads whole document or section, then response includes exact revision SHA, path/heading context, section anchors with occurrence for repeated headings, bounds, cursor and explicit `truncated=true|false`.
- Given canonical attachments and archive metadata, when UI renders them, then every attachment exposes full immutable tuple and archive invariants hold.
- Given Cyrillic and path fixtures, when validated, then document paths are repository-relative NFC, ambiguous mappings rejected, and source ID `DOC-0001` retains exact case.
- Given completed run, when evidence saved, then no secrets/absolute paths/real endpoints present.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

T02 harness reuse T01 reporters/sanitize patterns:
1. Load two Space fixtures as in-memory Git-like trees.
2. Parse front matter from each Markdown file; validate `document_id`, `archive`, `links`, `attachments`.
3. Build parent/child index; verify stable IDs survive rename/move fixtures.
4. Direct read: extract whole document or section by heading, compute bounds/cursor/truncation.
5. Attachment/archive/path validators produce PASS/FAIL/BLOCKED checks.
6. Report with project-root-relative paths, SHA-256, rerun commands.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t02/run_document_tests.py --dry-run` -- expected: parse fixtures, list checks, exit 0.
- `uv run python _bmad-output/test-artifacts/t02/run_document_tests.py` -- expected: PASS/FAIL/BLOCKED counts, write reports.
- `python -m json.tool _bmad-output/test-artifacts/t02/document-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t02/` -- expected: no matches.

**Manual checks:**
- `specs/corporate-kb/evidence/t02/summary.md` содержит counts и top findings.
- `specs/corporate-kb/evidence/t02/document-results.json` содержит `secrets_included: false`.
