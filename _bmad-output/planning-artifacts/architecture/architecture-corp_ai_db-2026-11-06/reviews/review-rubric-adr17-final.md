# Final architecture reviewer-gate re-review — AD-17 / ADR-17

**Review date:** 2026-11-09  
**Mode:** read-only re-review of the current files after fixes; no deployment, lifecycle, isolation, restore, upgrade, rollback, or migration test was executed.  
**Scope:** closure of the four findings in `review-rubric-adr17.md`; historical debt is excluded.

## Verdict

**PASS — NO ACTIONABLE FINDINGS.**

All four previous findings are resolved without reopening the owner-selected topology. AD-17 remains a real and enforceable divergence decision: GitLab is outside the client application namespace/release lifecycle; Standard may use a hardened shared instance; Isolated/Dedicated uses a separate same-baseline, versioned-configuration instance; client code branches remain forbidden.

The restricted platform-wide DR artifact is now explicitly separated from client-facing backup/export/restore. Shared upgrades are platform-level all-tenant operations with no independent per-client version change/rollback. Existing-Space profile migration is DEFERRED and disallowed until a separate ADR and verified runbook. Lifecycle verification now covers all named release transitions, hooks, RBAC, and API deletion denial.

No production readiness or executed verification is inferred from this PASS.

## Previous-findings closure

| Previous finding | Result | Current evidence |
|---|---|---|
| F-01 HIGH — mixed instance-wide backup contradicted the no-shared-backup perimeter | **RESOLVED** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:18,38,60,83` limits the prohibition to client-facing artifacts/restore units and restricts platform-wide backup to control-plane DR inside the shared trust domain, never issued to a client or used for per-client restore. `specs/corporate-kb/spec.md:488,490`, `specs/corporate-kb/architecture-spine.md:136`, `specs/corporate-kb/architecture.md:373`, and `specs/corporate-kb/operations.md:57,59,65` use the same boundary. `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:17` and A19 at `specs/corporate-kb/spec.md:762` require independent client backup packages. AD-11/R14/R17 client portability and isolation are therefore preserved. |
| F-02 MEDIUM — shared upgrade/rollback lacked all-tenant coordination | **RESOLVED** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:42,85` requires affected-tenant inventory, compatible pinned target, coordinated maintenance/write freeze, backup readiness, rollback impact, startup reconciliation, per-client negatives, and staged activation; independent per-client version change/rollback is prohibited. `specs/corporate-kb/operations.md:459` carries the same pre-change and post-change controls, while `operations.md:469-479` retains authorized production reconciliation and conservative rollback checks. `specs/corporate-kb/spec.md:490`, `architecture-spine.md:136`, and `architecture.md:373` are aligned. |
| F-03 MEDIUM — bidirectional migration and canonical-authority handoff were incompletely specified | **RESOLVED BY EXPLICIT DEFERRAL** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:39,70,86` does not define or claim a migration protocol: existing-Space movement is DEFERRED and not permitted before a separate migration ADR and verified runbook. The listed single-writer freeze, exact linkage, stable IDs, conclusive reconciliation, and no-dual-write items are mandatory inputs to that future ADR, not current migration semantics or evidence. `specs/corporate-kb/architecture-spine.md:136,216`, `specs/corporate-kb/spec.md:490`, `specs/corporate-kb/architecture.md:373`, and `specs/corporate-kb/operations.md:57` consistently preserve the deferral. New-client dedicated provisioning remains permitted without implicitly copying an existing corpus. |
| F-04 LOW — lifecycle verification omitted install/upgrade/recreate and hook/API paths | **RESOLVED** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:22,80` covers install, upgrade, recreate, rollback, and uninstall; rendered manifests, lifecycle hooks, ServiceAccounts/controllers, RBAC, unchanged repositories/MR metadata/protected tags/workloads/PVC/refs, and API deletion denial. `specs/corporate-kb/operations.md:57`, `specs/corporate-kb/architecture.md:373`, and `specs/corporate-kb/architecture-spine.md:136` state the matching application-identity/resource boundary. |

