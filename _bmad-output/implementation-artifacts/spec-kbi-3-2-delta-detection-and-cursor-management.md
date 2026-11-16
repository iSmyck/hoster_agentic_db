---
title: 'KBI.3.2 Delta detection and cursor management'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '2e50ae6979a2bafc34a3ea1c7de7acd5fc26c58b'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-3-1-source-registry-and-configuration.md'
warnings: []
deferred:
  - summary: >-
      Cursor commits on human_review (disposition != refused) so retries stay idempotent.
      Stricter "commit only after merge" would re-propose the same delta every poll.
    evidence: |-
      _run commits cursor when outcome.disposition != "refused".
    location: >-
      src/kb-ingestion/app/services/source_sync.py
    severity: low
  - summary: >-
      Cursor is in-memory; restart loses seen versions. Durable cursor belongs to GO/kb_ops (KBI.4).
    evidence: |-
      SourceSyncService._cursors is a dict keyed by source_id then source_object_id.
    location: >-
      src/kb-ingestion/app/services/source_sync.py
    severity: low
  - summary: >-
      Retry after GO_SUBMIT_FAILED uses a new sync_run_id, so idempotency_key changes and
      StubGOClient can create a duplicate proposal. Live GO one-outstanding is not claimed.
    evidence: |-
      idempotency_key = f"{sync_run_id}:{document.source_object_id}"
    location: >-
      src/kb-ingestion/app/services/source_sync.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Без cursor и сравнения `source_version`/`sha256` каждый sync гоняет все документы, а удаления пропадают.

**Approach:** `POST /api/kb/v1/ingest/sources/{source_id}/sync` принимает uniform documents. Сравнивает с cursor: created/updated/noop/deleted. Неизменный hash+version+path → no-op. Delete → deletion proposal (через policy 3.3).

## Boundaries & Constraints

**Always:**
- Document: `source_object_id`, `source_version`, `sha256` (64 hex), `path`, `action` ∈ {upsert,delete}, `ownership_mode` default `source_managed`, optional `lines_changed`, `tombstone`.
- Cursor keyed by `(source_id, source_object_id)` stores sha256+version+path.
- Unchanged sha256 **and** source_version **and** path + upsert → `kind=noop`, GO не вызывается.
- New object → created. Changed hash, version, or path → updated.
- delete + previously seen → deleted (+ deletion proposal in 3.3). Unknown delete → noop.
- 404 SOURCE_NOT_FOUND. 409 SYNC_IN_PROGRESS если run already running.
- Отчёт: `sync_run_id`, `changes[]`, `outcomes[]`.
- Cursor не двигается при refused и при падении всего run до commit item.

**Never:**
- Не ходить в SharePoint. Не двигать cursor при failure всего run (item no-op не двигает). Не PostgreSQL. Не Git.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| first upsert | new object | created | N/A |
| same hash+version+path | second sync | noop, GO not called | N/A |
| new hash | same object new sha | updated | N/A |
| version only | same sha, new source_version | updated | N/A |
| path only | same sha+version, new path | updated | N/A |
| delete known | action=delete, tombstone | deleted + GO proposal | N/A |
| unknown delete | delete of unseen id | noop | N/A |
| unknown source | bad id | отказ | 404 SOURCE_NOT_FOUND |
| overlap | source already in _running | отказ | 409 SYNC_IN_PROGRESS |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/services/source_sync.py` — `_detect`, `_commit_cursor`, `run_sync` 409, CursorStore.
- `src/kb-ingestion/app/schemas/source_sync.py` — SyncDocument/ChangeRecord/SyncReport.
- `src/kb-ingestion/app/api/router.py` — POST `/sources/{id}/sync`.
- `src/kb-ingestion/tests/test_source_sync.py` — 3.2 rows.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/services/source_sync.py` -- _detect + cursor -- created/updated/noop/deleted
- `src/kb-ingestion/app/services/source_sync.py` -- run_sync overlap -- 409 SYNC_IN_PROGRESS
- `src/kb-ingestion/tests/test_source_sync.py` -- version/path/unknown-delete/409 -- доказательство

**Acceptance Criteria:**
- Given registered source with cursor, when sync starts, then new/changed/deleted identified by source_version and sha256.
- Given unchanged hash+version+path, when processed, then no-op.
- Given version-only or path-only change, when processed, then updated.
- Given deleted source document previously seen, when processed, then a deletion proposal is created.
- Given delete of unknown object, when processed, then noop.
- Given a running sync, when another sync starts, then 409 SYNC_IN_PROGRESS.

## Spec Change Log

- 2026-11-17: uniform POST /sync; cursor by (source_id, source_object_id); created/updated/noop/deleted.
- 2026-11-17 review: noop requires sha256+version+path; unknown delete noop; 409 overlap; GO empty-id 502; failed job status.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: high 0, medium 2 patched + 1 deferred, low 2 deferred
- findings:
  - `[medium]` `[patch]` version-only same hash treated as noop — `_detect` requires version+path match
  - `[medium]` `[patch]` path-only rename treated as noop — same `_detect` clause + test
  - `[medium]` `[patch]` SYNC_IN_PROGRESS untested — `test_sync_in_progress_conflict`
  - `[low]` `[patch]` unknown delete created a change — now noop without GO
  - `[low]` `[defer]` cursor on human_review for idempotency
  - `[low]` `[defer]` in-memory cursor
  - `[medium]` `[defer]` retry after GO fail uses new sync_run_id / duplicate stub proposals

## Auto Run Result

- Delta compares sha256+version+path; overlap returns 409; unknown delete is noop.
- Files: `services/source_sync.py`, `schemas/source_sync.py`, `api/router.py`, `tests/test_source_sync.py`
- Review: patched version/path detect, 409, unknown delete; deferred durability and GO idempotency key.
- Follow-up review: `true`. Residual: durable cursor + one-outstanding proposal in GO.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 165 passed; ruff clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (165)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
