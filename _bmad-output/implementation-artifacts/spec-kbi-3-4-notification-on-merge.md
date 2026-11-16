---
title: 'KBI.3.4 Notification on merge'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '2e50ae6979a2bafc34a3ea1c7de7acd5fc26c58b'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-3-3-auto-merge-policy-engine.md'
warnings: []
deferred:
  - summary: >-
      webhook channel is simulated (fail_next injection); no outbound HTTP. Live webhook/email/Slack out of scope.
    evidence: |-
      Notifier._deliver decrements fail_next; never calls httpx.
    location: >-
      src/kb-ingestion/app/services/notifier.py
    severity: low
  - summary: >-
      Subscriptions are in-memory; restart drops them.
    evidence: |-
      Notifier._subs is a dict.
    location: >-
      src/kb-ingestion/app/services/notifier.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Редактор не узнаёт, что подписанный path изменился proven merge.

**Approach:** Подписки `editor_stable_id`+`space_id`+`path`+`channel`. После proven merge (outcome=merged) notifier доставляет. Сбой доставки — retry и лог; merge не откатывается. human_review/refused не нотифицируют.

## Boundaries & Constraints

**Always:**
- `POST /api/kb/v1/ingest/notifications/subscriptions`: editor_stable_id, space_id, path, channel ∈ {log, webhook}.
- Match: exact path или prefix (`docs/` matches `docs/a.md`).
- После merged auto-merge: delivery attempt. channel=log всегда успешен в тестах.
- Failure: до 3 попыток, запись в `failures[]`, merge outcome остаётся merged, GO merge не revert.
- Исчерпанные retries: status=failed, merge всё равно merged.
- Нет подписки → deliveries пусты, sync 200.
- human_review / refused / noop → notifier не вызывается.

**Never:**
- Не rollback merge. Не email/Slack live. Не Git. Не PostgreSQL.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| subscribed merge | sub on path prefix, auto-merge | delivery sent | N/A |
| no sub | merge, no sub | no delivery | N/A |
| delivery fail then recover | fail_next=2 | retried, attempts=3, merge still merged | logged then sent |
| exhausted | fail_next≥3 | failures[].status=failed, merge stays merged | logged failure |
| human_review | validation_required, with or without sub | no delivery | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/services/notifier.py` — subscriptions, notify_merge, retries, path prefix.
- `src/kb-ingestion/app/services/source_sync.py` — notify_merge only after merged auto-merge.
- `src/kb-ingestion/app/api/router.py` — POST `/notifications/subscriptions`.
- `src/kb-ingestion/tests/test_source_sync.py` — 3.4 rows.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/services/notifier.py` -- subscribe + notify_merge -- prefix match, 3 retries
- `src/kb-ingestion/app/services/source_sync.py` -- call after merged only -- no notify on human_review
- `src/kb-ingestion/tests/test_source_sync.py` -- recover/exhausted/silent-review -- доказательство

**Acceptance Criteria:**
- Given merge commit in main for a subscribed path, when merge is proven, then notifications sent to subscribed editors.
- Given notification failure, when delivery fails then recovers, then retried and merge is not rolled back.
- Given retries exhausted, when delivery fails, then logged failed and merge stays merged.
- Given human_review outcome, when sync completes, then notifier is not called.

## Spec Change Log

- 2026-11-17: subscriptions + notify after proven merge; 3 retries; no rollback.
- 2026-11-17 review: exhausted retries keep merge; human_review silent.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: high 0, medium 0, low patched/deferred
- findings:
  - `[low]` `[patch]` exhausted retries untested — `test_notification_exhausted_does_not_rollback_merge`
  - `[low]` `[patch]` human_review could notify — assert deliveries == []
  - `[low]` `[defer]` webhook has no HTTP client
  - `[low]` `[defer]` in-memory subscriptions
  - `[low]` `[reject]` live Slack/email channels — spec {log, webhook}

## Auto Run Result

- Proven auto-merge notifies prefix-matched subscribers; retries do not revert GO merge; human_review is silent.
- Files: `services/notifier.py`, `services/source_sync.py`, `api/router.py`, `tests/test_source_sync.py`
- Review: patched exhausted + silent-review; deferred live webhook.
- Follow-up review: `true`. Residual: real webhook transport.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 165 passed; ruff clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (165)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
