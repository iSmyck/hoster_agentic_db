---
title: 'OIDC/Keycloak unified token seam for Open WebUI and KB services'
type: 'feature'
created: '2026-11-11'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '386b5d266bd2c77829bbf05431d3a831e6456bec'
context:
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py
  - scripts/local_stack.py
  - .env
  - src/identity/app/main.py
  - src/session/app/main.py
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** T04a live browser acceptance is BLOCKED because the `/kb` editor sends the Open WebUI native token to GO/session identity endpoints, which reject it with `INVALID_SESSION`. Phase B identity live integration also needs a real IdP seam.

**Approach:** Unify authentication on the existing sandbox Keycloak realm (`corp-kb`): configure Open WebUI for OIDC, make session/GO services trust Keycloak-issued tokens, and update the `/kb` editor to send the same OIDC token that Open WebUI uses.

## Boundaries & Constraints

**Always:**
- Use the existing sandbox Keycloak realm `corp-kb` and pinned versions.
- Keep Open WebUI token and session/GO token as the same OIDC token where the browser sends it.
- Preserve deny-by-default execution adapter and least-privilege rules (ADR-04).
- Record actual evidence; PASS or BLOCKED.
- Sanitize evidence before placing it in `specs/corporate-kb/evidence/`.

**Never:**
- Upgrade Open WebUI, Keycloak, or pinned baseline.
- Run production deploy, paid external calls, or production migrations.
- Present mocked integration as live PASS.
- Commit or push unless explicitly requested.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Open WebUI OIDC login | Browser redirects to Keycloak | User returns with valid OIDC token | Login error logged, fallback to local auth disabled |
| /kb editor identity call | OIDC token in Authorization | GO/session returns stable identity | 401 INVALID_SESSION if token rejected |
| Session service validation | Keycloak JWKS / userinfo | Stable identity + groups resolved | Fail closed if IdP unreachable |
| T04a harness | Full browser flow | PASS if identity seam works | FAIL/BLOCKED with explicit reason |

</frozen-after-approval>

## Code Map

- `scripts/local_stack.py` — must seed Keycloak users/groups and Open WebUI OIDC env vars.
- `.env` — add Open WebUI OIDC client credentials and redirect URIs.
- `src/identity/app/main.py` / adapters — verify Keycloak token and resolve stable identity.
- `src/session/app/main.py` — accept Keycloak-issued token instead of local session token for identity/me.
- `_bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` — harness that exercises the flow.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status tracker.

## Tasks & Acceptance

**Execution:**
- [x] Keycloak — created/configured `openwebui` OIDC client in `corp-kb` realm via `src/identity/scripts/setup_keycloak.py`.
- [x] `.env` — added OIDC env vars for Open WebUI and `IDENTITY_SERVICE_URL`.
- [x] `scripts/local_stack.py` — calls `setup_keycloak.py`, seeds test users/groups, exports OIDC env vars to Open WebUI.
- [x] `src/session/app/services/session_service.py` and `src/identity/app/api/router.py` — session service falls back to OIDC introspection via identity adapter; identity groups endpoint added.
- [x] `/kb` editor frontend — patched `open-webui/src/lib/apis/kb.ts` and backend oauth callback to expose `oidc_access_token` cookie.
- [x] `scripts/smoke_local_stack.py` — added OIDC config, Keycloak token, session OIDC validate, and GO `/identity/me` checks.
- [x] `_bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` — re-ran and captured evidence: 18 PASS / 0 FAIL / 0 BLOCKED.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — updated T04a to `verified`, ACT-001 to `done`, Phase B to `in-progress`, B.1/B.2 to `verified`.

**Acceptance Criteria:**
- Given Keycloak is running, when Open WebUI starts with OIDC env vars, then `/api/config` shows OAuth provider and auth enabled.
- Given a user logs in via Keycloak, when `/kb` editor calls `/api/kb/v1/identity/me`, then session/GO returns a stable identity.
- Given identity seam works, when T04a harness runs, then it completes with PASS or honest FAIL/BLOCKED.
- Given evidence is captured, when sprint status is updated, then T04a reflects the actual outcome.

## Review Triage Log

| Finding | Verdict | Evidence | Route |
|---|---|---|---|
| Hardcoded G1 test user passwords in source | medium | Moved passwords to `.env` (`KEYCLOAK_G1_*_PASSWORD`); `setup_keycloak.py` fails closed if unset. | patch |
| Raw f-string injection into `localStorage` could break on quotes/backslashes | medium | Replaced with `page.evaluate("(token) => localStorage...", json.dumps(token))`. | patch |
| Hardcoded PostgreSQL DSN fallback in harness | low | Removed fallback; harness now requires `GO_DATABASE_URL`/`DATABASE_URL`. | patch |
| OIDC fallback triggered for any `TOKEN_INVALID` (including expired session tokens) | medium | Added `_looks_like_oidc_token()` heuristic using issuer check + `OIDC_ISSUER` config. | patch |
| OIDC approver role silently downgraded to `user` if groups endpoint fails | medium | Made groups failure raise `TOKEN_INVALID` (fail-closed). | patch |
| `role` claim in GO auth not validated | low | Added allowlist `{"user", "admin"}` with default `"user"`. | patch |
| Identity router rejected lowercase `bearer` scheme | low | Made `Authorization` scheme check case-insensitive. | patch |
| `setup_keycloak.py` docstring contradicted `.env` writes | low | Updated docstring to describe actual behavior. | patch |
| Frontend patch not visible in git diff | rejected | Open WebUI checkout lives in untracked `_bmad-output/test-artifacts/t00/...`; diff cannot include it. | reject |
| ROPC grant used in harness | rejected | Acceptable for sandbox automation; real browser OIDC flow verified separately. | reject |

## Verification

**Commands:**
- `uv run python scripts/local_stack.py` — starts full stack with OIDC.
- `curl http://localhost:3100/api/config` — shows OAuth provider.
- `uv run python scripts/smoke_local_stack.py` — expected: 17 PASS / 0 FAIL / 0 BLOCKED.
- `uv run python _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py` — expected: 18 PASS / 0 FAIL / 0 BLOCKED.

**Manual checks:**
- Login to Open WebUI via Keycloak in browser; verify `/kb` page loads and Submit proposal is enabled.
