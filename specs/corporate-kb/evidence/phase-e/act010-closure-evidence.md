# ACT-010 closure evidence

## Intent

Owner approved an internal sandbox tenant for multi-tenant validation. ACT-010 closes by delivering a concrete tenant isolation specification, a parameterized provisioning skeleton, and a validation checklist so that T18a/T18b can be executed without waiting for an external client.

## Delivered artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Tenant isolation specification | `specs/corporate-kb/evidence/phase-e/internal-sandbox-tenant-spec.md` | Defines naming, isolation boundaries for Keycloak, GitLab, PostgreSQL and MinIO, network/domain rules, rollback steps and shared-resource risks. |
| Provisioning skeleton | `_bmad-output/test-artifacts/t18/provision-sandbox-tenant.sh` | Shell checklist with all values parameterized via environment variables and no hard-coded secrets. |
| Validation checklist | `_bmad-output/test-artifacts/t18/tenant-validation-checklist.md` | Step-by-step checklist covering identity, Git, KB Spaces, retrieval, object store, cross-tenant access denial and rollback. |
| Sprint status update | `_bmad-output/implementation-artifacts/sprint-status.yaml` | ACT-010 marked `done`; overall_percent updated to 90. |

## Acceptance criteria status

- Given the tenant spec, when reviewed, then it defines clear isolation boundaries for all four layers (GitLab, PostgreSQL, object store, Keycloak). **PASS**
- Given the provisioning script, when inspected, then all values are parameterized and no secrets are hard-coded. **PASS**
- Given the validation checklist, when reviewed, then it covers cross-tenant access denial and shared-resource risks. **PASS**
- Given the sprint status file, when updated, then ACT-010 is `done` and overall_percent is 90. **PASS**

## Verification commands

```bash
ls specs/corporate-kb/evidence/phase-e/internal-sandbox-tenant-spec.md
bash -n _bmad-output/test-artifacts/t18/provision-sandbox-tenant.sh
python -c "import yaml; yaml.safe_load(open('_bmad-output/implementation-artifacts/sprint-status.yaml'))"
```

All three checks completed without errors.

## Design alignment

- ADR-16 repository-per-Space rule is preserved: each Space maps to one repository under the tenant group.
- ADR-15 single-writer schema ownership is preserved: distinct `kb_authz_*`, `kb_ops_*`, `kb_index_*` schemas with dedicated roles.
- ADR-10 identity adapter contract is preserved: stable IDs, group snapshots, `AuthzContext` with `tenant_id`, revocation barrier.
- ADR-19 deferral is respected: T19/T20 remain deferred; this work does not expand scope.
- Sprint decision D3-DEC4 is referenced for future per-client bucket/account isolation.

## What is not claimed

- No real production resources were provisioned.
- No real client data or credentials were committed.
- Multi-tenant validation itself is not complete from documentation alone; T18a/T18b live runtime remains BLOCKED until the sandbox environment is available.
- Object-store ACL production engine recheck remains BLOCKED per G0-D16/T13/T16.
- Production AD, live SLO, HA and cross-client deployment remain deferred per G1-D6 and Phase E backlog.

## Sign-off

ACT-010 implementation completed and ready for review.
