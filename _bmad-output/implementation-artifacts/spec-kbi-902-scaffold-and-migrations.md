---
title: 'KBI-902 kb-ingestion scaffold and migrations'
type: 'feature'
created: '2026-11-17'
status: 'done'
---

## Intent

**Problem:** Cross-cutting asked for alembic next to the kb-ingestion scaffold.

**Approach:** The FastAPI module already exists. Record that product tables stay in GO `kb_ops` (ADR-015). Ship an empty deferred migrations package, not ingestion-owned revisions.

## Boundaries & Constraints

**Always:**
- `src/kb-ingestion/` remains the service root.
- `migrations/` documents deferred ownership; no `versions/*.py`.
- Durable jobs/cursors stay in-memory until GO `kb_ops` work is authorized.

**Never:**
- Do not add ingestion PostgreSQL tables.
- Do not run alembic upgrade for kb-ingestion from local_stack.

## Code Map

- `src/kb-ingestion/app/main.py` — FastAPI factory
- `src/kb-ingestion/migrations/deferred.py` — ADR-015 marker
- `scripts/local_stack.py` — `migrations: None`

## Tasks & Acceptance

**Acceptance Criteria:**
- Given `src/kb-ingestion/app/main.py`, when imported, then FastAPI app factory exists.
- Given `src/kb-ingestion/migrations/`, when listed, then no Alembic revision files exist.
- Given local_stack service entry for kb-ingestion, when migrations field is read, then it is `None`.

## Spec Change Log

- 2026-11-17: deferred migrations package; no product schema.

## Review Triage Log

### 2026-11-17 — Review pass
- `[medium]` `[defer]` durable `kb_ops` job/cursor tables — GO-owned, not this story
- `[low]` `[reject]` ingest-owned alembic `versions/` — contradicts ADR-015

## Auto Run Result

- Scaffold present; no revision files; local_stack migrations None.
- Verification: 211 passed; ruff clean.
