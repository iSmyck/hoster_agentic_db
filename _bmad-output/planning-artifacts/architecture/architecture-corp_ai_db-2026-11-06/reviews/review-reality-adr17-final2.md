# AD-17 / ADR-17 final reality re-review 2

**Review date:** 2026-11-09  
**Scope:** closure of ADR17-FINAL-01 and factual/status review of the final client-level mode invariant, per-Space credential scopes, and per-Space backup wording against ADR-17 and ADR-16. No deployment, chart, HA, shared-client, dedicated-client, migration, credential-scope, or restore test was executed.  
**Verdict:** **PASS — NO ACTIONABLE FINDINGS. The remaining LOW finding is closed and no factual/status regression was found. This is not production/G3 readiness.**

## Closure and consistency results

### ADR17-FINAL-01 — CLOSED: client backup packages and restricted platform DR are distinct

- `specs/corporate-kb/repository-provisioning.md:7` now prohibits shared canonical repositories, managed credentials, and **client backup packages**, and separately assigns restricted platform-wide DR to ADR-17.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:41` permits platform-wide backup only as restricted control-plane DR, not as a client-issued artifact or per-client restore unit.
- The wording now matches `specs/corporate-kb/operations.md:57-59` and `specs/corporate-kb/architecture-spine.md:136`.

No remaining contradiction was found.

### Client-level mode invariant is internally consistent

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:43` defines `gitlab_mode`, `gitlab_instance_id`, endpoint, and client group as client-level values inherited by every Space, with no independent per-Space override.
- `specs/corporate-kb/repository-provisioning.md:34,39-40` repeats those values in per-Space records only as inherited read-only bindings and rejects mixed-mode/mixed-instance overrides.
- The same invariant appears in `specs/corporate-kb/spec.md:489`, `specs/corporate-kb/architecture-spine.md:136`, and `specs/corporate-kb/architecture.md:373`.
- This does not create a second repository/Space boundary: `repository-provisioning.md:16-20` and `ADR-016-repository-per-space.md:16-24` preserve one repository per Space and one ACL/cutover/index/export perimeter per repository.
- Existing-Space movement between modes remains prohibited and deferred, so the invariant does not conflict with a currently permitted migration: `ADR-017-gitlab-deployment-topology.md:42,89` and `architecture-spine.md:216`. A future migration ADR must preserve or deliberately revise the client-level invariant rather than silently switching one Space.

### Per-Space credential scopes strengthen, rather than change, repository=Space isolation

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:30-36` keeps client/capability separation while requiring every managed credential to have explicit `(tenant_id,space_id,repository_id,capability)` scope; client-group membership alone is not sufficient.
- `specs/corporate-kb/repository-provisioning.md:57-61` binds service identities to that scope, makes GO the sole normal merge actor for the specific Space repository, denies agent access to another Space by default, and limits CI/index to the specific repository.
- `specs/corporate-kb/operations.md:57,65` and `specs/corporate-kb/spec.md:489` use the same scope tuple. These rules implement the existing repository credential perimeter in `ADR-016-repository-per-space.md:17-22,26`; they do not merge Spaces or grant group-wide implicit access.
- The restricted platform admin/DR exception is explicitly outside client/GO normal managed paths and remains subject to inventory, audit, and G0-D3 handling: `ADR-017-gitlab-deployment-topology.md:38-40` and `operations.md:134`. It does not weaken the per-Space managed-credential rule.
- The planned two-client/two-Space wrong-credential and mixed-mode checks remain unexecuted design, not evidence of a passed runtime check: `ADR-017-gitlab-deployment-topology.md:84` and `test-plan.md:4,15,352-359`.

### Per-Space backup wording matches the canonical and operational perimeters

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:41` defines independent per-Space mirror/metadata/decisions/assets/policies/grants/object packages with separate snapshot closure and independent restore, inside a per-client outer perimeter.
- Client-level configuration and required durable `kb_ops` backups must identify their Space set and cannot replace per-Space closure or implicitly mix Space snapshots: `ADR-017-gitlab-deployment-topology.md:41,86` and `operations.md:57,395-397`.
- This is consistent with `ADR-016-repository-per-space.md:17-22`, which assigns clone/export, mirror backup, and restore to the repository=Space perimeter, and with `repository-provisioning.md:16-20,68`.
- Per-client wording remaining in summaries is the outer perimeter, not a mixed snapshot: `ADR-017-gitlab-deployment-topology.md:41,63-65` and `operations.md:57,65`. Restricted platform DR remains a separate control-plane artifact and is not a client restore package.

## Version and status regression check

- GitLab CE remains `19.5.3-ce.0`, revision `0d4c9a9a2fa`: `specs/corporate-kb/baseline.md:12`; ADR-17 preserves that pin at `ADR-017-gitlab-deployment-topology.md:44`.
- Real shared production, dedicated deployment, chart/HA, and restore drills remain BLOCKED: `ADR-017-gitlab-deployment-topology.md:90`, `spec.md:14`, and `architecture.md:478`.
- T18a remains `synthetic_local_no_gitlab`: `evidence/t18a/summary.md:7`; its live second-client infrastructure remains BLOCKED at lines 36-40.
- T18b live second-client restore, correction backup/restore, upgrade rehearsal, independent G3 review, and external source update remain BLOCKED: `evidence/t18b/summary.md:43-48`; full T18/G3 remains BLOCKED at line 68.
- The final A19 additions are test scenarios only; `test-plan.md:4,15` remains `design_not_executed` and does not convert the new mode/credential/backup checks into PASS.
- No new product, package, chart, image, version, production resource, or live capability claim was introduced by these clarifications.

## Deferred real-world checks — briefly

1. **Lifecycle/chart/HA:** prove application install/upgrade/recreate/rollback/uninstall and RBAC cannot mutate GitLab resources; validate the selected production chart, network, HA/failover, and backup appliance (`ADR-017-gitlab-deployment-topology.md:83,90`).
2. **Shared isolation and upgrades:** run two real clients with at least two Spaces each, cross-client and same-client wrong-Space denial, mixed-mode rejection, restricted admin/DR checks, and coordinated shared upgrade rehearsal (`ADR-017-gitlab-deployment-topology.md:84-85,88`).
3. **Dedicated second client:** execute config-only delivery with independent GitLab instance, endpoints, secrets, storage, network, backups, object store, CI, and egress (`evidence/t18a/summary.md:36-40`; `ADR-017-gitlab-deployment-topology.md:87`).
4. **Independent restore:** clean-restore every per-Space package with explicit `kb_ops` Space mapping and no other Space/client data; prove restricted platform DR is not a client restore package (`ADR-017-gitlab-deployment-topology.md:86`; `evidence/t18b/summary.md:43-48`).
5. **Full live G3:** real connector evidence, upgrade/rollback, completed runbooks, independent review, and owner operational acceptance remain open (`evidence/t18b/summary.md:43-48,68`; `operations.md:557-564`).
6. **Shared↔Dedicated migration:** remains DEFERRED/BLOCKED pending a separate ADR/runbook; it is not authorized as a config-only endpoint change (`ADR-017-gitlab-deployment-topology.md:42,89`; `architecture-spine.md:216`).

No project artifact other than this review was modified.
