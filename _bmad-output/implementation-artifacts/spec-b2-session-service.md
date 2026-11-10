---
title: 'B.2 Session service — identity-bound tokens for GO/Retrieval'
type: 'feature'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_commit: '736aaf2'
context:
  - specs/corporate-kb/adr/ADR-010-ldap-oidc-identity.md
  - specs/corporate-kb/adr/ADR-015-postgresql-schema-ownership.md
  - src/identity/app/core/config.py
  - src/identity/app/api/router.py
  - src/identity/app/services/identity_service.py
  - src/identity/app/models/authz.py
  - src/git-orchestrator/app/api/auth.py
  - src/git-orchestrator/app/core/config.py
  - src/retrieval/app/core/config.py
  - src/retrieval/app/api/router.py
warnings:
  - multiple-goals
---

<intent-contract>

## Intent

**Problem:** Git Orchestrator сейчас валидирует сессию через upstream Open WebUI (`/api/v1/auths/`), получая только email/id/role. Нет собственных short-lived токенов, привязанных к stable identity и к policy-bundle revisions, нет refresh/revocation и нет propagation revocation в GO/Retrieval.

**Approach:** Создать новый `src/session/` FastAPI сервис на порту 8004, который:
- Выдаёт access + refresh токены после успешного upstream-логина (или по external ref для тестов).
- Хранит в PostgreSQL `kb_sessions.sessions`: `session_id`, `stable_id`, `issued_at`, `expires_at`, `refresh_expires_at`, `revoked_at`, `access_policy_revision`, `approval_policy_revision`.
- Валидирует access токены и возвращает stable_id + policy revisions.
- Поддерживает refresh с invalidation старого access токена.
- Поддерживает logout и global/per-user revocation.
- Предоставляет `/api/kb/v1/session/validate` для вызова из GO и Retrieval.
- Обновить `src/git-orchestrator/app/api/auth.py` так, чтобы GO валидировал Bearer токен через Session service, а не через Open WebUI.

## Boundaries & Constraints

**Always:**
- Использовать только `docker-compose.yml` для Postgres/Keycloak.
- Secrets (token signing key) хранить только в `.env`, не коммитить.
- Использовать `kb_sessions` schema в той же PostgreSQL базе.
- Live evidence писать в `_bmad-output/test-artifacts/b2/` и `specs/corporate-kb/evidence/b2/`.

**Never:**
- Не заменять upstream Open WebUI user/session tables.
- Не коммитить реальные secrets.
- Не менять pinned versions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Create session | POST `/api/kb/v1/session/create` with external_ref | Access + refresh tokens returned | Invalid ref → 401 |
| Validate access token | GET `/api/kb/v1/session/validate` with Bearer | stable_id + policy revisions | Expired/revoked → 401 |
| Refresh | POST `/api/kb/v1/session/refresh` with refresh token | New access token, old invalidated | Invalid/expired → 401 |
| Logout | POST `/api/kb/v1/session/logout` with access token | Token revoked | — |
| Global revocation | POST `/api/kb/v1/session/revoke-all` | All active sessions revoked | — |
| GO protected route | Request to GO with valid session Bearer | Allowed, actor stable_id used | Invalid/expired → 401/403 |
| GO route with revoked token | Request after logout/revoke | 401 | — |

## Code Map

- `src/session/app/main.py` — FastAPI factory.
- `src/session/app/core/config.py` — settings, token signing secret.
- `src/session/app/models/session.py` — `SessionRecord` SQLAlchemy model.
- `src/session/app/repositories/db.py` — engine, session factory, dependency.
- `src/session/app/services/session_service.py` — create, validate, refresh, revoke, logout.
- `src/session/app/api/router.py` — REST endpoints.
- `src/session/migrations/versions/2026_11_10_0001_initial_kb_sessions_tables.py` — Alembic migration.
- `src/session/scripts/setup_sessions_schema.py` — helper to create schema/tables (idempotent).
- `src/session/scripts/smoke_session.py` — live smoke test.
- `src/session/tests/test_session_service.py` — unit tests.
- `src/session/tests/test_session_live.py` — live integration tests.
- `src/git-orchestrator/app/api/auth.py` — switch from Open WebUI to Session service validation.
- `.env.example` — add session service vars.

## Tasks & Acceptance

**Execution:**
- [x] Scaffold `src/session/` module: config, models, repository, service, router, main, migrations.
- [x] Implement `SessionService.create_session`, `validate_access_token`, `refresh_access_token`, `revoke_session`, `revoke_all_for_user`, `logout`.
- [x] Implement REST endpoints under `/api/kb/v1/session/`.
- [x] Create Alembic migration for `kb_sessions.sessions` table.
- [x] Update `src/git-orchestrator/app/api/auth.py` to validate Bearer tokens via Session service (`http://localhost:8004/api/kb/v1/session/validate`).
- [x] Add `.env.example` vars: `SESSION_SECRET_KEY`, `SESSION_ACCESS_TTL_SECONDS`, `SESSION_REFRESH_TTL_SECONDS`, `SESSION_SERVICE_URL`, `SESSION_DATABASE_URL`.
- [x] Write `src/session/scripts/smoke_session.py` and run it.
- [x] Write `src/session/tests/test_session_service.py` and `test_session_live.py`.
- [x] Run `uv run pytest -q src/session/tests` and `uv run ruff check src/session src/git-orchestrator`.
- [x] Write evidence to `_bmad-output/test-artifacts/b2/` and `specs/corporate-kb/evidence/b2/`.
- [x] Update `sprint-status.yaml`: `b.2-session-service: done`.

