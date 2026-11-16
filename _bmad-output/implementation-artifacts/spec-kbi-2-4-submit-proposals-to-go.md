---
title: 'KBI.2.4 Submit proposals to GO'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '9271d626b4f6f1f34cf20e7b985664ea4c7e16c1'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-2-3-structure-proposal-review.md'
  - '{project-root}/specs/corporate-kb/contracts/proposal-record.schema.json'
warnings: []
deferred:
  - summary: >-
      Sequential GO submit is fail-fast: earlier documents may already be sent if a later call fails.
    evidence: |-
      No compensation/rollback against GO. Retry uses idempotency_key.
    location: >-
      src/kb-ingestion/app/services/structure_proposals.py
    severity: medium
  - summary: >-
      GO payload is the MVP ProposalSubmitRequest envelope, not full proposal-record.schema.json.
    evidence: |-
      git-orchestrator POST /proposals accepts proposal_data dict; expanding the GO contract is out of kb-ingestion G1.
    location: >-
      src/kb-ingestion/app/adapters/go_client.py
    severity: low
  - summary: >-
      HttpGOClient is unused in create_app; tests inject StubGOClient. Live GitLab/GO is not claimed.
    evidence: |-
      Default wiring is StubGOClient. No live GO evidence.
    location: >-
      src/kb-ingestion/app/main.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Одобренное дерево не попадает в GO: нет ProposalRecord на документ с `base_sha` / `author_stable_id` / `requester_stable_id`. Невалидный FM может уйти в Git.

**Approach:** `POST /api/kb/v1/ingest/structure/proposals/{id}/submit` только для `status=approved`. На каждый node — один вызов GO `POST /api/kb/v1/proposals` через stub/HTTP client. Перед вызовом merge `parent_id`/`links` в копию FM и jsonschema; отказ `FRONT_MATTER_INVALID` без GO.

## Boundaries & Constraints

**Always:**
- Submit body: `base_sha` (40 hex), `author_stable_id`, `requester_stable_id`; `target_branch` default `main`.
- Только `approved`. Иначе 400 `NOT_APPROVED`. 404 если proposal нет.
- Один ProposalRecord на document: payload содержит `base_sha`, `author_stable_id`, `requester_stable_id`, `front_matter` (merged), `document_id`, `markdown_object_id`.
- `proposal_sha` = sha1 hex of canonical per-document payload (40 chars). `idempotency_key` = `{structure_proposal_id}:{document_id}`.
- Validate merged FM via front-matter-v2 schema. Invalid → 400 `FRONT_MATTER_INVALID`, ни одного GO вызова.
- GO ошибка → 502 `GO_SUBMIT_FAILED`.
- Ответ: submissions[] с `document_id`, `go_proposal_id`, `proposal_sha`, `base_sha`, author/requester ids.
- Stub GO в тестах. Не live GitLab.

**Never:**
- Не auto-merge (ADR-018 structure запрещён). Не Git write из kb-ingestion.
- Не submit `in_review`. Не auth. Не PostgreSQL queue.
- Не мутировать convert corpus.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| approved two docs | approved proposal + base_sha + stable ids | two GO submit_proposal calls, ids in response | N/A |
| not approved | in_review | GO not called | 400 NOT_APPROVED |
| invalid FM | extra key / bad parent in merged FM | GO not called | 400 FRONT_MATTER_INVALID |
| missing | unknown proposal_id | GO not called | 404 NOT_FOUND |
| GO fail | stub raises | отказ | 502 GO_SUBMIT_FAILED |

</intent-contract>

## Code Map

- Новый: `app/adapters/go_client.py` — port + StubGOClient (+ HttpGOClient unused in tests).
- `app/services/structure_proposals.py` — `submit`.
- `app/validators/front_matter.py` — public `validate_front_matter_draft`.
- `app/schemas/structure.py` — submit request/response.
- `app/api/router.py` — POST submit.
- `app/main.py` — inject GO client.
- `tests/test_structure_submit.py` — матрица.

## Tasks & Acceptance

**Execution:**
- `go_client.py` -- stub submit -- без live GO
- `structure_proposals.submit` -- FM validate + per-doc ProposalRecord fields -- AC
- `test_structure_submit.py` -- матрица -- доказательство

**Acceptance Criteria:**
- Given an approved StructureProposal, when submit is triggered, then GO receives one ProposalRecord per document with correct base_sha, author_stable_id, requester_stable_id.
- Given a proposal with invalid front-matter, when submit is triggered, then it is rejected with FRONT_MATTER_INVALID.

## Spec Change Log

- 2026-11-17: POST submit approved proposals; stub GO; FM validate before any call.
- 2026-11-17 review: canonical proposal_sha includes author/requester/markdown_object_id; format-check FM uuid; GO missing-id and empty submit guards.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: merged — high 0, medium 6, low 6
- findings:
  - `[medium]` `[patch]` proposal_sha omitted author/requester/markdown_object_id — canonical JSON expanded
  - `[medium]` `[patch]` GO payload fields unasserted — idempotency_key, target_branch, go_proposal_id, document ids
  - `[medium]` `[patch]` matrix “bad parent” untested — format checker + `test_submit_invalid_merged_parent_rejected`
  - `[medium]` `[patch]` empty approved nodes would 200 with zero GO — EMPTY_PROPOSAL
  - `[medium]` `[defer]` partial multi-doc GO failure leaves earlier submits
  - `[low]` `[patch]` GO 2xx non-JSON / missing id → 500 — GOClientError / GO_SUBMIT_FAILED
  - `[low]` `[reject]` full proposal-record.schema.json on GO POST — GO MVP envelope
  - `[low]` `[defer]` live HttpGOClient / GitLab
  - `[low]` `[patch]` tautological proposal_sha lowercase assert — cross-check response vs stub

## Auto Run Result

- Approved submit: one stub GO ProposalRecord per document with base_sha and stable ids. Invalid merged FM → FRONT_MATTER_INVALID, zero GO calls.
- Files: `adapters/go_client.py`, `structure_proposals.py`, `front_matter.py`, `schemas/structure.py`, `api/router.py`, `main.py`, `tests/test_structure_submit.py`
- Review: patched 4 medium + 2 low; deferred partial GO rollback and live HTTP; rejected full ProposalRecord schema in this slice.
- Follow-up: `true`. Residual: fail-fast partial submit; stub-only GO.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 138 passed; ruff clean.
- Commit withheld.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_structure_submit.py src/kb-ingestion/tests/test_structure_review.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
