# Final adversarial re-review — AD-17 / ADR-17

Date: 2026-11-09  
Scope: re-check of the previous review's CRITICAL/HIGH findings against the current artifacts only. Historical portability debt and unrelated architecture issues are excluded. This is a static document review; no deployment, restore, migration, or lifecycle operation was executed.

## Verdict

**CHANGES REQUIRED — 0 CRITICAL, 4 HIGH remaining findings.**

The unsafe active migration rule is removed. Existing canonical Space migration is now explicitly DEFERRED/BLOCKED pending a separate ADR/runbook, so the previous repository-ID, note-ID, dual-write, and migration-time stable-ID findings are not current implementation permissions. The Shared acceptance wording and application-lifecycle controls are materially corrected. Four contradictions/under-specified boundaries remain inside the new ADR-17 deployment scope.

## Disposition of previous CRITICAL/HIGH findings

| Previous finding | Current disposition | Current evidence |
|---|---|---|
| ADR17-ADV-01 repository-ID migration | **Closed for current ADR-17 scope; deferred protocol work** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:39,86`; `specs/corporate-kb/architecture-spine.md:216` |
| ADR17-ADV-02 Decision-Note-ID migration | **Closed for current ADR-17 scope; deferred protocol work** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:39,86`; `specs/corporate-kb/architecture-spine.md:216` |
| ADR17-ADV-03 dual-write/single-canonical migration | **Closed for current ADR-17 scope; single-writer freeze/no-dual-write is a future migration prerequisite** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:39`; `specs/corporate-kb/architecture-spine.md:216` |
| ADR17-ADV-04 Shared vs “no shared canonical store” | **Resolved** | `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:17,31`; `specs/corporate-kb/test-plan.md:354-358`; `specs/corporate-kb/spec.md:762` |
| ADR17-ADV-05 tenant-wide vs per-Space mode | **Remains HIGH — ADR17-FINAL-01** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:23-27,40`; `specs/corporate-kb/repository-provisioning.md:34-40,54-55` |
| ADR17-ADV-06 migration-time IdP/stable-ID change | **Closed for current ADR-17 scope; deferred protocol work** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:39,86`; `specs/corporate-kb/architecture-spine.md:216` |
| ADR17-ADV-07 cross-client tokens vs platform control plane | **Remains HIGH — ADR17-FINAL-02** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:30-38` |
| ADR17-ADV-08 per-client vs per-Space credentials | **Remains HIGH — ADR17-FINAL-03** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:30-34,81`; `specs/corporate-kb/adr/ADR-016-repository-per-space.md:17-22` |
| ADR17-ADV-09 per-client vs per-Space backup/restore | **Remains HIGH — ADR17-FINAL-04** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:38,83`; `specs/corporate-kb/operations.md:392-400` |
| ADR17-ADV-10 application-lifecycle verification | **Resolved** | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:22,80`; `specs/corporate-kb/architecture.md:373`; `specs/corporate-kb/operations.md:57` |

---

## Remaining actionable findings

### ADR17-FINAL-01 — HIGH: tenant-wide mode still conflicts with independently writable per-Space mode/instance fields

**References:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:23-27,40`; `specs/corporate-kb/repository-provisioning.md:7,32-40,54-55`.

ADR-17 still says that the tenant profile selects one mode and gives the client one private group. The provisioning registry still requires `gitlab_mode` and `gitlab_instance_id` on every Space, and its creation order approves the profile per Space. No invariant requires those values to be identical for every Space belonging to one client.

Two registry writers can therefore produce:

- **Unit A:** all Spaces inherit one client-level `shared` or `dedicated` mode and one logical instance;
- **Unit B:** one Space is `shared` and another is `dedicated`, with separate instance/group/credential/backup boundaries, while each row individually satisfies the provisioning schema.

Deferring migration of an existing Space does not resolve B for a newly provisioned multi-Space client. It also leaves unclear whether a temporary mixed-mode layout is ever valid.

**Action:** make mode and logical instance client-level values referenced by every Space, or explicitly define a mixed-mode topology and its group/credential/backup model. If mixed mode is permitted only during a future migration ADR, prohibit it in the ordinary per-Space provisioning contract.

### ADR17-FINAL-02 — HIGH: the absolute cross-client-token ban still conflicts with privileged platform duties

