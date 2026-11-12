# Sandbox tenant isolation validation checklist

Tenant under test: `tenant-sandbox-01`
Primary tenant reference: `tenant-primary`

## Identity / Keycloak

- [ ] Realm `corp-kb-sandbox-01` exists and is distinct from the primary realm.
- [ ] Clients `openwebui-sandbox-01` and `identity-service-sandbox-01` do not share credentials with primary clients.
- [ ] Group paths include the tenant slug, e.g. `/sandbox-01/sales-authors`.
- [ ] `AuthzContext` returned for a sandbox user contains `tenant_id: tenant-sandbox-01`.
- [ ] Token issued for sandbox realm is rejected by primary-tenant service endpoints.
- [ ] Removing a user from the last sandbox group revokes managed grants within the agreed barrier.

## GitLab / Space isolation

- [ ] Group `corp-kb-sandbox-01` exists and primary-tenant users cannot access it.
- [ ] Space repository path follows `corp-kb-sandbox-01/<space-id>`.
- [ ] Git Orchestrator scoped token for sandbox cannot list or clone primary-tenant repositories.
- [ ] Merge serialization key includes the full repository path; two tenants with the same Space slug do not collide.
- [ ] Webhooks and CI variables for sandbox point to sandbox endpoints only.

## PostgreSQL schema isolation

- [ ] Schemas `kb_authz_sandbox_01`, `kb_ops_sandbox_01`, `kb_index_sandbox_01` exist.
- [ ] Each schema has a dedicated writer role; no role has write access to another tenant's schemas.
- [ ] Identity adapter writes only `kb_authz_sandbox_01`.
- [ ] Git Orchestrator writes only `kb_ops_sandbox_01`.
- [ ] Index worker writes only `kb_index_sandbox_01`.
- [ ] Retrieval service has read-only access to `kb_index_sandbox_01`.
- [ ] Running a component migration targets the configured schema and does not alter primary-tenant schemas.

## Object store / MinIO

- [ ] Bucket `corp-kb-sandbox-01` exists with `assets/`, `preflight/` and `exports/` prefixes.
- [ ] Sandbox service credentials can read/write only `corp-kb-sandbox-01`.
- [ ] Primary-tenant credentials are denied access to `corp-kb-sandbox-01` (list/read/write).
- [ ] Object ACL and production engine recheck status is recorded as BLOCKED if not yet available.

## Cross-tenant access denial

- [ ] User from `tenant-sandbox-01` querying a primary-tenant Space is rejected with 403/401.
- [ ] User from `tenant-primary` querying a sandbox-tenant Space is rejected with 403/401.
- [ ] `AuthzContext` with mismatched `tenant_id` is rejected by GO, retrieval and identity endpoints.
- [ ] Search/retrieval results from `kb_index_sandbox_01` are never returned to a primary-tenant query.

## Shared-resource risks

- [ ] Document that the sandbox shares the same PostgreSQL, MinIO, Keycloak and GitLab instances as the primary tenant.
- [ ] Confirm isolation is enforced by namespace/schema/bucket/realm/group boundaries, not by network separation.
- [ ] Record any deviation or bypass found during validation.

## Rollback verification

- [ ] Rollback script removes the sandbox realm, schemas, bucket and GitLab group.
- [ ] After rollback, no primary-tenant token, credential or configuration references the sandbox tenant.
- [ ] Rollback does not affect primary-tenant data or availability.

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| DevOps | | | |
| QA | | | |
| Security | | | |
