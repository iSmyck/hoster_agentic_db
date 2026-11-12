# Internal sandbox tenant specification

## Scope

This document defines the synthetic internal sandbox tenant (`tenant-sandbox-01`) used to validate multi-tenant isolation for the Corporate KB platform without waiting for an external client deployment. It is intentionally minimal and shares the same GitLab, PostgreSQL, MinIO and Keycloak instances as the primary tenant, relying on namespace/schema/bucket/realm separation rather than dedicated infrastructure.

Full tenant-level network isolation and dedicated instances are out of scope for the launch validation slice. They remain deferred to post-launch Phase E work.

## Normative references

- `specs/corporate-kb/adr/ADR-016-repository-per-space.md` — one GitLab repository maps to exactly one Space; `space_id` is a stable lowercase slug.
- `specs/corporate-kb/adr/ADR-015-postgresql-schema-ownership.md` — per-client dedicated PostgreSQL instance with separate `kb_authz`, `kb_ops`, `kb_index` schemas and distinct DB roles.
- `specs/corporate-kb/adr/ADR-010-ldap-oidc-identity.md` — stable identity, group snapshots, `AuthzContext`, revocation SLO ≤ 30 minutes.
- `specs/corporate-kb/adr/ADR-019-t19-t20-deferred-business-gate.md` — T19/T20 remain deferred; multi-tenant validation is config-only baseline work.
- Sprint decision `D3-DEC4` — future DR tenant isolation uses separate buckets/accounts per client.

## Tenant naming convention

| Attribute | Value | Rationale |
|-----------|-------|-----------|
| `tenant_id` | `tenant-sandbox-01` | Synthetic, non-client, lexically stable. |
| `tenant_slug` | `sandbox-01` | Short form used in paths and DNS labels. |
| `tenant_label` | `Internal Sandbox 01` | Human-readable display label. |
| `base_domain` | `sandbox-01.example.local` | Placeholder domain; no real DNS registration. |
| `primary_tenant_id` | `tenant-primary` | Reference tenant for cross-tenant negative tests. |

Tenant IDs are lowercase alphanumeric with hyphens only. They are immutable once assigned to a Space, bucket, schema or realm to avoid orphaning policies, indexes or backups.

## Isolation boundaries

### 1. Identity / Keycloak

- A dedicated Keycloak realm named `corp-kb-sandbox-01` is created for the sandbox tenant.
- Realm contains two confidential OIDC clients:
  - `openwebui-sandbox-01` — upstream Open WebUI OIDC seam.
  - `identity-service-sandbox-01` — Corporate KB identity adapter.
- No shared client credentials between `tenant-primary` and `tenant-sandbox-01`.
- Realm-level group mappings are tenant-scoped; group names carry the tenant slug, e.g. `/sandbox-01/sales-authors`.
- `AuthzContext` issued by the identity adapter always includes `tenant_id`; services reject contexts where `tenant_id` does not match the requested Space or resource.
- Revocation barrier: group snapshots are refreshed at most every 15 minutes; sensitive operations (merge, export, retrieval of closed pages) re-check membership before payload delivery.

### 2. GitLab group and project isolation

- A top-level GitLab group `corp-kb-sandbox-01` is created for the tenant.
- Each Space maps to exactly one repository under this group, per ADR-16.
- Repository path format: `corp-kb-sandbox-01/<space-id>`.
- Scoped GitLab tokens for the Git Orchestrator are bound to the tenant group and carry only the required role (`Developer` for proposal push, `Maintainer` for protected branch/tag management).
- Cross-tenant path prefixing prevents repository ID collisions. Repository IDs used in GO merge locks include the full path, e.g. `corp-kb-sandbox-01/sales`.
- Webhooks and CI variables for the sandbox tenant must point to sandbox-specific service endpoints and secrets, never to the primary tenant.

### 3. PostgreSQL schema isolation

- The sandbox tenant uses a logically separate schema set within the same PostgreSQL instance used for the primary tenant, matching the minimal production target approved by the owner.
- Schema naming:
  - `kb_authz_sandbox_01` — identity/group snapshots and managed grants.
  - `kb_ops_sandbox_01` — proposals, decisions, operations, recovery barriers.
  - `kb_index_sandbox_01` — chunks, embeddings, index runs.
- Each schema has its own dedicated DB role:
  - `kb_authz_sandbox_01_writer` owns `kb_authz_sandbox_01`.
  - `kb_ops_sandbox_01_writer` owns `kb_ops_sandbox_01`.
  - `kb_index_sandbox_01_writer` owns `kb_index_sandbox_01`.
  - `kb_index_sandbox_01_reader` is the only role granted to the Retrieval service.
- Cross-schema writes are denied by DB role grants, not only by convention, per ADR-15.
- Alembic migrations for each owning component target the configured schema via the component's migration environment.

### 4. Object store / MinIO bucket isolation

- A dedicated MinIO bucket `corp-kb-sandbox-01` is provisioned for the tenant.
- Sub-bucket prefixes separate asset classes:
  - `corp-kb-sandbox-01/assets/` — immutable attachment revisions.
  - `corp-kb-sandbox-01/preflight/` — inactive index snapshots pending activation.
  - `corp-kb-sandbox-01/exports/` — portable export archives.
- Bucket policies deny cross-bucket access. The primary tenant's service credentials must not list, read or write `corp-kb-sandbox-01`.
- Object ACL and production engine recheck remain blocked by G0-D16/T13/T16; this specification records the intended bucket boundary only.

### 5. Network and domain considerations

- The sandbox tenant reuses the same local network as the primary tenant. No VLAN or firewall segmentation is required for this validation slice.
- Placeholder domain `sandbox-01.example.local` is used in service discovery and OIDC redirect URIs.
- Service-to-service calls must include the `X-Tenant-ID` header; the receiving service validates it against the tenant encoded in the `AuthzContext` or resource path.
- Egress from the sandbox tenant follows the same rules as the primary tenant: no external calls except to explicitly configured OIDC, embeddings and source endpoints.

## Rollback steps

1. Delete Keycloak realm `corp-kb-sandbox-01` and revoke all issued tokens.
2. Drop PostgreSQL schemas `kb_authz_sandbox_01`, `kb_ops_sandbox_01`, `kb_index_sandbox_01` and their roles.
3. Delete the MinIO bucket `corp-kb-sandbox-01` and any access policies tied to it.
4. Archive or delete GitLab group `corp-kb-sandbox-01` and its repositories.
5. Remove sandbox tenant entries from service configuration and secret stores.
6. Verify that no primary-tenant token, credential or configuration references the sandbox tenant.

## Shared-resource risks

| Risk | Mitigation | Validation gate |
|------|------------|-----------------|
| Same PostgreSQL instance | Logical schema + role separation; no shared search_path. | T18a schema-ownership negative test. |
| Same MinIO server | Separate bucket + distinct access keys per tenant. | T18a bucket ACL probe. |
| Same Keycloak server | Separate realm + separate clients. | T18a realm isolation probe. |
| Same GitLab server | Top-level group prefix per tenant. | T18a group/repository IDOR probe. |
| Cross-tenant AuthzContext leak | `tenant_id` in every context; services fail closed on mismatch. | T18b cross-tenant access denial test. |

## Out of scope

- Dedicated PostgreSQL/MinIO/Keycloak/GitLab instances or clusters.
- Tenant-level network segmentation (VLANs, firewalls).
- Production Active Directory integration.
- Real client corpus or production data.
- T19/T20 retrieval engine evolution and Fast/Trust/Scale policies (deferred per ADR-19).

## Change log

- 2026-11-12 — Initial version for ACT-010 closure.
