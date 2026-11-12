---
title: 'Close G1 API fault-matrix gates (A05–A10 / A27–A30 + concurrency/fault scenarios)'
type: 'chore'
created: '2026-11-12'
status: 'done'
baseline_revision: 'b6e6d5d0b12aa03edce486c032845b107fcbf0ca'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings:
  - multiple-goals
  - oversized
deferred: []
---

<intent-contract>

## Intent

**Problem:** G1 is accepted, but the full A01–A36 fault matrix is still deferred. The API lifecycle subset currently passes only the happy path and a few negative cases. We need deterministic synthetic coverage for the remaining A05–A10 and A27–A30 fault scenarios plus concurrency/idempotency/fault-injection cases so the deferred gate can be closed.

**Approach:** Extend the GO contract/unit test suite with a synthetic fault-matrix harness that exercises invalid state transitions, actor mismatches, idempotency violations, concurrent races, and malformed payloads against the GO API in-memory. Update sprint status and evidence; keep live GitLab destructive acceptance optional and separately documented.

## Boundaries & Constraints

**Always:**
- Use only synthetic fixtures; do not require live GitLab/PostgreSQL or destructive schema resets.
- Reuse existing GO FastAPI TestClient, stub adapters, and contract schemas.
- Keep live acceptance behind `G1_ALLOW_DESTRUCTIVE_RESET=1`; do not enable it implicitly.
- Record evidence under `_bmad-output/test-artifacts/g1/` and sanitized report under `specs/corporate-kb/evidence/g1/`.
- Update `sprint-status.yaml` after verification passes.

**Never:**
- Change pinned versions, upgrade dependencies, or run production migrations.
- Mark live gates as passed from synthetic results.
- Add new tables/schemas without an ADR.
- Delete or weaken existing passing checks.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Invalid state transition | Merge requested before decision | `INVALID_STATE` 409, no merge | Recorded as PASS |
| Actor spoofing | Decision actor != authenticated approver | `ACTOR_MISMATCH` 403, no DecisionRecord | Recorded as PASS |
| Self-approval | Author == approver | `SELF_APPROVAL` 403 | Recorded as PASS |
| Idempotency key reuse with different payload | Same key, different proposal | `IDEMPOTENCY_KEY_REUSED` 409, zero writes | Recorded as PASS |
| Concurrent decision records | Two decisions for same proposal | Second rejected or idempotent if identical | No duplicate DecisionRecord |
| Invalid SHA | Proposal SHA not 40 hex | Validation error 422 | Recorded as PASS |
| Reject decision | Decision action = rejected | Proposal cannot merge; rejection persisted | Recorded as PASS |
| Cancel/supersede | Decision supersedes prior | Prior decision barred, new decision governs | Recorded as PASS |

</intent-contract>

## Code Map

- `src/git-orchestrator/app/services/proposals.py` -- proposal lifecycle, merge guards.
- `src/git-orchestrator/app/services/decisions.py` -- decision record creation, tagging.
- `src/git-orchestrator/app/api/router.py` -- GO HTTP routes and error mapping.
- `src/git-orchestrator/app/api/auth.py` -- identity injection and role checks.
- `src/git-orchestrator/app/schemas/proposals.py` -- Pydantic proposal request/response models.
- `src/git-orchestrator/app/schemas/decisions.py` -- Pydantic decision request/response models.
- `src/git-orchestrator/app/adapters/gitlab.py` -- GitLab port and stub adapter.
- `src/git-orchestrator/tests/test_g1_fault_matrix.py` -- destination for new fault-matrix tests (new file).
- `_bmad-output/test-artifacts/g1/run_g1_live_acceptance.py` -- live acceptance harness (happy path + basic negatives).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- source of truth for status.
- `specs/corporate-kb/evidence/g1/` -- destination for sanitized evidence.

## Tasks & Acceptance

**Execution:**
- `src/git-orchestrator/tests/test_g1_fault_matrix.py` -- create comprehensive fault-matrix tests covering A05–A10/A27–A30 scenarios, idempotency, concurrency, invalid payloads, actor mismatches, and state-transition guards. Use TestClient + stub GitLab adapter. RATIONALE: deterministic synthetic closure of deferred API fault gates.
- `src/git-orchestrator/app/services/proposals.py` and `src/git-orchestrator/app/services/decisions.py` -- fix any bugs uncovered by fault-matrix tests (e.g., missing state guards, race windows). RATIONALE: make the fault matrix pass.
- `src/git-orchestrator/app/api/router.py` -- ensure error responses use unified `{code, message, request_id, retryable}` shape for all new fault cases. RATIONALE: contract compliance.
- `_bmad-output/test-artifacts/g1/run_g1_fault_matrix.py` -- optional standalone runner that executes the fault-matrix tests and writes JSON/Markdown reports. RATIONALE: reproducible evidence artifact.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- update ACT-004 to done, remove full A01–A36 fault matrix from blocked_gates, update T05/T04a notes. RATIONALE: reflect closure.
- `specs/corporate-kb/evidence/g1/g1-fault-matrix-evidence.md` -- sanitized evidence report. RATIONALE: reviewable proof.

