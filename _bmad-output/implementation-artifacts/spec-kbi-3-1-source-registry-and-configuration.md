---
title: 'KBI.3.1 Source registry and configuration'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '2e50ae6979a2bafc34a3ea1c7de7acd5fc26c58b'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-3-context.md'
  - '{project-root}/specs/corporate-kb/adr/ADR-018-source-sync-auto-merge-policy.md'
warnings: []
deferred:
  - summary: >-
      Registry is in-memory; process restart drops sources. Durable store is KBI.4 / kb_ops.
    evidence: |-
      SourceRegistry._items is a dict. No PostgreSQL (KBI.4).
    location: >-
      src/kb-ingestion/app/services/source_sync.py
    severity: low
  - summary: >-
      credentials_ref is stored as an opaque string; vault/n8n existence is not checked.
    evidence: |-
      Field min_length=1 only. Spec forbids raw secrets, not remote lookup.
    location: >-
      src/kb-ingestion/app/schemas/source_sync.py
    severity: low
  - summary: >-
      data_profile is persisted but not applied at register or sync (content-standard is KBI.4).
    evidence: |-
      SourceRecord.data_profile is unused in _policy.
    location: >-
      src/kb-ingestion/app/services/source_sync.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Нет реестра источников: нельзя сохранить `source_type`/`source_ref`/`auto_merge`/`trusted` и отклонить небезопасный auto-merge.

**Approach:** `POST /api/kb/v1/ingest/sources` валидирует и сохраняет source config. `auto_merge=true` без `trusted=true` → `AUTO_MERGE_REQUIRES_TRUSTED`. Секреты не принимаются.

## Boundaries & Constraints

**Always:**
- Body: `source_type`, `source_ref`, `credentials_ref`, `poll_interval`, `space_id`, `data_profile`, `validation_required`, `auto_merge`, `trusted`. Опционально `max_files_per_sync` (default 50), `max_lines_changed` (default 2000).
- `source_type` ∈ {`n8n`,`callback`}. `data_profile` ∈ {`strict`,`pii_permitted`}. `poll_interval` ≥ 1 секунда.
- `credentials_ref` непустая ссылка (vault/n8n path), не raw secret в других полях.
- 201: `source_id` (uuid hex), те же поля. GET по id.
- `auto_merge=true` и `trusted=false` → 400 `AUTO_MERGE_REQUIRES_TRUSTED`, не persist.
- Ошибки `{"code","message"}` в detail.

**Never:**
- Не SharePoint/FTP клиент. Не хранить пароли/токены. Не Git. Не PostgreSQL. Не auto-merge run (3.3). Не delta (3.2).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| trusted auto | trusted+auto_merge | 201 persisted | N/A |
| untrusted auto | auto_merge true, trusted false | отказ, не persist | 400 AUTO_MERGE_REQUIRES_TRUSTED |
| callback type | source_type=callback | 201 | N/A |
| get | created id | 200 same config | N/A |
| missing | unknown id | отказ | 404 SOURCE_NOT_FOUND |
| poll_interval 0 | poll_interval=0 | отказ | 422 VALIDATION_ERROR |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/schemas/source_sync.py` — SourceRegisterRequest/SourceRecord.
- `src/kb-ingestion/app/services/source_sync.py` — SourceRegistry.register/get.
- `src/kb-ingestion/app/api/router.py` — POST/GET `/api/kb/v1/ingest/sources`.
- `src/kb-ingestion/app/main.py` — wires SourceRegistry on app.state.
- `src/kb-ingestion/tests/test_source_sync.py` — 3.1 rows.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/services/source_sync.py` -- SourceRegistry -- persist + AUTO_MERGE_REQUIRES_TRUSTED
- `src/kb-ingestion/app/schemas/source_sync.py` -- SourceRegisterRequest -- bounds on poll/type/profile
- `src/kb-ingestion/app/api/router.py` -- POST/GET sources -- 201/200/400/404
- `src/kb-ingestion/tests/test_source_sync.py` -- матрица 3.1 -- доказательство

**Acceptance Criteria:**
- Given source config with required fields, when POST /sources, then persisted and validated.
- Given auto_merge=true without trusted=true, when registered, then AUTO_MERGE_REQUIRES_TRUSTED.
- Given source_type=callback, when registered, then 201 with the same type.
- Given poll_interval=0, when registered, then 422.
- Given unknown source_id, when GET, then 404 SOURCE_NOT_FOUND.

## Spec Change Log

- 2026-11-17: POST/GET sources; AUTO_MERGE_REQUIRES_TRUSTED; credentials_ref only.
- 2026-11-17 review: callback type test; poll_interval=0 422; GET 404 envelope; data_profile deferred to KBI.4.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: high 0, medium 1 deferred, low 2 deferred, patched 2
- findings:
  - `[low]` `[patch]` callback source_type untested — `test_register_callback_source`
  - `[low]` `[patch]` poll_interval=0 untested — `test_register_rejects_invalid_poll_interval`
  - `[medium]` `[defer]` data_profile stored, not enforced — KBI.4 content-standard
  - `[low]` `[defer]` in-memory registry
  - `[low]` `[defer]` credentials_ref not resolved against vault
  - `[low]` `[reject]` SharePoint/FTP connectors — n8n supplies delta

## Auto Run Result

- Registry persists n8n/callback sources; auto_merge without trusted is rejected and not stored.
- Files: `schemas/source_sync.py`, `services/source_sync.py`, `api/router.py`, `main.py`, `tests/test_source_sync.py`
- Review: patched callback + poll_interval tests; deferred data_profile, durability, vault lookup.
- Follow-up review: `true` (first pass). Residual: data_profile enforcement in KBI.4.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 165 passed; `uv run ruff check src/kb-ingestion` clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (165)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
