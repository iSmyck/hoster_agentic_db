---
title: 'T11 Approved hoster.ai studio inference lifecycle'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/baseline.md
  - specs/corporate-kb/integration.md
  - specs/corporate-kb/operations.md
  - specs/corporate-kb/components/open-webui-fork.md
  - _bmad-output/implementation-artifacts/epic-7-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that owner-approved hoster.ai studio inference routes are inventoried, that streaming and tool-call handling preserves correlation and safety, that errors/failures/cancellations are observable, and that no hidden provider/model/perimeter fallback exists.

**Approach:** Create a T11 harness that exercises synthetic YAML fixtures for approved inference route metadata, streaming/tool-call correlation and authorization, malformed/unsafe input rejection, retry/cancel/disconnect observability, egress/perimeter controls, and lifecycle metric structure. Live hoster.ai calls remain BLOCKED.

## Boundaries & Constraints

**Always:**
- Every inference route records approved connection, model/version, data profile, capabilities and required dimension/index-profile linkage.
- Streaming sequential/parallel tool calls preserve request/run correlation and citations, assemble typed arguments without executing partial content, and validate authorization before dispatch.
- Malformed JSON, unknown fields, unsupported operations, oversized payloads and prompt-injection instructions fail safely without shell/SQL/arbitrary execution, unauthorized model payload, merge or privilege expansion.
- Retry/cancel/disconnect/4xx/5xx behavior is observable; mutation retries preserve the same idempotency identity and exact payload.
- Egress is limited to approved endpoints; `pii_permitted` content stays inside the agreed perimeter; revocation closes live streams; offline startup uses only preapproved assets.
- Lifecycle measurements report TTFT and full-response latency separately, with retry/cancel/malformed-call rates, route inventory and fallback attempts; costs are attributable to the run.

**Never:**
- Do not use a real hoster.ai endpoint, model inventory, credentials or egress.
- Do not claim integration PASS for live inference.
- Do not invent thresholds, model IDs or capacity values.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Route inventory | Approved route metadata | All routes record connection/model/version/profile/capabilities | Missing linkage → FAIL |
| Streaming/tool calls | Sequential/parallel tool-call chunks with correlation/citations | Correlation preserved, typed args assembled, authz before dispatch | Partial execution / missing authz → FAIL |
| Malformed/unsafe inputs | Malformed JSON, unknown fields, unsupported ops, oversized payload, prompt injection | Safe rejection without shell/SQL/arbitrary execution or privilege expansion | Unsafe acceptance → FAIL |
| Retry/cancel/disconnect | Retry/cancel/disconnect/4xx/5xx events | Observable; mutation retry preserves idempotency identity and exact payload | Changed payload / lost identity → FAIL |
| Egress/perimeter | Approved endpoints, pii_permitted content, revocation, offline assets | Egress limited; PII inside perimeter; streams closed on revocation; offline startup preapproved | Unauthorized egress / leak → FAIL |
| Lifecycle metrics | Request/run telemetry | TTFT and full-response latency separate; rates/inventory/fallback/cost attributable | Missing metrics / hidden fallback → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t11/run_t11_tests.py` — main harness.
- `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml` — synthetic inference lifecycle fixtures.
- `specs/corporate-kb/baseline.md` — pinned toolchain and hoster.ai deferral status.
- `specs/corporate-kb/integration.md` — integration protocols and error shapes.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t11/run_t11_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t11/inference-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t11/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `7-1-t11-...` → `done`.

**Acceptance Criteria:**
- [x] Given route inventory fixtures, every route records approved connection, model/version, data profile, capabilities and required dimension/index-profile linkage.
- [x] Given streaming/tool-call fixtures, request/run correlation and citations are preserved, typed arguments are assembled without executing partial content, and authorization is validated before dispatch.
- [x] Given malformed/unsafe input fixtures, requests fail safely without shell/SQL/arbitrary execution, unauthorized model payload, merge or privilege expansion.
- [x] Given retry/cancel/disconnect fixtures, behavior is observable and mutation retries preserve the same idempotency identity and exact payload.
- [x] Given egress/perimeter fixtures, egress is limited to approved endpoints, `pii_permitted` content stays inside the perimeter, revocation closes live streams and offline startup uses only preapproved assets.
- [x] Given lifecycle metric fixtures, TTFT and full-response latency are reported separately with retry/cancel/malformed-call rates, route inventory, fallback attempts and cost attribution.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths and live hoster.ai integration is recorded as BLOCKED.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns; validators operate on synthetic YAML fixtures. Real hoster.ai studio endpoint, model inventory, credentials and egress remain BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the approved inference lifecycle without invoking a live provider. Route inventory, streaming/tool-call invariants, safe rejection of malformed/unsafe inputs, retry/cancel/disconnect observability, egress/perimeter controls and metric structure are checked structurally. Live inference evidence remains BLOCKED until owner-approved hoster.ai inputs exist.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t11/run_t11_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t11/run_t11_tests.py` -- expected: writes `inference-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t11/inference-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t11/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
