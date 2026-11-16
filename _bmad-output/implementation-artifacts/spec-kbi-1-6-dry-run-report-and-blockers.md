---
title: 'KBI.1.6 Dry-run report and blockers'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: '90c516eff798fc7446ffdad6c2db8582a7dc5dfc'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-1-context.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Dry-run должен отдать path_map, attachments, blockers, losses, errors; при блокере — не писать в Git и создать correction task. errors[] сейчас всегда пуст; canonical write только имплицитен.

**Approach:** `DryRunReport` с полным набором полей. Blockers → correction_tasks (docops-correction-task-v1, proposed_draft) 1:1. losses из парсера (empty_page). errors[] для нефатальных сбоев извлечения (например нечитаемый image stream записывается в errors, конвертация продолжается). Никакого git/GO/canonical write в convert/run.

## Boundaries & Constraints

**Always:**
- 200 body: path_map (source_path→object_id исходного файла), attachments[], blockers[], losses[], errors[], front_matter_draft, correction_tasks, status, markdown.
- Blocker MEDIA_VERIFICATION_PENDING → correction_task с тем же blocker_code, document_path=source_path, document_id=FM id, reason=blocker.detail.
- Нет import git / gitlab / ProposalRecord в kb-ingestion convert path. store.put только staging media.
- Fatal format/security остаётся HTTP 400 (не 200 с errors) — как 1.2.

**Never:**
- Не commit, не GO submit, не index write.
- Не менять backup.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ready md | policy.md | path_map, empty blockers/tasks/errors, status ready | N/A |
| pdf empty page | blank pdf | losses kind empty_page | N/A |
| blocked media | handwritten image | blockers + correction_tasks 1:1, status blocked | N/A |
| no git | any convert/run | no git module used; only object-store put for media | N/A |
| unreadable pdf image | XObject get_data fails | 200 with errors[] entry, conversion continues without that image | not HTTP 500 |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/schemas/convert.py` — DryRunReport, CorrectionTaskDraft.
- `src/kb-ingestion/app/services/converter.py` — errors=[] hardcoded; pdf_parser currently raises on get_data fail.
- `src/kb-ingestion/app/api/router.py` — convert_run.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/parsers/pdf_parser.py` -- unreadable image → loss/error not abort -- errors[]
- `src/kb-ingestion/app/services/converter.py` -- pass parsed errors; tasks 1:1 -- report
- `src/kb-ingestion/tests/test_dry_run.py` -- матрица -- доказательство

**Acceptance Criteria:**
- Given completed conversion, when dry-run requested, then path_map, attachments[], blockers[], losses[], errors[].
- Given any blocker, when report generated, then no canonical write and a correction task may be created.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass (joint 1.4–1.6)
- verdicts: 8 findings touching 1.6 — high 0, medium 3, low 3, false 1, maybe-false 0
- findings:
  - `[medium]` `[patch]` two pending media → two tasks untested — `test_two_pending_media_two_correction_tasks`
  - `[medium]` `[patch]` blocked markdown attachment:// untested — assert added
  - `[low]` `[reject]` full docops-correction-task.schema.json — this story is proposed_draft dry-run, not GO persist
  - `[low]` `[defer]` no-git is AST not runtime — convert path has no git symbols
  - `[medium]` `[patch]` XObject get_object fail aborted PDF — try/except continue
  - `[low]` `[defer]` orphaned puts if FM invalid after stage — rollback is extra surface
  - `[false]` `[reject]` blocker KeyError — converter always sets code/detail
  - `[low]` `[reject]` artifact logs empty at review time — filled this pass

## Auto Run Result

- Dry-run fields + 1:1 correction_tasks; unreadable PDF image → errors[] and HTTP 200. No git imports.
- Follow-up true (≥2 medium patches). Residual: Form XObjects; zip lying headers (1.2 deferred).
- Verification: 93 passed, ruff clean. Commit withheld.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_dry_run.py src/kb-ingestion/tests/test_markdown_images.py src/kb-ingestion/tests/test_front_matter.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
