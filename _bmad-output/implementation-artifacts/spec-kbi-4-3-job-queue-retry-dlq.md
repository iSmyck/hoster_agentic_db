---
title: 'KBI.4.3 Job queue with retry and DLQ'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '2e50ae6979a2bafc34a3ea1c7de7acd5fc26c58b'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-4-context.md'
  - '{project-root}/specs/corporate-kb/adr/ADR-015-postgresql-schema-ownership.md'
warnings: []
deferred:
  - summary: >-
      Queue is in-memory. Live PostgreSQL / kb_ops jobs are GO-owned (ADR-015);
      AGENTS.md forbids a new ingestion schema without an ADR.
    evidence: |-
      InMemoryJobQueue._jobs is a dict. No alembic migration added.
    location: >-
      src/kb-ingestion/app/jobs/queue.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Ingestion jobs при сбое теряются или ретраятся бесконечно; нет DLQ и метрик.

**Approach:** In-memory `JobQueue` с bounded exponential backoff, DLQ после исчерпания бюджета, sanitised `last_error`. `POST /jobs`, `POST /jobs/tick`, `GET /jobs/metrics`. Live PostgreSQL не вводим: ADR-015 / AGENTS.md.

## Boundaries & Constraints

**Always:**
- Job: `{job_id, kind, payload, status: queued|running|retry|done|dead, attempts, max_attempts, next_run_at, last_error}`.
- Transient fail: attempts++, next_run_at = now + 2^(attempts-1)s (cap 60s), status=retry.
- attempts ≥ max_attempts или permanent fail → status=dead, reason sanitised (email/token redacted).
- Metrics: queued/retry/dead/done counts, lag_seconds, attempts_total, outcomes.
- Tick обрабатывает один due job; future next_run_at → processed=0.

**Never:**
- Не новая PostgreSQL schema. Не live Redis. Не секреты в last_error.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| transient then ok | inject transient then none | retry +1s then done | N/A |
| too soon | tick before next_run_at | processed=0 | N/A |
| exhaust | 2 transient on max_attempts=2 | dead | sanitised reason |
| permanent | inject permanent | dead immediately, token/email redacted | N/A |
| metrics | done+dead+queued | lag, attempts_total, outcomes | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/jobs/queue.py` — InMemoryJobQueue, sanitize_error, process_one.
- `src/kb-ingestion/app/schemas/jobs.py` — enqueue/tick/metrics models.
- `src/kb-ingestion/app/api/router.py` — POST `/jobs`, `/jobs/tick`, GET `/jobs/metrics`.
- `src/kb-ingestion/app/main.py` — wires job_queue.
- `src/kb-ingestion/tests/test_validators_queue.py` — 4.3 rows.

## Tasks & Acceptance

**Execution:**
- `jobs/queue.py` -- retry/DLQ/sanitize -- AC
- `api/router.py` -- jobs surface -- enqueue/tick/metrics
- `test_validators_queue.py` -- backoff, DLQ, metrics -- доказательство

**Acceptance Criteria:**
- Given a transient job failure, when the worker processes it, then it retries with bounded exponential backoff.
- Given retry budget exhausted or a permanent failure, when the worker processes it, then the job moves to dead-letter with sanitized reason.
- Given a running queue, when metrics are scraped, then queue lag, attempt count, and outcome are observable.

## Spec Change Log

- 2026-11-17: in-memory queue; tick inject; metrics; error redaction.
- 2026-11-17 review: enqueue `now` so lag is deterministic; backoff +1s asserted.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: high 0, medium 1 deferred + 1 patched, low patched
- findings:
  - `[medium]` `[patch]` metrics lag used wall-clock queued_at — enqueue accepts `now`
  - `[low]` `[patch]` backoff interval untested — assert next_run_at +1s and too-soon tick
  - `[low]` `[patch]` secrets in DLQ reason — Bearer/email redacted
  - `[medium]` `[defer]` PostgreSQL queue — ADR-015 kb_ops, no new schema
  - `[low]` `[reject]` ingest-owned alembic tables — contradicts ADR-015

## Auto Run Result

- Queue retries with 2^(n-1)s backoff, dead-letters on exhaust/permanent failure, and exposes lag/attempts/outcomes. Live PG not claimed.
- Files: `jobs/queue.py`, `schemas/jobs.py`, `api/router.py`, `main.py`, `tests/test_validators_queue.py`
- Follow-up review: `true`. Residual: durable kb_ops queue.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 186 passed; ruff clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (186)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
