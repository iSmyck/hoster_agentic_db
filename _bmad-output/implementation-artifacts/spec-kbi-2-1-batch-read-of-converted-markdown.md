---
title: 'KBI.2.1 Batch read of converted Markdown'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '9271d626b4f6f1f34cf20e7b985664ea4c7e16c1'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-1-6-dry-run-report-and-blockers.md'
warnings: []
deferred:
  - summary: >-
      Object-store markdown persist has no delete; if corpus.put fails after store.put
      the markdown object is orphaned. In-memory corpus.put does not fail.
    evidence: |-
      ObjectStore protocol has put/get/get_staged/count only. Rollback would expand the shared adapter.
    location: >-
      src/kb-ingestion/app/services/converter.py
    severity: low
  - summary: >-
      Batch-read accepts non-hex ids and reports them as missing OBJECT_NOT_FOUND
      rather than VALIDATION_ERROR.
    evidence: |-
      Intent requires uuid hex on persist; unknown ids are missing. Format check is extra surface.
    location: >-
      src/kb-ingestion/app/services/agent_structurer.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Агент структуризации не может прочитать пачку convert-результатов: Markdown живёт только в HTTP dry-run, `markdown_object_id` нет. Blocked нельзя надёжно исключить.

**Approach:** `convert/run` сохраняет Markdown в object store и регистрирует документ. `POST /api/kb/v1/ingest/structure/batch-read` по списку `markdown_object_id` возвращает ready-документы (content, attachments, front-matter draft) и отдельно excluded blocked + missing.

## Boundaries & Constraints

**Always:**
- `convert/run` 200: поле `markdown_object_id` (uuid hex), байты markdown в store, запись в corpus registry (space_id/client_id изолированы).
- Batch-read body: `space_id`, `client_id`, `markdown_object_ids` (1–256). Дубликаты обрабатываются один раз в порядке первого появления (не 400).
- `documents[]`: только `status=ready`; каждый элемент: `markdown_object_id`, `markdown`, `attachments`, `front_matter_draft`, `source_path`, `status`.
- `excluded[]`: запрошенные id со `status=blocked` (`reason=blocked`) или иным не-ready статусом (`reason=not_ready`).
- `missing[]`: неизвестный id или чужой space/client → `OBJECT_NOT_FOUND`.
- Порядок `documents` стабилен по порядку запроса, пропуская excluded/missing.
- Ошибки HTTP: `{"code","message"}` в `detail`. Пустой список id → 400 `EMPTY_BATCH`. >256 id → 400 `BATCH_TOO_LARGE`. Пустые `space_id`/`client_id` → 422 `VALIDATION_ERROR`.

**Never:**
- Не предлагать дерево/links (2.2). Не GO submit (2.4). Не Git. Не auth. Не PostgreSQL queue.
- Не включать blocked или not_ready в `documents[]`.
- Не пересчитывать парсеры на read.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ready batch | два convert/run ready id | documents len=2, markdown+FM+attachments, порядок запроса | N/A |
| mixed | ready + blocked ids | ready in documents; blocked in excluded | N/A |
| missing | unknown hex id | missing OBJECT_NOT_FOUND | N/A |
| isolation space | id from other space | missing, not leaked | N/A |
| isolation client | same space, other client_id | missing OBJECT_NOT_FOUND | N/A |
| empty | markdown_object_ids=[] | отказ | 400 EMPTY_BATCH |
| too large | 257 ids | отказ | 400 BATCH_TOO_LARGE |
| duplicates | same id twice | documents len=1, first-seen order | N/A |
| convert persists | convert/run md | markdown_object_id set; store.get reads markdown | N/A |
| not ready | corpus status neither ready nor blocked | excluded reason=not_ready | N/A |
| slash ids | space `a/b` vs `a`+`b/c` | corpus keys do not collide | N/A |
| empty tenant | space_id="" | отказ | 422 VALIDATION_ERROR |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/services/converter.py` — persist markdown object + corpus register; `markdown_object_id` in DryRunReport.
- `src/kb-ingestion/app/schemas/convert.py` — `DryRunReport.markdown_object_id` required.
- `src/kb-ingestion/app/main.py` — wires ConvertedCorpus, AgentStructurer; RequestValidationError → `VALIDATION_ERROR`.
- `src/kb-ingestion/app/services/converted_corpus.py` — in-memory registry; quoted isolation keys.
- `src/kb-ingestion/app/services/agent_structurer.py` — `batch_read`: EMPTY_BATCH, BATCH_TOO_LARGE, ready/excluded/missing.
- `src/kb-ingestion/app/schemas/structure.py` — BatchReadRequest/Report.
- `src/kb-ingestion/app/api/router.py` — `POST /api/kb/v1/ingest/structure/batch-read`.
- `src/kb-ingestion/tests/test_structure.py` — матрица 2.1.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/services/converted_corpus.py` -- in-memory registry -- isolation
- `src/kb-ingestion/app/services/converter.py` -- persist markdown + register -- markdown_object_id
- `src/kb-ingestion/app/services/agent_structurer.py` -- batch_read -- AC exclude blocked
- `src/kb-ingestion/app/api/router.py` -- POST structure/batch-read -- поверхность агента
- `src/kb-ingestion/tests/test_structure.py` -- вся матрица -- доказательство

