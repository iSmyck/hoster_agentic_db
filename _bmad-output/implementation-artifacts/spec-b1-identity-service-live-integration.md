---
title: 'B.1 Identity service live integration with Keycloak sandbox'
type: 'feature'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_commit: '7809b493a4d01fd0775bb3ffc443fe3551c541ee'
context:
  - specs/corporate-kb/adr/ADR-010-ldap-oidc-identity.md
  - specs/corporate-kb/adr/ADR-015-postgresql-schema-ownership.md
  - src/identity/app/core/config.py
  - src/identity/app/adapters/keycloak.py
  - src/identity/app/services/identity_service.py
  - src/identity/scripts/setup_keycloak.py
  - src/identity/scripts/smoke_keycloak.py
  - src/identity/tests/test_keycloak_adapter.py
warnings:
  - multiple-goals
---

<intent-contract>

## Intent

**Problem:** Identity service имеет Keycloak adapter и synthetic тесты, но нет executable evidence live интеграции: realm/client не подняты, client secret не прописан, smoke-тесты не гонялись против реального Keycloak.

**Approach:** Поднять Keycloak + PostgreSQL из docker-compose, настроить realm `corp-kb`, client `identity-service`, audience mapper и тестового пользователя через `setup_keycloak.py`, получить client secret, обновить `.env`/`.env.example`, прогнать `smoke_keycloak.py` и pytest live-интеграции, зафиксировать найденные пробелы и evidence.

## Boundaries & Constraints

**Always:**
- Использовать только `docker-compose.yml` в проекте; не ставить standalone Keycloak.
- Secrets (client secret, admin password) хранить только в `.env` и не коммитить.
- Audience mapper включён, иначе token introspection для direct-access grants не работает.
- Live evidence писать в `_bmad-output/test-artifacts/b1/` и `specs/corporate-kb/evidence/b1/`.

**Never:**
- Не использовать production IdP/AD.
- Не коммитить реальные secrets.
- Не менять pinned versions (Keycloak 26.8.2, Open WebUI v0.13.0).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Sandbox up | `docker compose up -d postgres keycloak` | Keycloak responds on `localhost:8082` | Health timeout → FAIL |
| Realm setup | `setup_keycloak.py` with admin creds | Realm `corp-kb`, client `identity-service`, audience mapper, test user exist | 4xx/5xx → FAIL |
| Token fetch | Direct-access grant for test user | Access token returned | Invalid creds → FAIL |
| Introspection | `KeycloakIdentityAdapter.introspect_token` | Active introspection with `sub`, `preferred_username`, `groups` | Inactive/invalid → FAIL |
| Group fetch | `fetch_groups` for test user in `sales` group | Groups list contains `sales` | Empty groups → FAIL |
| Identity resolve | `resolve_identity_from_token` | Stable identity created/returned in `kb_authz` | Missing issuer/sub → FAIL |
| Revocation recheck | `recheck_group_membership` after user removed from group | New epoch, previous memberships expired | Adapter error → FAIL |

</intent-contract>

## Code Map

- `docker-compose.yml` — local Postgres + Keycloak services.
- `src/identity/app/core/config.py` — Keycloak URL, realm, client_id, client_secret settings.
- `src/identity/app/adapters/keycloak.py` — token introspection/userinfo/group fetch.
- `src/identity/app/services/identity_service.py` — `resolve_identity_from_token`, `fetch_upstream_groups`, `recheck_group_membership`.
- `src/identity/scripts/setup_keycloak.py` — idempotent realm/client/user bootstrap.
- `src/identity/scripts/smoke_keycloak.py` — existing smoke script.
- `src/identity/tests/test_keycloak_adapter.py` — existing adapter contract tests.
- `.env.example` — template for required env vars.

## Tasks & Acceptance

**Execution:**
- [x] `docker compose up -d postgres keycloak` — wait for health.
- [x] `uv run python src/identity/scripts/setup_keycloak.py` — bootstrap realm/client/user; capture client secret.
- [x] Update `.env` with `KEYCLOAK_CLIENT_SECRET` and other live values.
- [x] Update `.env.example` to document all Keycloak-related vars.
- [x] Run `uv run python src/identity/scripts/smoke_keycloak.py` and fix failures.
- [x] Run `uv run pytest -q src/identity/tests` against live Keycloak and fix failures.
- [x] Add live integration test for `resolve_identity_from_token` + `recheck_group_membership` if missing.
- [x] Write evidence to `_bmad-output/test-artifacts/b1/` and `specs/corporate-kb/evidence/b1/`.
- [x] Update `sprint-status.yaml`: mark B.1 done.

**Acceptance Criteria:**
- Given Keycloak sandbox is up, when `setup_keycloak.py` runs, then realm/client/audience mapper/test user exist.
- Given valid test user credentials, when token is fetched and introspected, then adapter returns active token with stable `sub` and groups claim.
- Given access token, when `resolve_identity_from_token` is called, then stable identity is persisted in `kb_authz`.
- Given user removed from group, when `recheck_group_membership` runs, then Space epoch advances and previous memberships expire.
- Given completed run, evidence contains no real production secrets or absolute paths under repo root.

