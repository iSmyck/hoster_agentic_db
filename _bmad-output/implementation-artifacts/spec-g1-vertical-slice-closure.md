---
title: 'G1 vertical slice closure and status synchronization'
type: 'feature'
created: '2026-11-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '35615ac9652c3cdb70bc6d2854316c66be8929d3'
context:
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/implementation-artifacts/sprint-g1-retrospective.md
  - _bmad-output/test-artifacts/t04b/run_editor_tests.py
  - _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py
  - _bmad-output/test-artifacts/g1/run_g1_live_acceptance.py
  - scripts/local_stack.py
  - scripts/smoke_local_stack.py
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `sprint-status.yaml` still reports G1 at 80 % with T04b `in-progress`, while `sprint-g1-retrospective.md` has already accepted G1 as synthetically done. Live acceptance gates (T04a browser, full A01–A36) and the Open WebUI white-label decision remain unresolved.

**Approach:** Synchronize `sprint-status.yaml` to the verified synthetic state, run every live acceptance harness the sandbox can support, explicitly mark BLOCKED gates that still lack inputs/environment, and surface the white-label decision for owner resolution.

## Boundaries & Constraints

**Always:**
- Update sprint status only from actual test evidence or existing accepted retrospective.
- Preserve `BLOCKED` labels for gates that lack owner inputs, sandbox browser automation, or external endpoints.
- Sanitize all evidence before placing it in `specs/corporate-kb/evidence/`.
- Keep pinned versions, base branches, and ADR commitments unchanged.

**Never:**
- Present mocked integration as live GitLab/IdP/hoster.ai PASS.
- Run production migrations, destructive cleanup, deploy, or paid external calls.
- Modify Open WebUI branding without owner/legal clearance.
- Commit or push changes unless explicitly requested.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| T04b synthetic closure | `run_editor_tests.py` | PASS ≥24, FAIL 0, BLOCKED 5 (live browser) | Update status to `verified` |
| Local stack health | `local_stack.py` + `smoke_local_stack.py` | 12 PASS, 0 FAIL, 1 BLOCKED | Mark acceptance BLOCKED if stack fails |
| T04a live browser | `run_openwebui_acceptance.py` | PASS if Open WebUI + Playwright ready | BLOCKED if browser/IdP/GitLab not ready |
| Full G1 live acceptance | `run_g1_live_acceptance.py` | PASS if GO + GitLab + PostgreSQL ready | BLOCKED if destructive reset/env not ready |
| White-label decision | Owner input | Decision recorded in sprint status | Deferred if no owner answer |

</frozen-after-approval>

## Code Map

- `_bmad-output/implementation-artifacts/sprint-status.yaml` — source of truth for G1 readiness; needs T04b and phase-a update.
- `_bmad-output/implementation-artifacts/sprint-g1-retrospective.md` — already accepts G1 synthetically; source for status decisions.
- `_bmad-output/test-artifacts/t04b/run_editor_tests.py` — synthetic T04b harness; 24 PASS / 5 BLOCKED.
- `_bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` — T04a/T04b live browser acceptance via Playwright.
- `_bmad-output/test-artifacts/g1/run_g1_live_acceptance.py` — full G1 MR/decision/merge lifecycle acceptance.
- `scripts/local_stack.py` — starts services and Open WebUI for live acceptance.
- `scripts/smoke_local_stack.py` — validates stack health and seeded G1 flow.
- `specs/corporate-kb/evidence/g1/` — destination for sanitized live acceptance evidence.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- update `t04b` to `verified` and `phase-a` to `verified`; set `g1_slice_percent` to 100 and `g1_status` to `DONE` only if synthetic evidence passes.
- [x] `_bmad-output/test-artifacts/t04b/run_editor_tests.py` -- re-run and verify `editor-results.json` shows PASS 24 / FAIL 0 / BLOCKED 5.
- [x] `scripts/local_stack.py` -- start in background (or confirm already running) with Open WebUI enabled.
- [x] `scripts/smoke_local_stack.py` -- run and verify 12 PASS / 0 FAIL / 1 BLOCKED.
- [x] `_bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` -- attempted; live browser gate BLOCKED (Open WebUI /kb Submit proposal button disabled in automation).
- [x] `_bmad-output/test-artifacts/g1/run_g1_live_acceptance.py` -- attempted with `G1_ALLOW_DESTRUCTIVE_RESET=1`; passed 20/0/0.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- recorded white-label deferral (G1-D8) and remaining BLOCKED gates.

**Acceptance Criteria:**
- Given T04b harness passes synthetically, when `sprint-status.yaml` is updated, then T04b reflects `verified` and G1 slice readiness reflects 100 %.
- Given local stack is running, when smoke tests execute, then they report 12 PASS / 0 FAIL / 1 BLOCKED.
- Given live acceptance prerequisites are missing, when harnesses are attempted, then they are recorded as BLOCKED with explicit reason rather than FAIL.
- Given owner provides a white-label answer, when status is updated, then the decision is recorded under `decisions` or `action_items`.

## Review Triage Log

| Finding | Verdict | Evidence | Route |
|---|---|---|---|
| Spec contains empty placeholder sections (`Implementation Notes`, `Spec Change Log`, `Design Notes`) | low | Sections are empty; template instructs to delete empty sections. | patch |
| Sprint `blocked_gates` does not explicitly list T04b live serializer/IME/a11y/XSS debt | low | Debt is acknowledged in T04b note and ACT-002, but missing from `blocked_gates`. | patch |
| ACT-012 status is `blocked` after decision G1-D8 is accepted | low | Decision is made; action item should reflect closure. | patch |
| Evidence sanitization manual check only forbids `localhost:8080` while evidence contains `localhost:8081` | low | Local dev endpoint is not a secret, but the check rule is too narrow. | patch |
| Timezone format differs between `sprint-status.yaml` and evidence JSON | rejected | Cosmetic; both are valid local/UTC representations. | reject |

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py` -- expected: PASS 24, FAIL 0, BLOCKED 5.
- `uv run python scripts/smoke_local_stack.py` -- expected: 12 PASS, 0 FAIL, 1 BLOCKED.
- `uv run python _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` -- expected: PASS or BLOCKED with reason.
- `G1_ALLOW_DESTRUCTIVE_RESET=1 uv run python _bmad-output/test-artifacts/g1/run_g1_live_acceptance.py` -- expected: PASS or BLOCKED with reason.

**Manual checks:**
- Inspect `_bmad-output/implementation-artifacts/sprint-status.yaml` after edits for consistent statuses.
- Verify `specs/corporate-kb/evidence/g1/` and `t04b/` contain no secrets, tokens, or real client/private endpoints.