**Acceptance Criteria:**
- Given list of markdown_object_id, when batch-read, then ready docs have content, attachments, front-matter drafts.
- Given blocked document, when batch-read, then excluded from structuring and reported.
- Given convert/run 200, when store.get(markdown_object_id), then markdown bytes are present.
- Given other space_id or client_id, when batch-read, then the document is missing OBJECT_NOT_FOUND, not leaked.
- Given empty markdown_object_ids, when batch-read, then 400 EMPTY_BATCH.
- Given 257 ids, when batch-read, then 400 BATCH_TOO_LARGE.

## Spec Change Log

- 2026-11-17: persist `markdown_object_id` on convert/run; add batch-read surface.
- 2026-11-17 review: isolation tests, BATCH_TOO_LARGE, not_ready exclusion, quoted corpus keys, VALIDATION_ERROR envelope, exact object-store deltas on DOCX/media.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: 18 findings — high 0, medium 8, low 6, false 0, maybe-false 0 (merged overlapping)
- findings:
  - `[medium]` `[patch]` client_id isolation untested — `test_other_client_not_leaked`
  - `[medium]` `[patch]` 257 ids untested / 422 shape — service `BATCH_TOO_LARGE` + test
  - `[medium]` `[patch]` non-ready corpus status treated as ready — `reason=not_ready` excluded
  - `[medium]` `[patch]` slash in space/client collides corpus keys — `urllib.parse.quote`
  - `[medium]` `[patch]` DOCX/media store count `> before` would miss dropped markdown persist — exact +2/+3 and get(markdown_object_id)
  - `[medium]` `[patch]` empty tenant ids unconstrained — Field min_length + VALIDATION_ERROR handler
  - `[low]` `[patch]` Code Map / AC / logs stale — this spec update
  - `[low]` `[patch]` `test_ready_markdown_report_shape` omitted markdown_object_id — asserted
  - `[low]` `[patch]` agent_structurer unset → AttributeError — HTTP 500 SERVICE_UNAVAILABLE
  - `[low]` `[defer]` store.put then corpus.put orphan (no ObjectStore.delete)
  - `[low]` `[defer]` markdown_object_id hex format not validated on read
  - `[low]` `[reject]` reject duplicate ids as 400 — spec: first-seen unique (G2)
  - `[low]` `[reject]` load markdown from store only — 2.1 registry may hold inline markdown
  - `[medium]` `[patch]` Pydantic 422 vs code/message — handler + BATCH_TOO_LARGE in service

## Auto Run Result

- Persist markdown_object_id on convert/run; batch-read partitions ready / blocked / missing with space+client isolation. Review patches: client isolation, batch cap, not_ready, quoted keys, validation envelope, DOCX store deltas.
- Files: `converter.py`, `converted_corpus.py`, `agent_structurer.py`, `schemas/structure.py`, `api/router.py`, `main.py`, `tests/test_structure.py`, `tests/test_media.py`, `tests/test_convert.py`, `tests/test_dry_run.py`
- Review: patched 8 medium + 3 low; deferred orphan rollback and hex-id format; rejected duplicate-reject and store-only read.
- Follow-up review: `true` (first pass, ≥2 medium patches). Residual: ObjectStore.delete; hex validation.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 106 passed; `uv run ruff check src/kb-ingestion` clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (106)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
