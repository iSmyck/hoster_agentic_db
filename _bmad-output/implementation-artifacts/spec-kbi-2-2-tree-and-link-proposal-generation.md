---
title: 'KBI.2.2 Tree and link proposal generation'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '9271d626b4f6f1f34cf20e7b985664ea4c7e16c1'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-2-1-batch-read-of-converted-markdown.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Converted Markdown имеет `parent_id=null` и `links=[]`. Агент должен предложить дерево и стабильные связи, не записывая Git.

**Approach:** `POST /api/kb/v1/ingest/structure/propose` читает batch через 2.1 и детерминированно предлагает `parent_id` и `links[]` (relation=references). Низкая уверенность помечается для человека. Persistence StructureProposal — 2.3.

## Boundaries & Constraints

**Always:**
- Body как batch-read: `space_id`, `client_id`, `markdown_object_ids` (1–256, first-seen unique).
- Узлы только из `documents[]` (ready). Blocked/not_ready → `excluded[]`; unknown/other tenant → `missing[]`.
- `parent_id`: UUID документа из этой пачки или null. Нет self-parent, нет циклов, нет parent вне пачки.
- Группировка: `Path(source_path).parent`. В группе лексикографически первый path — корень группы (`parent_id=null`); остальные дети этого корня.
- Одиночка в каталоге: `parent_id=null`, `confidence=low`, `needs_attention=true`, reason `ambiguous isolation`.
- `links[]`: `{target_document_id, relation=references}` если (a) пересечение title-токенов длиной ≥4 или (b) title цели встречается в markdown источника. Без self-link, unique по target.
- Ребёнок без links при siblings: `confidence=low`, `needs_attention=true`, reason `unlinked sibling`.
- Корень группы с siblings: `confidence=medium` если есть хотя бы одна связь в группе, иначе `low` + attention `unlinked sibling`.
- Ребёнок со связью: `confidence=high`.
- HTTP ошибки как 2.1: EMPTY_BATCH, BATCH_TOO_LARGE, VALIDATION_ERROR.
- Детерминизм: одинаковый вход → одинаковый JSON узлов (порядок nodes = порядок documents batch-read).

**Never:**
- Не LLM/сеть. Не Git. Не GO submit (2.4). Не auth. Не PostgreSQL.
- Не мутировать corpus/front-matter convert-документов.
- Не persist StructureProposal (2.3). Не auto-merge.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| same dir related | two md in `docs/` sharing title token | first is parent null; second parent=first id; links references | N/A |
| same dir unlinked | two md no shared tokens | parent as above; both needs_attention unlinked sibling | N/A |
| singleton | one ready doc | parent null, low, ambiguous isolation | N/A |
| mixed | ready + blocked | blocked excluded, not in nodes | N/A |
| missing | unknown id | missing OBJECT_NOT_FOUND, nodes only ready | N/A |
| empty | [] | отказ | 400 EMPTY_BATCH |
| no self/cycle | any batch | no node.parent_id == own id; DAG | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/services/agent_structurer.py` — `propose_tree` after `batch_read`.
- `src/kb-ingestion/app/schemas/structure.py` — StructureNode, StructureProposalReport.
- `src/kb-ingestion/app/api/router.py` — POST `/api/kb/v1/ingest/structure/propose`.
- `src/kb-ingestion/tests/test_structure_propose.py` — матрица 2.2.
- ConvertedCorpus / converter — не менять (2.1).

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/schemas/structure.py` -- proposal models -- контракт
- `src/kb-ingestion/app/services/agent_structurer.py` -- propose_tree heuristic -- AC parent/links/attention
- `src/kb-ingestion/app/api/router.py` -- POST structure/propose -- поверхность агента
- `src/kb-ingestion/tests/test_structure_propose.py` -- матрица -- доказательство

**Acceptance Criteria:**
- Given a batch of documents, when the agent analyzes content, then it proposes parent_id for each document and links[] between related documents.
- Given ambiguous or conflicting structure, when the agent generates a proposal, then it marks low-confidence nodes for human attention.

## Spec Change Log

- 2026-11-17: POST `/structure/propose` deterministic parent_id/links heuristic.
- 2026-11-17 review: group-wide links for root `medium`; title-in-body fixture; missing FM id; duplicate-id self-parent guard.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: merged — high 0, medium 6, low 4
- findings:
  - `[medium]` `[patch]` group-root confidence used per-node links — `_confidence(..., group_has_links=)`
  - `[medium]` `[patch]` related-path never asserted root `medium` / empty low list — tests
  - `[medium]` `[patch]` title-in-body link untested without token overlap — `test_title_in_body_link_without_token_overlap`
  - `[medium]` `[patch]` missing FM id KeyError — `FRONT_MATTER_INVALID`
  - `[low]` `[patch]` duplicate document UUID could self-parent — skip parent when ids equal
  - `[low]` `[patch]` two-directory groups untested — `test_two_directories_have_independent_roots`
  - `[low]` `[patch]` propose BATCH_TOO_LARGE / not_ready — tests
  - `[low]` `[patch]` spec logs empty — this update
  - `[low]` `[reject]` reject duplicate markdown ids on propose — 2.1 first-seen unique still applies

## Auto Run Result

- Deterministic propose: directory-star parent_id, references links, low-confidence attention. Review patches: group-level root medium, body-title links, FM id guard.
- Files: `agent_structurer.py`, `schemas/structure.py`, `api/router.py`, `tests/test_structure_propose.py`
- Review: patched 4 medium + 4 low; rejected duplicate-id 400.
- Follow-up review: `true` (≥2 medium). Residual: none blocking 2.3.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 120 passed; ruff clean.
- Commit withheld.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_structure_propose.py src/kb-ingestion/tests/test_structure.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
