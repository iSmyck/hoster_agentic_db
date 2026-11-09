# Epic 9 Retrospective: Identity + AuthZ adapter implementation

Date: 2026-11-09
Epic status: done
Stories: 9-1 I01, 9-2 I02, 9-3 I03, 9-4 I04

## What went well

- `src/identity/` FastAPI service bootstrapped with SQLAlchemy 2.0, Alembic, Pydantic v2.
- `kb_authz` schema and migrations for Identity, GroupSnapshot, PolicyBundle, AuthzContext, Revocation.
- APIs for identity resolution, group snapshot ingestion, policy activation, AuthzContext, path approval.
- PostgreSQL JSONB/SQLite fallback for tests.
- Code review found and fixed race conditions, empty-actor-ref bug, actor_type validation, error handling.
- 96 passed (1 skipped migration smoke test that needs PostgreSQL).

## What needs improvement

- `IdentityExternalRef` normalized table added late to fix race; early design should have included it.
- Migration smoke test skipped without local PostgreSQL.
- Real Keycloak/LDAP/OIDC adapter remains BLOCKED.

## Action items

- Add real IdP adapter implementations once endpoints are available.
- Add performance tests for group snapshot flattening at scale.