## Final rubric walk

| Criterion | Result | Assessment |
|---|---|---|
| Real divergence point | **PASS** | ADR-17 lines 12–18 identify the application/data lifecycle coupling and distinct Standard versus Isolated/Dedicated isolation needs. |
| Enforceable AD-17 | **PASS** | ADR-17 lines 22–42 define concrete resource, tenant, credential, backup, migration-deferral, and upgrade controls; lines 80–87 provide corresponding verification and BLOCKED states. |
| Prevents stated problems | **PASS** | Application identities cannot own/manage GitLab resources; client canonical repositories, credentials, and client backup packages remain separate; Dedicated requires no client code branch. |
| Preserves AD-1–AD-16 / R01–R18 / I01–I14 | **PASS** | Repository=Space, GO-only managed merge, business users without GitLab accounts, canonical DecisionRecord linkage, independent client data/resources, export/restore closure, and rebuildable projections remain intact. Platform control-plane DR is no longer conflated with the AD-11/R14/R17 client backup package. |
| REQUIREMENT / DESIGN / UNKNOWN / DEFERRED / BLOCKED discipline | **PASS** | Accepted topology rules are normative; concrete production placement remains configuration/owner choice; migration is DEFERRED; unavailable real checks remain BLOCKED. |
| Operational envelope | **PASS** | Provisioning, credentials, privileged governance, client backup/restore, restricted platform DR, shared upgrade coordination, authorized rollback, and lifecycle negative controls are covered at design level. |
| ADR-07 packaging compatibility | **PASS** | ADR-07 lines 16–17, 24, and 31 preserve one reusable core, per-client resources and client backup packages, the ADR-17 Shared exception, and no shared application/PostgreSQL/index/object/secrets data plane. |
| A19 acceptance coverage | **PASS** | `specs/corporate-kb/spec.md:762` now requires both Shared two-client isolation and the Dedicated separate-instance profile, in addition to config-only delivery and independent client resources. |
| No production-evidence overclaim | **PASS** | ADR-17 lines 41 and 87 keep production chart/HA, real Shared/Dedicated deployment, and restore drills BLOCKED; this review executed none of them. |

## Remaining actionable findings

**NONE.**

## Deferred real-world verification gaps

These are open evidence gates, not architecture findings and not PASS:

1. **Shared two-client isolation:** execute on the real hardened instance: cross-client read/propose/merge/export/restore denial, credential rejection, absence of client Group Owners/cross-client Maintainer identities, direct-merge denial, and privileged unexpected-history quarantine. References: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:81-83,87`.
2. **Dedicated second-client delivery:** deploy config-only from the same pinned core/template with separate instance endpoints, secrets, storage, network rules, backups, and restore environment, without code edits. References: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:28,84,87`; `specs/corporate-kb/spec.md:762`.
3. **Lifecycle evidence:** run the specified synthetic install/upgrade/recreate/rollback/uninstall checks, including rendered hooks/RBAC and API deletion denial, before treating the lifecycle rule as verified. Reference: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:80`.
4. **Restore and Shared upgrade evidence:** perform clean isolated per-client restores in both profiles, prove restricted platform DR is never a client restore unit, and run the two-tenant Shared upgrade rehearsal with coordinated freeze, backups, reconciliation, negative controls, staged activation, and denial of independent per-client version change/rollback. References: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:83,85,87`; `specs/corporate-kb/operations.md:459`.
5. **Production deployment/HA:** real chart/deployment, HA, production Shared instance, Dedicated deployment, and production restore drills remain BLOCKED until authorized and executed. References: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:41,87`.
6. **Existing-Space profile migration:** remains DEFERRED/BLOCKED pending a separate owner-reviewed migration ADR and verified runbook; no migration capability or evidence is claimed by ADR-17. References: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:39,86`; `specs/corporate-kb/architecture-spine.md:216`.

This review authorizes no production instance, corpus movement, secret access, deployment, migration, destructive action, external egress, or paid call.
