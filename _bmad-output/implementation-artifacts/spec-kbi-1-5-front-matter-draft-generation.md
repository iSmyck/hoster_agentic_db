---
title: 'KBI.1.5 Front-matter draft generation'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '90c516eff798fc7446ffdad6c2db8582a7dc5dfc'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-1-context.md'
  - '{project-root}/specs/corporate-kb/contracts/front-matter.schema.json'
  - '{project-root}/specs/corporate-kb/contracts/source-origin.schema.json'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Черновик FM-v2 должен быть schema-valid. Сейчас dict собирается, jsonschema в пайплайне нет.

**Approach:** `build_front_matter_draft` всегда валидирует результат против `front-matter.schema.json` (+ origin $ref). `source_managed` без origin / mismatch → ORIGIN_REQUIRED / FRONT_MATTER_INVALID. Запрещённые ключи (`access`, `status`, `owner`) schema `additionalProperties: false`.

## Boundaries & Constraints

**Always:**
- Ключи: schema_version=document-front-matter-v2, id (uuid), title, parent_id=null, ownership_mode, links=[], valid_until=null, archived=false, attachments[], origin (migrated и source_managed).
- origin.ownership_mode == ownership_mode.
- attachments[] shape из $defs.attachment; description.automatic если alt сгенерирован.
- Валидация Draft 2020-12. Отказ → 400 FRONT_MATTER_INVALID или ORIGIN_REQUIRED.
- live_operational не принимается как ownership_mode документа.

**Never:**
- Не заполнять parent_id/links деревом (KBI.2). Не писать Git. Не access в шапке.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| migrated md | convert/run default | draft passes jsonschema; origin.ownership_mode=migrated | N/A |
| with attachments | DOCX + image | attachments[] schema-valid | N/A |
| source_managed no origin | ownership_mode source_managed origin null | 400 ORIGIN_REQUIRED | 400 |
| source_managed mismatch | origin.ownership_mode=migrated | 400 FRONT_MATTER_INVALID | 400 |
| source_managed ok | matching origin | origin present, schema-valid | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/validators/front_matter.py` — constructor, no schema validate.
- `specs/corporate-kb/contracts/front-matter.schema.json`
- `src/kb-ingestion/tests/test_convert.py` — keys only.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/validators/front_matter.py` -- jsonschema validate before return -- closed schema
- `src/kb-ingestion/tests/test_front_matter.py` -- матрица + schema -- доказательство

**Acceptance Criteria:**
- Given converted markdown and attachments, when FM generated, then required v2 keys and schema-valid draft.
- Given source_managed, when FM generated, then origin required and matches ownership_mode.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass (joint 1.4–1.6)
- verdicts: 4 findings touching 1.5 — high 0, medium 0, low 3, false 1, maybe-false 0
- findings:
  - `[low]` `[defer]` curated HTTP path untested — not in 1.5 matrix; allowed by schema
  - `[false]` `[reject]` live_operational must be tested — ConvertRunRequest Literal rejects it (422)
  - `[low]` `[reject]` extra keys access/status/owner HTTP — additionalProperties on schema; generator never emits them
  - `[low]` `[defer]` schema file missing → 500 — contracts are in-repo; wrap OSError later

## Auto Run Result

- Draft validated Draft 2020-12 against front-matter.schema.json. jsonschema+referencing added to project deps.
- Tests: `test_front_matter.py`. 93 pytest. No commit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_front_matter.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
