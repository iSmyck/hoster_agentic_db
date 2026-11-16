---
title: 'KBI.2.3 Structure proposal review'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '9271d626b4f6f1f34cf20e7b985664ea4c7e16c1'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-2-2-tree-and-link-proposal-generation.md'
warnings: []
deferred:
  - summary: >-
      Concurrent PATCH on the same proposal_id has no lock; last writer wins.
    evidence: |-
      In-memory store; G1 tests are single-threaded. Locking is extra surface.
    location: >-
      src/kb-ingestion/app/services/structure_proposals.py
    severity: low
  - summary: >-
      Version snapshots are stored internally; GET returns only the current version.
    evidence: |-
      Spec requires versioned edits (version number), not a history API.
    location: >-
      src/kb-ingestion/app/services/structure_proposals.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Предложение дерева из 2.2 эфемерно. Специалист не может открыть preview и версионировать правки `parent_id`/`links` до GO.

**Approach:** In-memory `StructureProposal`. POST создаёт из batch (внутренний propose). GET отдаёт tree preview, links graph и per-document front-matter. PATCH правит parent_id/links и поднимает version. Approve фиксирует `approved` для 2.4.

## Boundaries & Constraints

**Always:**
- `POST /api/kb/v1/ingest/structure/proposals` body = batch-read request. 201: `proposal_id` (uuid hex), `version=1`, `status=in_review`, tree, links_graph, nodes (с `front_matter_draft`), excluded, missing.
- `GET /api/kb/v1/ingest/structure/proposals/{proposal_id}` — текущая версия. 404 `NOT_FOUND`.
- Tree preview: каждый документ; `children` = document_id прямых детей; корни `parent_id=null`.
- Links graph: рёбра `{source_document_id, target_document_id, relation}`.
- Per-document FM: `nodes[].front_matter_draft` исходный convert draft (parent_id/links convert не мутируются).
- `PATCH` body `{nodes: [{document_id, parent_id?, links?}]}`. Неуказанные поля узла не меняются. Новая version = n+1. Если было `approved`, статус снова `in_review`.
- Инварианты PATCH: parent в proposal или null; нет self-parent; нет циклов; link target в proposal, не self, unique. Иначе 400 `STRUCTURE_INVALID`.
- `POST .../proposals/{id}/approve` → `status=approved` (идемпотентно). Пустой proposal (0 nodes) → 400 `EMPTY_PROPOSAL`.
- HTTP `{"code","message"}` в detail.

**Never:**
- Не Git. Не GO submit (2.4). Не auth. Не PostgreSQL. Не LLM.
- Не auto-merge. Не менять ConvertedCorpus FM.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| create+get | two related md | 201 then GET same tree/links/FM | N/A |
| patch parent | child parent_id → null | version 2, tree updated | N/A |
| patch cycle | A parent B, B parent A | отказ | 400 STRUCTURE_INVALID |
| patch unknown id | document_id not in proposal | отказ | 400 STRUCTURE_INVALID |
| missing proposal | random uuid | отказ | 404 NOT_FOUND |
| approve | in_review with nodes | status approved | N/A |
| patch after approve | edit links | version++, status in_review | N/A |

</intent-contract>

## Code Map

- Новый: `app/services/structure_proposals.py` — in-memory store + review service.
- `app/schemas/structure.py` — view/edit models.
- `app/api/router.py` — POST/GET/PATCH/approve.
- `app/main.py` — wire store.
- `tests/test_structure_review.py` — матрица.
- `agent_structurer.propose_tree` — reuse, не дублировать эвристику.

## Tasks & Acceptance

**Execution:**
- `structure_proposals.py` -- persist + version + preview -- AC review
- `router.py` -- REST -- поверхность специалиста
- `test_structure_review.py` -- матрица -- доказательство

**Acceptance Criteria:**
- Given a StructureProposal, when the specialist opens it, then they see tree preview, links graph, and per-document front-matter.
- Given a correction, when the specialist edits parent_id or links, then the proposal is updated and versioned.

## Spec Change Log

- 2026-11-17: POST/GET/PATCH/approve StructureProposal with tree preview, links graph, versioned edits.
- 2026-11-17 review: create validates tree; PATCH rejects empty/duplicate edits; tests for self-parent, self-link, excluded/missing, tree/graph after patch.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: merged — high 0, medium 7, low 5
- findings:
  - `[medium]` `[patch]` PATCH invariants besides cycle untested — self-parent, self-link, duplicate links
  - `[medium]` `[patch]` tree/`links_graph` not asserted after PATCH — tests
  - `[medium]` `[patch]` omitted parent_id on links PATCH untested — prior parent preserved
  - `[medium]` `[patch]` excluded/missing omitted on create tests — `test_create_reports_excluded_and_missing`
  - `[medium]` `[patch]` empty PATCH still bumped version — reject STRUCTURE_INVALID
  - `[medium]` `[patch]` duplicate document_id in PATCH last-wins — reject
  - `[low]` `[patch]` create skipped `_validate_structure` — validate when nodes present
  - `[low]` `[reject]` GO submit in same service — 2.4 on same type, story-scoped tests
  - `[low]` `[defer]` concurrent PATCH lock
  - `[low]` `[defer]` version history API
  - `[low]` `[patch]` schema module docstring stale

## Auto Run Result

- In-memory StructureProposal: create from batch, GET preview, versioned PATCH, approve. Convert FM not mutated.
- Files: `structure_proposals.py`, `schemas/structure.py`, `api/router.py`, `main.py`, `tests/test_structure_review.py`
- Review: patched 6 medium + 2 low; deferred concurrency and history GET; rejected splitting GO submit out of the service module.
- Follow-up: `true`. Residual: no PATCH lock; versions not listed.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 138 passed; ruff clean.
- Commit withheld.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_structure_review.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
