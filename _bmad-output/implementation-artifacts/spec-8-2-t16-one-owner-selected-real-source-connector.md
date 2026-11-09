---
title: 'T16 One owner-selected real source connector'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/components/ingestion-connectors.md
  - specs/corporate-kb/components/git-orchestrator.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-8-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence for the one owner-selected real source connector (SharePoint, Bitrix24 or Kayako). Without owner selection, sandbox and credentials the integration cannot be claimed PASS; mocks do not count as integration evidence.

**Approach:** Create a T16 harness that records a synthetic feasibility inventory for the three candidate connectors, validates connector-design invariants on synthetic fixtures, and explicitly marks every live integration check BLOCKED. The harness distinguishes design-readiness evidence from real connector evidence and does not fabricate sandbox results.

## Boundaries & Constraints

**Always:**
- Feasibility inventory records exact edition, API, authentication, sandbox, scopes, rate limits and observed behavior for the selected source only; other connectors are not claimed ready.
- The connector preserves stable remote ID, immutable version/hash, source owner and provenance; maps only to the configured repository=Space; sends proposal-only requests to GO.
- Human DecisionRecord and GO merge remain mandatory; the connector has no push/merge/auto-merge/grants/export/index-pointer capability.
- Revoked credentials, changed ACL hints or revoked group membership fail closed; access hints are treated as hints only.
- Deletion produces a tombstone/obsolete review; bounded retry preserves operation identity; duplicate webhooks/polling/concurrent workers yield at most one outstanding proposal; poison objects reach an observable dead-letter.
- Attachments are immutable/versioned with SHA-256, size, media type and source reference; mutable URLs, missing/mismatched objects and failed ACL checks block affected claims.
- Source secrets, raw payloads, signed URLs and tokens never enter documents, MR evidence, model arguments, logs or reports.

**Never:**
- Do not claim real source connector PASS without owner selection, sandbox and credentials.
- Do not fabricate connector evidence or use mock results as integration PASS.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Feasibility inventory | Connector candidates and selected source | Selected source inventory complete; others marked not ready | Missing required field / claiming unselected connector ready → FAIL |
| Connector identity & provenance | Remote ID, version/hash, source owner, Space mapping | Stable binding to configured repository=Space; proposal-only | Mutable identity / wrong Space / push capability → FAIL |
| Access revocation | Revoked credentials, changed ACL hints, revoked group | Fail closed; hints treated as hints only | Access granted on revocation hint / hint treated as authority → FAIL |
| Deletion & retry | Source deletion, bounded retry, duplicate events | Tombstone MR; idempotent retry; at most one proposal; poison DLQ | Silent delete / duplicate proposal / lost poison → FAIL |
| Attachments & object ACL | Immutable object with SHA-256, size, media type, source ref | Versioned attachment recorded; mutable URL / hash mismatch blocked | Mutable URL / missing object / ACL fail → FAIL |
| Secrets hygiene | Payloads, tokens, signed URLs | No secrets in documents/MR evidence/model args/logs/reports | Secret leak → FAIL |

</frozen-after-approval>

## Open Questions

- Owner has not selected SharePoint, Bitrix24 or Kayako; real sandbox/credentials unavailable.

## Code Map

- `_bmad-output/test-artifacts/t16/run_t16_tests.py` — main harness.
- `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml` — synthetic connector design fixtures.
- `specs/corporate-kb/components/ingestion-connectors.md` — connector design.
- `specs/corporate-kb/components/git-orchestrator.md` — GO merge-only protocol.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t16/run_t16_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t16/connector-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t16/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `8-2-t16-...` → `done`.

**Acceptance Criteria:**
- [x] Given the feasibility inventory fixtures, the selected source records exact edition/API/auth/sandbox/scopes/rate limits and the other connectors are not claimed ready.
- [x] Given connector identity fixtures, stable remote ID, immutable version/hash, source owner and provenance are preserved and mapping is to the configured repository=Space.
- [x] Given connector capability fixtures, only proposal requests are sent to GO and no push/merge/auto-merge/grants/export/index-pointer capability exists.
- [x] Given revocation fixtures, revoked credentials, changed ACL hints or revoked group membership fail closed and access hints remain hints only.
- [x] Given deletion/retry fixtures, deletion produces a tombstone/obsolete review, bounded retry preserves operation identity, duplicate events yield at most one outstanding proposal and poison objects reach a dead-letter.
- [x] Given attachment fixtures, attachments are immutable/versioned with SHA-256, size, media type and source reference; mutable URLs, missing objects and failed ACL checks block affected claims.
- [x] Given secrets hygiene fixtures, source secrets, raw payloads, signed URLs and tokens do not enter documents, MR evidence, model arguments, logs or reports.
- [x] Given completed run, live connector integration against a real sandbox is recorded as BLOCKED and evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns via `harness_common.py`; validators operate on synthetic YAML fixtures. Live source connector integration remains BLOCKED pending owner selection and real sandbox credentials.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness records the design invariants that a real connector must satisfy and produces a synthetic feasibility inventory. It deliberately marks all live integration checks BLOCKED because no owner-selected source, sandbox or credentials exist. This satisfies the rule that mocks do not count as integration PASS.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t16/run_t16_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t16/run_t16_tests.py` -- expected: writes `connector-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t16/connector-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t16/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