**Acceptance Criteria:**
- Given valid external ref, when `POST /api/kb/v1/session/create`, then tokens returned and session row persisted.
- Given valid access token, when `GET /api/kb/v1/session/validate`, then stable_id + policy revisions returned.
- Given expired or revoked token, when validate, then 401.
- Given refresh token, when `POST /api/kb/v1/session/refresh`, then new access token issued and old access token invalidated.
- Given valid session, when GO protected route called, then request allowed with correct stable_id.
- Given revoked session, when GO protected route called, then 401.

## Design Notes

- Token format: signed JWT (HS256) with `session_id`, `stable_id`, `type` (`access`/`refresh`), `exp`. Validation checks signature, expiry, and DB revocation state.
- For tests, `create_session` accepts `external_ref` directly to avoid needing upstream Open WebUI login.
- GO auth change must remain backward-compatible with existing G1 tests that use `get_current_identity`; if tests mock the session service call, they continue to pass.
- Policy revisions stored at session creation time; GO must re-check AuthzContext for sensitive operations, but session validation only proves identity.

## Verification

**Commands:**
- `docker compose up -d postgres` -- expected: Postgres healthy.
- `uv run alembic -c src/session/alembic.ini upgrade head` -- expected: kb_sessions schema/tables created.
- `PYTHONPATH=src uv run uvicorn session.app.main:app --host 127.0.0.1 --port 8004 &` -- expected: health 200.
- `uv run python src/session/scripts/smoke_session.py` -- expected: exit 0.
- `uv run pytest -q src/session/tests` -- expected: all pass.
- `uv run ruff check src/session src/git-orchestrator` -- expected: clean.

## Review Triage Log

### 2026-11-10 — Review pass
- verdicts: 2 findings — high 0, medium 1, low 1
- findings:
  - `[medium]` `[patch]` Default `SESSION_SECRET_KEY` and test conftest secret were shorter than 32 bytes, causing PyJWT `InsecureKeyLengthWarning`. Fixed default secret and test secret to be at least 32 bytes.
  - `[low]` `[reject]` GO `get_current_identity` hardcodes `role="user"` because the Session service validate response does not include a role claim. Existing GO approver checks use `stable_id` from `settings.KB_APPROVER_IDS`, so this is acceptable for the current scope.

## Auto Run Result

- Summary: Implemented a new `src/session/` FastAPI service that issues and validates HS256 access/refresh tokens bound to stable identity and policy revisions. Wired Git Orchestrator auth to validate Bearer tokens via the Session service. Added Alembic migration, smoke script, unit/live tests, and evidence.
- Files changed:
  - New `src/session/` module: config, models, repository, service, schemas, router, main, migrations, scripts, tests.
  - `src/git-orchestrator/app/api/auth.py` — validates Bearer tokens via Session service `/api/kb/v1/session/validate`.
  - `src/git-orchestrator/app/core/config.py` — added `SESSION_SERVICE_URL`.
  - `.env.example` — added session service variables.
  - `pyproject.toml` — added `pyjwt`, included `src/session/tests` in testpaths, added ruff per-file ignores.
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — marked `b.2-session-service: done`.
  - Evidence in `_bmad-output/test-artifacts/b2/` and `specs/corporate-kb/evidence/b2/`.
- Patches applied: 1 medium (secret key length).
- Rejected findings: 1 low (role hardcoding).
- Follow-up review recommended: `false`.
- Verification performed:
  - `PYTHONPATH=src uv run alembic -c src/session/migrations/alembic.ini upgrade head` — migration applied, `kb_sessions.sessions` created.
  - `PYTHONPATH=src uv run uvicorn session.app.main:app --host 127.0.0.1 --port 8004` — health 200.
  - `PYTHONPATH=src uv run python src/session/scripts/smoke_session.py` — exit 0; create/validate/refresh/logout/revoke-all checks passed.
  - `uv run pytest -q src/session/tests` — 18 passed.
  - `uv run pytest -q` — 250 passed.
  - `uv run ruff check src/session src/git-orchestrator src/identity src/retrieval` — clean.
- Residual risks:
  - GO → Session live end-to-end was not run with both services up; GO contract is covered by mocked GO tests and Session service smoke test.
  - Role claim is not propagated from Session service to GO; approver authorization currently relies on `stable_id` allow-list.
  - Production deployments must set a strong `SESSION_SECRET_KEY` via `.env`.