## Design Notes

- Keycloak direct-access grant используется только для synthetic sandbox testing.
- Audience mapper обязателен: без него introspection endpoint для токена, выданного через direct-access grant, возвращает пустой active=false.
- Group claim mapping: в Keycloak по умолчанию группы не попадают в токен; нужен mapper `groups` или настройка realm roles.

## Verification

**Commands:**
- `docker compose up -d postgres keycloak` -- expected: both services healthy.
- `uv run python src/identity/scripts/setup_keycloak.py` -- expected: exit 0, realm/client/user created.
- `uv run python src/identity/scripts/smoke_keycloak.py` -- expected: exit 0, smoke evidence written.
- `uv run pytest -q src/identity/tests` -- expected: all pass.
- `uv run ruff check src/identity` -- expected: clean.

## Review Triage Log

### 2026-11-10 — Review pass
- verdicts: 28 findings — high 0, medium 2, low 0, false 0, maybe-false 0
- findings:
  - `[medium]` `[patch]` `sprint-status.yaml` dropped `action_items:` parent key, leaving the action-item list orphaned and producing invalid YAML — fixed by restoring the `action_items:` key.
  - `[medium]` `[patch]` `recheck_group_membership` change was only covered by skipped live Keycloak tests; added synthetic unit tests in `src/identity/tests/test_identity_service.py` that mock the adapter and assert matching snapshots expire, non-matching snapshots survive, and epoch/revocation advance.
  - `[low-rejected]` `setup_keycloak.py` prints the client secret to stdout — intentional and required by the intent so the secret can be copied into `.env`; not a leak because stdout is local to the operator running the script.
  - `[low-rejected]` `sales` group name is hardcoded in setup/test scripts — acceptable for the sandbox fixture scope; not configurable but not a defect.
  - `[low-rejected]` `test_keycloak_live.py` falls back to `admin`/`admin` admin credentials — only used when `KEYCLOAK_ADMIN_USER`/`KEYCLOAK_ADMIN_PASSWORD` are unset; sandbox defaults are documented.
  - `[low-rejected]` `load_dotenv(".env")` uses a relative path — project tests and scripts are invoked from the repository root per project convention.
  - `[low-rejected]` Evidence files are duplicated in `_bmad-output/test-artifacts/b1/` and `specs/corporate-kb/evidence/b1/` — intentional per the content pipeline standard and spec.
  - `[low-rejected]` Spec checkboxes were unchecked while sprint status marked B.1 done — fixed by checking the boxes after verification.

## Auto Run Result

- Summary: Implemented live Keycloak sandbox integration for the identity service: idempotent realm/client/user/group bootstrap via `setup_keycloak.py`, `.env`/`.env.example` wiring, smoke and pytest live evidence, a synthetic unit test for `recheck_group_membership`, and robustness fixes for the live test fixture.
- Files changed:
  - `src/identity/scripts/setup_keycloak.py` — loads `.env`, adds groups mapper, creates `sales` group, assigns test user, fetches/prints client secret.
  - `src/identity/scripts/smoke_keycloak.py` — loads `.env` automatically.
  - `src/identity/app/services/identity_service.py` — replaced deprecated `JSON.contains` with in-Python filtering for bounded space snapshots.
  - `src/identity/tests/test_keycloak_live.py` (new) — live Keycloak integration tests.
  - `src/identity/tests/test_identity_service.py` (new) — synthetic `recheck_group_membership` tests.
  - `.env.example` — added `KEYCLOAK_ADMIN_USER`/`KEYCLOAK_ADMIN_PASSWORD`.
  - `.env` — added live admin/test credentials and client secret (gitignored).
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — marked `phase-b: in-progress` and `b.1-identity-service-live-integration: done`.
  - Evidence reports and test output in `_bmad-output/test-artifacts/b1/` and `specs/corporate-kb/evidence/b1/`.
- Patches applied: 2 medium (sprint-status YAML fix, synthetic unit-test coverage).
- Rejected findings: 6 low/cosmetic items that are either intentional per the intent or acceptable sandbox defaults.
- Follow-up review recommended: `false`.
- Verification performed:
  - `docker compose up -d postgres keycloak` — services healthy (Keycloak 26.8.2, PostgreSQL/pgvector 0.8.7).
  - `uv run python src/identity/scripts/setup_keycloak.py` — exit 0, realm/client/user/group/audience mapper/groups mapper verified.
  - `uv run python src/identity/scripts/smoke_keycloak.py` — exit 0.
  - `uv run pytest -q src/identity/tests` — 44 passed, 1 deprecation warning.
  - `uv run ruff check src/identity` — clean.
- Residual risks:
  - Live tests require the Keycloak sandbox and are skipped otherwise; they do not replace production IdP/AD runtime certification.
  - Revocation SLO ≤ 30 minutes is enforced by design but not measured under production load.
  - Production IdP profile (AD/OpenLDAP/LDAPS/StartTLS) remains deferred per ADR-10.