**Acceptance Criteria:**
- Given the fault-matrix test file, when `uv run pytest src/git-orchestrator/tests/test_g1_fault_matrix.py -q` is executed, then all tests pass.
- Given the full GO test suite, when `uv run pytest src/git-orchestrator/tests -q` is executed, then all non-skipped tests pass.
- Given the standalone runner, when executed, then it writes a JSON report with PASS/FAIL counts and zero FAIL.
- Given the sprint status file, when updated, then ACT-004 is `done` and the A01–A36 fault matrix is no longer listed as blocked.
- Given the evidence report, when reviewed, then it distinguishes synthetic PASS from live GitLab acceptance status.

## Spec Change Log

## Review Triage Log

### 2026-11-12 — Review pass (self-review)
- verdicts: 3 findings — high 0, medium 0, low 0, false 0, maybe-false 3
- findings:
  - `[maybe-false]` `[defer]` Error responses now require `request_id` and `retryable`; any client that parses only `code`/`message` could break — existing GO test suite passes, but integration clients outside this repo were not exercised. Settle by running `run_g1_live_acceptance.py` with `G1_ALLOW_DESTRUCTIVE_RESET=1` against sandbox GitLab when available.
  - `[maybe-false]` `[defer]` `record_decision` now allows only one decision per proposal unless superseded; downstream code that created multiple decisions without supersede will now receive `INVALID_STATE` — existing tests and harnesses pass, but production usage outside G1 scope was not verified.
  - `[maybe-false]` `[defer]` `request_id` is generated per error rather than propagated from an inbound tracing header — satisfies the required response shape for G1; end-to-end correlation would need additional middleware if it becomes a requirement.

## Design Notes

The fault matrix is intentionally synthetic: it runs against the GO FastAPI TestClient with a stub GitLab adapter. This avoids destructive PostgreSQL resets and live GitLab state. Live acceptance still requires `G1_ALLOW_DESTRUCTIVE_RESET=1` and a running sandbox GitLab; that gate stays explicitly documented as optional/blocked until the environment is available.

## Verification

**Commands:**
- `uv run pytest src/git-orchestrator/tests/test_g1_fault_matrix.py -q` -- expected: all pass.
- `uv run pytest src/git-orchestrator/tests -q` -- expected: all non-skipped pass.
- `uv run python _bmad-output/test-artifacts/g1/run_g1_fault_matrix.py` -- expected: exits 0, writes `_bmad-output/test-artifacts/g1/g1-fault-matrix-results.json`.
- `python -c "import yaml; yaml.safe_load(open('_bmad-output/implementation-artifacts/sprint-status.yaml'))"` -- expected: no parse errors.

**Manual checks (if no CLI):**
- Inspect `_bmad-output/test-artifacts/g1/g1-fault-matrix-results.json` for zero FAIL.
- Inspect `specs/corporate-kb/evidence/g1/g1-fault-matrix-evidence.md` for sanitized evidence.
- Inspect `sprint-status.yaml` blocked_gates for removal of A01–A36 fault matrix.

## Auto Run Result

- Summary: G1 API fault-matrix gates A05–A10/A27–A30 plus concurrency/idempotency scenarios closed synthetically. Added 20 fault-matrix tests, unified error shape, decision supersede support, and standalone runner. Sprint status updated; ACT-004 marked done.
- Files changed:
  - `src/git-orchestrator/tests/test_g1_fault_matrix.py` — new fault-matrix tests (20).
  - `src/git-orchestrator/app/services/git_orchestrator.py` — decision supersede and prior-decision guard.
  - `src/git-orchestrator/app/api/router.py` — unified error shape `{code, message, request_id, retryable}`; actor mismatch routed through domain error handler.
  - `src/git-orchestrator/app/schemas/ops.py` — added `supersedes_decision_id` to `DecisionRecordRequest`.
  - `_bmad-output/test-artifacts/g1/run_g1_fault_matrix.py` — standalone runner.
  - `_bmad-output/test-artifacts/g1/g1-fault-matrix-results.json` — machine results.
  - `_bmad-output/test-artifacts/g1/g1-fault-matrix-summary.md` — human-readable report.
  - `specs/corporate-kb/evidence/g1/g1-fault-matrix-evidence.md` — sanitized evidence.
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — status updates.
- Review findings: 3 maybe-false deferred (error-shape compatibility, behavior change, request_id correlation).
- Follow-up review recommended: false.
- Verification performed:
  - `uv run pytest src/git-orchestrator/tests/test_g1_fault_matrix.py -q` → 20 passed.
  - `uv run pytest src/git-orchestrator/tests -q` → 73 passed.
  - `uv run python _bmad-output/test-artifacts/g1/run_g1_fault_matrix.py` → PASS=20, FAIL=0.
  - `uv run ruff check ...` → All checks passed.
- Residual risks:
  - Live GitLab/PostgreSQL destructive acceptance not run; gated by `G1_ALLOW_DESTRUCTIVE_RESET=1`.
  - Unified error shape may require integration client updates if they previously parsed only `code`/`message`.
