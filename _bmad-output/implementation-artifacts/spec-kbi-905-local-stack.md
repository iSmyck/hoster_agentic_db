---
title: 'KBI-905 Local stack and smoke health'
type: 'feature'
created: '2026-11-17'
status: 'done'
---

## Intent

**Problem:** `local_stack` and smoke checks omit kb-ingestion, so the service cannot join the host process set.

**Approach:** Register kb-ingestion on port 8006 with migrations `None`, alias the hyphenated package in `run_service.py`, and add `/health` to the smoke map. Do not start docker or claim live stack PASS from this story.

## Boundaries & Constraints

**Always:**
- Service name `kb-ingestion`, port 8006, health `http://127.0.0.1:8006/health`.
- `run_service.py` aliases `kb-ingestion` → `kb_ingestion` like git-orchestrator.
- Smoke registry includes the service; live HTTP remains BLOCKED unless the stack is actually running.

**Never:**
- Do not run docker compose / paid egress as part of unit evidence.
- Do not add alembic for this service.

## Code Map

- `scripts/local_stack.py` — SERVICES entry
- `scripts/smoke_local_stack.py` — health map
- `src/run_service.py` — `_alias_kb_ingestion`
- `.env.example` — KB_INGEST_* vars

## Tasks & Acceptance

**Acceptance Criteria:**
- Given `scripts/local_stack.py` SERVICES, when listed, then kb-ingestion is present on 8006 with migrations None.
- Given `scripts/smoke_local_stack.py` SERVICES, when listed, then kb-ingestion health URL is present.
- Given `run_service.py` with service kb-ingestion, when imported, then the alias helper exists.

## Spec Change Log

- 2026-11-17: port 8006, hyphen alias, smoke health.

## Review Triage Log

### 2026-11-17 — Review pass
- `[medium]` `[defer]` live `local_stack.py` / smoke HTTP — BLOCKED, not executed
- `[low]` `[patch]` hyphenated package would fail `importlib.import_module(f"{service}.app.main")` — alias added

## Auto Run Result

- Registry tests pass. Docker/stack not started.
- Verification: 211 passed; ruff clean.
