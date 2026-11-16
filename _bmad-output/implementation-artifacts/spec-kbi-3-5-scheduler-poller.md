---
title: 'KBI.3.5 Scheduler / poller'
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
      Tick is an explicit POST; no in-process cron daemon. Durable job queue is KBI.4.
    evidence: |-
      Scheduler.tick is invoked by /scheduler/tick only.
    location: >-
      src/kb-ingestion/app/jobs/scheduler.py
    severity: low
  - summary: >-
      Jobs/last_queued live in SourceSyncService memory. Restart loses cadence state.
    evidence: |-
      _jobs and _last_queued are dicts on the service.
    location: >-
      src/kb-ingestion/app/services/source_sync.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Источники не опрашиваются по `poll_interval`; параллельные run одного source гоняются вместе.

**Approach:** `POST /api/kb/v1/ingest/scheduler/tick` ставит sync job, если due. Overlap того же source (queued/running or `_running`): skip/dedupe, не второй running. Tick не ходит в источник; n8n POST /sync исполняет queued job.

## Boundaries & Constraints

**Always:**
- Job `{job_id, source_id, status: queued|running|done|skipped|failed, scheduled_at}`.
- Due: нет last_queued или now ≥ last_queued + poll_interval.
- Overlap: если есть queued/running **или** `is_running` по source_id → tick не создаёт второй (skipped).
- n8n POST /sync при queued job переводит в running→done; GO failure → failed.
- Tick не ходит в внешний source (нет credentials).
- Invalid `now` → 400 VALIDATION_ERROR.

**Never:**
- Не cron daemon в процессе тестов. Не PostgreSQL queue (KBI.4). Не live n8n.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| cadence | interval 60, tick 0 then 60 after done | two queued jobs | N/A |
| too soon | tick +30s on 60 interval | skipped, still one in-flight | N/A |
| after done not due | sync done, tick +45s | no job | N/A |
| overlap queued | queued exists, tick | skipped, still one in-flight | N/A |
| overlap running | _running set, tick | skipped | N/A |
| invalid now | now=not-a-timestamp | отказ | 400 VALIDATION_ERROR |
| GO fail after queue | queued then /sync GO down | job.status=failed | 502 from /sync |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/jobs/scheduler.py` — Scheduler.tick due/overlap.
- `src/kb-ingestion/app/services/source_sync.py` — enqueue_job, is_running, in_flight_job, job status done/failed.
- `src/kb-ingestion/app/api/router.py` — POST `/scheduler/tick` with now parse.
- `src/kb-ingestion/tests/test_source_sync.py` — 3.5 rows.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/jobs/scheduler.py` -- tick -- cadence + overlap skip
- `src/kb-ingestion/app/services/source_sync.py` -- job lifecycle queued→running→done/failed
- `src/kb-ingestion/tests/test_source_sync.py` -- cadence after done, running skip, invalid now -- доказательство

**Acceptance Criteria:**
- Given source with poll_interval, when scheduler runs, then a sync run is queued at the specified cadence.
- Given overlapping sync runs for the same source (queued or running), when a new run is queued, then it is skipped.
- Given queued job and GO failure on /sync, when sync fails, then job.status=failed.
- Given invalid now timestamp, when tick is posted, then 400 VALIDATION_ERROR.

## Spec Change Log

- 2026-11-17: POST /scheduler/tick queues due jobs; overlap skip; /sync completes queued job.
- 2026-11-17 review: skip while is_running; job failed on GO error; invalid now 400; cadence after done.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: high 0, medium 2 patched, low patched/deferred
- findings:
  - `[medium]` `[patch]` tick ignored in-request `_running` without a job row — scheduler checks is_running
  - `[medium]` `[patch]` GO fail left queued job as running/done — status failed
  - `[low]` `[patch]` invalid now 500 — 400 VALIDATION_ERROR
  - `[low]` `[patch]` cadence after done untested — tick +45s empty, +60s queues
  - `[low]` `[defer]` no cron daemon
  - `[low]` `[defer]` in-memory jobs (KBI.4 queue)

## Auto Run Result

- Tick queues due sources, skips overlap including in-flight run, and /sync marks the job done or failed.
- Files: `jobs/scheduler.py`, `services/source_sync.py`, `api/router.py`, `schemas/source_sync.py`, `tests/test_source_sync.py`
- Review: patched running skip, failed status, invalid now; deferred durable queue.
- Follow-up review: `true`. Residual: PostgreSQL job queue in KBI.4.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 165 passed; ruff clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (165)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
