---
title: 'KBI.4.1 Front-matter-v2 validator'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '2e50ae6979a2bafc34a3ea1c7de7acd5fc26c58b'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-4-context.md'
  - '{project-root}/specs/corporate-kb/contracts/front-matter.schema.json'
warnings: []
deferred:
  - summary: >-
      CONFLICT_WITH_CURATED and POLICY_BUNDLE_MISMATCH need live GO three-way merge,
      not jsonschema. Still not claimed.
    evidence: |-
      enforce_front_matter checks keys, archive xor, origin, then jsonschema only.
    location: >-
      src/kb-ingestion/app/validators/front_matter.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Canonical write может уйти с `access`/`additionalProperties`, без `origin` у `source_managed`, или с `archived=true` без `archive`.

**Approach:** `enforce_front_matter` поверх jsonschema. `POST /api/kb/v1/ingest/validate/front-matter`. Structure submit и source-sync (если передан front_matter) используют тот же enforce.

## Boundaries & Constraints

**Always:**
- `access`, `owner`, `status` или иное additionalProperty → `FRONT_MATTER_INVALID`.
- `ownership_mode=source_managed` без `origin` → `ORIGIN_REQUIRED`.
- `archived=true` без `archive`, или `archive` при `archived=false` → `ARCHIVE_INVARIANT_VIOLATION`.
- Валидный document-front-matter-v2 → 200 `{valid: true}`.
- Ошибки `{"code","message"}` в detail.

**Never:**
- Не Git. Не live GO. Не менять front-matter.schema.json. Не PostgreSQL.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| valid draft | schema-valid FM | valid true | N/A |
| access key | access present | отказ | 400 FRONT_MATTER_INVALID |
| extra key | owner/status | отказ | 400 FRONT_MATTER_INVALID |
| no origin | source_managed, origin omitted | отказ | 400 ORIGIN_REQUIRED |
| archived xor | archived true, no archive | отказ | 400 ARCHIVE_INVARIANT_VIOLATION |
| archived ok | archived true + archive object | valid | N/A |
| sync FM | source-sync document.front_matter invalid | refused, no GO | FRONT_MATTER_INVALID |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/validators/front_matter.py` — enforce_front_matter; validate_front_matter_draft delegates.
- `src/kb-ingestion/app/api/router.py` — POST `/validate/front-matter`.
- `src/kb-ingestion/app/services/structure_proposals.py` — submit uses enforce.
- `src/kb-ingestion/app/services/source_sync.py` — `_enforce_content` before GO.
- `src/kb-ingestion/tests/test_validators_queue.py` — 4.1 rows.

## Tasks & Acceptance

**Execution:**
- `front_matter.py` -- enforce -- access/origin/archive
- `router.py` -- POST validate/front-matter -- поверхность
- `source_sync.py` -- refuse invalid FM -- no GO
- `test_validators_queue.py` -- матрица 4.1 -- доказательство

**Acceptance Criteria:**
- Given a document with additionalProperties or access key, when validation runs, then FRONT_MATTER_INVALID.
- Given ownership_mode=source_managed without origin, when validation runs, then ORIGIN_REQUIRED.
- Given archived=true without archive object, when validation runs, then ARCHIVE_INVARIANT_VIOLATION.
- Given archived=true with archive object, when validation runs, then valid.
- Given source-sync document with forbidden FM key, when sync runs, then refused without GO.

## Spec Change Log

- 2026-11-17: enforce_front_matter + validate endpoint; archive xor; forbidden keys before jsonschema.
- 2026-11-17 review: archived+archive valid; source-sync FM refuse.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: high 0, medium 1 deferred, low patched
- findings:
  - `[low]` `[patch]` archived=true with valid archive untested — added
  - `[low]` `[patch]` source-sync ignored front_matter — `_enforce_content` refuses
  - `[medium]` `[defer]` CONFLICT_WITH_CURATED / POLICY_BUNDLE_MISMATCH — live GO
  - `[low]` `[reject]` rewrite front-matter.schema.json — contract is normative

## Auto Run Result

- FM enforce maps access/additionalProperties, missing origin, and archive xor to the story codes; structure submit and source-sync reuse it.
- Files: `validators/front_matter.py`, `api/router.py`, `services/source_sync.py`, `tests/test_validators_queue.py`
- Follow-up review: `true`. Residual: GO conflict codes.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 186 passed; ruff clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (186)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
