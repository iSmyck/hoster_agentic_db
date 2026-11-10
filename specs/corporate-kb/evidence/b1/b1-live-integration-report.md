# B.1 Identity service live integration with Keycloak sandbox — Evidence

**Date:** 2026-11-10  
**Spec:** `_bmad-output/implementation-artifacts/spec-b1-identity-service-live-integration.md`  
**Pinned versions:** Keycloak `26.8.2`, PostgreSQL `18.6` + pgvector `0.8.7`

## Scope

Close implementation gaps WP-00–WP-05 for the Identity + AuthZ adapter by wiring it to a live Keycloak sandbox:

- Realm `corp-kb`, client `identity-service`, audience mapper, groups mapper, test user in `sales` group.
- Client secret captured and stored in `.env` (not committed).
- Smoke test and pytest live integration executed against the running sandbox.

## Infrastructure state

Services started from the project `docker-compose.yml`:

```text
$ docker compose up -d postgres keycloak
```

Both services healthy; Keycloak reachable on `localhost:8082`, PostgreSQL on `localhost:5432`.

## Bootstrap

```text
$ uv run python src/identity/scripts/setup_keycloak.py
Keycloak admin: http://localhost:8082
Realm 'corp-kb' already exists
Client 'identity-service' already exists
Audience mapper 'identity-service-audience' already exists
Added groups mapper 'groups'
Test user 'testuser' already exists
Group 'sales' already exists
Added test user to 'sales' group

# Client secret (copy to .env as KEYCLOAK_CLIENT_SECRET):
<REDACTED>
```

The client secret was written to `.env` as `KEYCLOAK_CLIENT_SECRET`; `.env.example` documents all Keycloak-related variables.

## Smoke test

```text
$ uv run python src/identity/scripts/smoke_keycloak.py
Keycloak: http://localhost:8082
Realm: corp-kb
Resolved identity:
  id: <uuid>
  external_refs: [{
    'sub': '<uuid>',
    'name': 'Test User',
    'email': 'test@example.com',
    'issuer': 'http://localhost:8082/realms/corp-kb',
    'given_name': 'Test',
    'family_name': 'User',
    'preferred_username': 'testuser'
  }]
  created_at: <iso>
```

Exit code: `0`.

## Test results

```text
$ uv run pytest -q src/identity/tests
44 passed in 3.80s
```

The live integration tests (`src/identity/tests/test_keycloak_live.py`) verify:

1. Token introspection returns `active=True`, `sub`, `preferred_username`, and `groups` containing `sales`.
2. `resolve_external_refs` normalizes issuer + sub + profile claims.
3. `fetch_groups` returns the `sales` group.
4. `resolve_identity_from_token` persists a stable `Identity` in `kb_authz` and is idempotent.
5. `recheck_group_membership` advances the Space epoch and expires previous snapshots when the user is removed from `sales`.
6. Invalid tokens raise `IdentityAdapterError`.

Synthetic unit tests in `src/identity/tests/test_identity_service.py` verify `recheck_group_membership` without requiring a live Keycloak instance.

## Configuration changes

- `.env` updated with live Keycloak values (admin/test credentials + captured client secret).
- `.env.example` updated to document all Keycloak-related variables:
  - `IDENTITY_ADAPTER`
  - `KEYCLOAK_URL`
  - `KEYCLOAK_REALM`
  - `KEYCLOAK_CLIENT_ID`
  - `KEYCLOAK_CLIENT_SECRET`
  - `KEYCLOAK_ADMIN_USER`
  - `KEYCLOAK_ADMIN_PASSWORD`
  - `KEYCLOAK_TEST_USERNAME`
  - `KEYCLOAK_TEST_PASSWORD`

## Code changes

- `src/identity/scripts/setup_keycloak.py`
  - Loads `.env` automatically.
  - Creates `sales` group and assigns the test user.
  - Adds `groups` protocol mapper so group membership appears in access-token introspection.
  - Fetches and prints the client secret for `.env` wiring.
  - Idempotent re-runs are safe.

- `src/identity/scripts/smoke_keycloak.py`
  - Loads `.env` automatically so the script works with `uv run python ...` without manual exports.

- `src/identity/app/services/identity_service.py`
  - Replaced deprecated `JSON.contains` SQL expression in `recheck_group_membership` with an in-Python filter + `id.in_` update.

- `src/identity/tests/test_keycloak_live.py` (new)
  - Live integration tests against Keycloak; skipped automatically if `IDENTITY_ADAPTER != keycloak` or `KEYCLOAK_CLIENT_SECRET` is missing.

- `src/identity/tests/test_identity_service.py` (new)
  - Synthetic `recheck_group_membership` tests that mock the adapter and run without Keycloak.

## Validation

- `uv run ruff check src/identity` — clean.
- `uv run pytest -q src/identity/tests` — 44 passed.
- `uv run python src/identity/scripts/smoke_keycloak.py` — exit 0.

## Open / risky items

- The live tests require the Keycloak sandbox to be running; they are skipped otherwise. They are not a replacement for production AD/LDAP runtime certification.
- Revocation SLO ≤ 30 minutes is enforced by design (group recheck before sensitive operations + epoch invalidation) but not measured under production load.
- `recheck_group_membership` uses a coarse per-space filter; future scale testing should verify snapshot row counts remain bounded.
- Production IdP profile (AD/OpenLDAP/LDAPS/StartTLS) remains deferred per ADR-10.
- `Base.metadata.create_all` fails against PostgreSQL because the GIN index on `identities.external_refs` targets the generic `JSON` type instead of `JSONB`. This pre-existing schema incompatibility means the identity service test suite currently relies on SQLite. It must be resolved before the service can run against the project PostgreSQL database.
