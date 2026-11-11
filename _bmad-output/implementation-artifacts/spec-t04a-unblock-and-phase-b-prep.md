---
title: 'T04a live browser unblocking and Phase B readiness prep'
type: 'feature'
created: '2026-11-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'f5a3670d934fdb83dc7b7046f949d93af8320363'
context:
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py
  - scripts/local_stack.py
  - .env
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** T04a live browser acceptance is BLOCKED because `scripts/local_stack.py` misconfigures Open WebUI auth: it checks `openwebui.user` while Open WebUI v0.13.0 creates `public.user`, so auth is disabled and the harness cannot sign up an admin. Phase B readiness (identity/retrieval live integration) needs owner inputs documented.

**Approach:** Fix the local stack detection logic so `run_openwebui_acceptance.py` can run end-to-end, capture the result honestly, and prepare the Phase B readiness checklist in parallel.

## Boundaries & Constraints

**Always:**
- Make the smallest possible change to `scripts/local_stack.py`.
- Preserve pinned versions and existing ADR decisions.
- Record actual evidence, whether PASS or BLOCKED.
- Sanitize evidence before placing it in `specs/corporate-kb/evidence/`.

**Never:**
- Upgrade Open WebUI or change pinned baseline.
- Run production migrations, deploy, or paid external calls.
- Present mocked integration as live PASS.
- Commit or push unless explicitly requested.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Local stack auth fix | `scripts/local_stack.py` | Open WebUI auth enabled, signup allowed, admin creatable | Harness gets admin token |
| Open WebUI acceptance | `run_openwebui_acceptance.py` | Runs to completion; PASS/FAIL/BLOCKED recorded | Update T04a status from evidence |
| Phase B readiness | Keycloak/retrieval inputs | Checklist of missing owner/sandbox inputs | Record in sprint-status action items |

</frozen-after-approval>

## Code Map

- `scripts/local_stack.py` — Open WebUI auth detection logic to fix.
- `_bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` — harness that needs admin signup.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status tracker.
- `.env` — local dev credentials and endpoints.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/local_stack.py` -- fixed user detection to match Open WebUI v0.13.0 schema behavior (`public.user`), forced `WEBUI_AUTH=true`, `ENABLE_SIGNUP=true`, `RESET_CONFIG_ON_START=true`, and set `WEBUI_SECRET_KEY`.
- [x] `scripts/smoke_local_stack.py` -- re-ran; added `load_dotenv` so GitLab health is exercised.
- [x] `_bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` -- ran to completion; added graceful handling and report writing on all exit paths.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- updated T04a to `blocked` with honest evidence (6/3/0) and root cause.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- populated ACT-005/ACT-006 with exact missing owner/sandbox inputs for Phase B.

**Acceptance Criteria:**
- Given local stack starts, when smoke tests run, then they report health endpoints PASS and Open WebUI reachable.
- Given Open WebUI auth/signup works, when harness runs, then it completes and writes `g1-openwebui-results.json`.
- Given evidence is generated, when sprint status is updated, then T04a reflects PASS or BLOCKED with explicit reason.
- Given Phase B inputs are not yet available, when action items are updated, then they list the exact owner inputs needed.

## Review Triage Log

| Finding | Verdict | Evidence | Route |
|---|---|---|---|
| `#kb-status` element may be missing during error capture, crashing harness | low | Added nested try/except with empty fallback. | patch |
| Report write `OSError` could leave no evidence | low | Wrapped `_write_report` body in try/except OSError. | patch |
| `G1_ALLOW_DESTRUCTIVE_RESET` guard only accepted `"1"` | low | Changed to accept `{"1", "true", "yes"}` case-insensitively. | patch |
| No test exercises `_reset_openwebui_users()` guard | medium | Added `tests/test_local_stack.py` with two guard cases. | patch |
| Spec has empty placeholder sections and inconsistent `status` | low | Removed empty sections; status tracks workflow state. | patch |

## Verification

**Commands:**
- `uv run python scripts/local_stack.py` -- starts stack with fixed auth.
- `uv run python scripts/smoke_local_stack.py` -- expected: 13 PASS / 0 FAIL / 0 BLOCKED.
- `uv run python _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` -- expected: completes and writes results (current: 6 PASS / 3 FAIL / 0 BLOCKED).

**Manual checks:**
- `curl http://localhost:3100/api/config` shows `"auth": true` and `"enable_signup": true`.
- Evidence files contain no secrets or real endpoints.