**References:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:30-38`; `specs/corporate-kb/operations.md:27-28,65`.

Decision 6 still categorically prohibits cross-client tokens. Decisions 7–9 still require platform-owned group/repository protections and privileged inventory on a shared instance and permit a restricted platform-wide DR artifact. The new DR/client-backup distinction resolves artifact ownership, but does not state whether the absolute token prohibition has a platform control-plane exception.

Two credential models remain textually incompatible:

- **Unit A:** only per-client credentials exist, satisfying Decision 6 but providing no single identity for instance-wide administration/DR;
- **Unit B:** a restricted instance-admin/control-plane identity manages shared protections and DR, satisfying Decisions 7–9 but possessing cross-client capability prohibited by the unqualified Decision 6 wording.

**Action:** scope the prohibition explicitly to tenant/runtime credentials and define the separate platform control-plane credential class, its exact permissions, non-tenant ownership, inventory, audit, emergency authorization, and incident/quarantine propagation. If DR uses only local/root-only tooling rather than an API token, state that instead of leaving an implicit exception.

### ADR17-FINAL-03 — HIGH: per-client identity separation still does not enforce the existing per-Space credential perimeter

**References:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:30-34,81`; `specs/corporate-kb/adr/ADR-016-repository-per-space.md:17-22,46-48,64-67`; `specs/corporate-kb/contracts/gitlab-integration.md:21-28`; `specs/corporate-kb/repository-provisioning.md:57-61`.

ADR-17 still requires credentials to differ by client and capability, and its new two-client verification still tests only cross-client rejection. ADR-16 continues to place GO/agent/connector credentials and clone/export/restore inside each repository=Space perimeter.

Consequently:

- **Unit A:** one group-scoped GO merge or CI identity per client is inherited by every Space repository, satisfying the ADR-17 client/capability wording and its cross-client test;
- **Unit B:** credentials are scoped per client, capability, and repository, so a Space-A credential is denied by Space B of the same client.

Only B demonstrates the credential portion of repository=Space isolation. The current ADR-17 verification can accept A without detecting the same-client cross-Space capability.

**Action:** require effective authorization scope `(client,Space/repository,capability)`, even where an account object is reused. Add same-client/cross-Space denial vectors for proposal, merge, CI read, mirror, export, and restore credentials to ADR-17/A19 or explicitly link them to an expanded A32 oracle.

### ADR17-FINAL-04 — HIGH: per-client backup verification still permits an implicit mixed-Space snapshot/restore unit

**References:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:38,83`; `specs/corporate-kb/adr/ADR-016-repository-per-space.md:17-22,28,46-48,59`; `specs/corporate-kb/operations.md:392-400,410-425`.

ADR-17 still defines the client-facing package only at per-client granularity and verifies only exclusion of another client. It does not say that the client package must contain independently consistent per-Space subpackages. Existing operations rules still require per-Space exact snapshots, reject an implicit mixed multi-Space snapshot, and reopen restored targets separately.

Two backup units remain possible under the ADR-17-only oracle:

- **Unit A:** one group-level client snapshot aggregates every Space and restores them together;
- **Unit B:** a client outer perimeter contains separate per-Space mirrors, manifests, positions, and independently restorable subpackages.

A can satisfy the stated per-client/cross-client check while violating the existing snapshot consistency and independent recovery rules.

**Action:** define the client package as an outer administrative perimeter containing mandatory per-Space subpackages with exact repository/HEAD/ref/policy/object/operational positions. Require independent and combined restores, same-client cross-Space negatives, drift detection, and proof that restoring one Space neither exposes nor mutates another Space.

---

## Deferred real-world verification gaps — not additional findings

1. **Existing canonical Space profile migration:** remains DEFERRED/BLOCKED pending a separate migration ADR and verified runbook covering single-writer freeze, repository/note/tag/merge linkage, stable IDs, DecisionRecord/export verification, conclusive reconciliation, and no dual-write (`specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:39,86`; `specs/corporate-kb/architecture-spine.md:216`).
2. **Shared two-client security evidence:** real cross-client read/proposal/merge/export/restore denial, credential rejection, Group Owner restrictions, and privileged unexpected-history quarantine remain unexecuted (`specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:81-82,87`).
3. **Dedicated repeatability and production topology:** the second config-only Dedicated deployment, real chart/HA behavior, production instances/endpoints, and separate storage/network/secrets remain BLOCKED pending real evidence (`specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:41,84,87`).
4. **Backup/restore and DR evidence:** per-client clean isolated restore, required `kb_ops` recovery, and proof that restricted platform-wide DR is neither client-visible nor a client restore unit remain unexecuted (`specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:83,87`; `specs/corporate-kb/operations.md:408-425`).
5. **Lifecycle negative evidence:** synthetic install/upgrade/recreate/rollback/uninstall with hooks/RBAC inspection, before/after GitLab inventories and stored refs, and application-identity API deletion denial remain unexecuted (`specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:80`).
6. **Shared coordinated upgrade evidence:** two-tenant affected-inventory, coordinated freeze, backup readiness, startup reconciliation, per-client negatives, staged activation, and rejection of independent version change/rollback remain unexecuted (`specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:42,85`).
