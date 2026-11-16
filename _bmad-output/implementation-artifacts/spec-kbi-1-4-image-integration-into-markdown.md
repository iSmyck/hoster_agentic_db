---
title: 'KBI.1.4 Image integration into Markdown'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '90c516eff798fc7446ffdad6c2db8582a7dc5dfc'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-1-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-1-3-media-extraction-and-classification.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Markdown должен ссылаться на staged object_id, исключать decorative и помечать auto-alt. Тесты 1.3 не сверяют `attachment://{object_id}` с `attachments[].object_id`.

**Approach:** Для каждого non-decorative вложения converter пишет `![alt](attachment://{object_id})` где object_id равен staged `put`. Decorative не в теле. `automatic=true` на сгенерированном alt.

## Boundaries & Constraints

**Always:**
- Ссылка только `attachment://{object_id}` (hex id из store), не URL и не путь файла.
- object_id в markdown == `attachments[].object_id` для того же файла.
- decorative: нет `attachment://` и нет имени watermark/icon/logo в markdown.
- Сгенерированный alt: `automatic=true` в манифесте (и `description.automatic` в FM, если FM уже есть).
- Поверхность: `POST /api/kb/v1/ingest/convert/run`.

**Never:**
- Не OCR, не ручной alt, не vision. Не менять классификатор 1.3. Не Git. Не auth.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| illustrative embed | DOCX figure.png ≥512B | markdown contains `![...](attachment://{id})` matching attachment object_id | N/A |
| decorative | watermark.png | no attachment://, no watermark in markdown | N/A |
| auto alt | any non-decorative | attachments[].automatic is true | N/A |
| png document | scan.png primary | attachment:// present with staged id | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/services/converter.py` — markdown_parts append / skip decorative.
- `src/kb-ingestion/tests/test_convert.py` — PNG проверяет подстроку, не object_id.
- Новый: `src/kb-ingestion/tests/test_markdown_images.py`.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/services/converter.py` -- markdown uses staged object_id -- AC match
- `src/kb-ingestion/tests/test_markdown_images.py` -- вся матрица HTTP -- доказательство

**Acceptance Criteria:**
- Given extracted images with object_id, when Markdown generated, then `![alt](attachment://{object_id})`.
- Given decorative, when Markdown generated, then excluded.
- Given generated alt, when produced, then automatic=true in attachment manifest.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass (joint 1.4–1.6)
- verdicts: 6 findings touching 1.4 — high 0, medium 1, low 3, false 0, maybe-false 0
- findings:
  - `[medium]` `[patch]` blocked media missing attachment:// assert — added in `test_blocked_media_correction_task_one_to_one`
  - `[low]` `[reject]` icon/logo 1.4 HTTP — matrix row is watermark; class covered in 1.3
  - `[low]` `[reject]` test_convert PNG substring leftover — superseded by test_markdown_images
  - `[low]` `[reject]` watermark substring stricter than epic — extra guard, keep
  - `[low]` `[reject]` alt `]` injection — filenames from extractors, not user markdown
  - `[medium]` `[defer]` PDF readable-image HTTP in this slice — covered in test_media 1.3

## Auto Run Result

- Markdown uses staged object_id; decorative skipped; automatic=true. Tests in `test_markdown_images.py`.
- Verification: 93 pytest kb-ingestion, ruff clean. Commit withheld (AGENTS.md).

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_markdown_images.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
