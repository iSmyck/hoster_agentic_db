# AD-17 / ADR-17 final reality re-review

**Review date:** 2026-11-09  
**Scope:** recheck of ADR17-RR-01 through ADR17-RR-04 against current files, including the reviewed local reference input; factual/status consistency only. No deployment, chart, HA, shared-client, dedicated-client, migration, or restore test was executed.  
**Verdict:** **PASS WITH ONE LOW actionable documentation finding. All four previous findings are closed. No HIGH or MEDIUM finding remains. This is not production/G3 readiness.**

## Previous findings

### ADR17-RR-01 — CLOSED: Shared GitLab carve-out is explicit

- `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:4` identifies ADR-17 as the separate owner-approved placement exception.
- `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:17` permits Shared GitLab only with per-client groups/repositories, credentials, and backup/restore, while preserving a separate application/PostgreSQL/index/object/secrets data plane.
- `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:31` now rejects only the shared application/PostgreSQL/index/object/secrets data plane and explicitly allows Shared GitLab within ADR-17.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:24-28,37-38` consistently defines the two profiles, common trust/failure domain, and client-facing backup perimeter.

The former rule conflict is resolved.

### ADR17-RR-02 — CLOSED: Kubernetes is an owner-selected profile boundary, not a universal new mandate

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:12` explicitly scopes Kubernetes to the owner-described deployment profile and disclaims a Kubernetes requirement for all future standalone/on-prem profiles.
- `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:24` separately records that profile boundary and still does not select a packaging/orchestration tool.
- The reviewed reference input permits namespace, dedicated nodes, separate cluster, VM, or on-prem deployment at `/Users/antonsmychkin/Downloads/reference-architecture.md:18-24`, and expressly leaves Kubernetes non-mandatory for small standalone/on-prem solutions at line 190.
- ADR-17 introduces no new package/library/image/chart dependency and claims no Kubernetes runtime validation.

The former silent universal-platform selection is resolved. Real validation of the selected profile remains deferred below.

### ADR17-RR-03 — CLOSED: shared instance state is distinguished from per-client repositories/backups

- `specs/corporate-kb/operations.md:57` separates the common GitLab platform service from the application lifecycle and requires per-client credentials, mirrors, exports, durable operational backups, and restore environments.
- `specs/corporate-kb/operations.md:65` now explicitly says that `shared` has a common instance with separate client groups/repositories, `dedicated` has a separate instance, and both have per-client backup/restore.

The former persistent-state ambiguity is resolved in operations.

### ADR17-RR-04 — CLOSED: reference metadata, local source, and mappings were verified

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:8` records the exact title, v1.0, date 2026-10-29, RA identifiers, reviewed local path, and contextual/non-pinned status.
- `/Users/antonsmychkin/Downloads/reference-architecture.md:1-8` confirms the title, v1.0, owner, and date.
- RA-1 trusted tenant binding is present at source lines 84-88; RA-3 namespace-isolation limits at lines 97-102; RA-4 independent state lifecycle at lines 104-108; RA-10 backup/restore/upgrade/offboarding controls at lines 150-155.
- Source lines 169-181 explicitly describe a target architecture and production gate, not existing-site readiness, matching `ADR-017-gitlab-deployment-topology.md:14`.

The citation is now locally reviewable and the mappings are supported by the referenced text.

## Remaining actionable finding

### ADR17-FINAL-01 — LOW: repository provisioning still blanket-denies shared backups without the restricted platform-DR qualification

**References:**

- `specs/corporate-kb/repository-provisioning.md:7` says shared hosting “never implies shared canonical repositories, managed credentials or backups.”
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:38` permits a restricted platform-wide instance backup as a control-plane DR artifact inside the shared trust domain, while prohibiting cross-client mixed client artifacts/restore units.
- `specs/corporate-kb/operations.md:57-59` and `specs/corporate-kb/architecture-spine.md:136` contain the correct client-package/platform-DR distinction.

**Issue:** the unqualified “shared … backups” wording can prohibit the restricted platform-wide DR artifact that ADR-17 expressly allows. The intended prohibition is on shared client backup packages and client-facing restore units, not on the separately restricted platform control-plane DR artifact.

**Action:** qualify `repository-provisioning.md:7` as “shared client backup packages” or “shared client-facing backup/export/restore perimeter,” or add the ADR-17 restricted platform-DR exception. This is a wording correction only; it does not authorize a backup mechanism or change any verification status.

## Version and evidence status recheck

- GitLab CE remains `19.5.3-ce.0`, revision `0d4c9a9a2fa`: `specs/corporate-kb/baseline.md:12` and `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:41`. No current/latest release, EE, chart, or HA capability is invented.
- T00 remains a synthetic GitLab CE `19.5.3` sandbox with no HA, backup appliance, production network, real identities, or client documents: `specs/corporate-kb/evidence/t00/gitlab-capabilities.md:5,48-52`.
- T18a remains `synthetic_local_no_gitlab`; live second-client environment/object store/CI/network perimeter remains BLOCKED and no production dedicated deployment PASS is claimed: `specs/corporate-kb/evidence/t18a/summary.md:7,36-40,60`.
- T18b remains `synthetic_local_no_gitlab`; live second-client restore, correction backup/restore, upgrade rehearsal, independent G3 review, and external source update remain BLOCKED: `specs/corporate-kb/evidence/t18b/summary.md:7,43-48,68`.
- ADR-17 still marks real shared production instance, dedicated deployment, chart/HA, and restore drills BLOCKED: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:87`; `specs/corporate-kb/spec.md:14` and `specs/corporate-kb/architecture.md:478` retain the corresponding real-evidence gates.
- Existing-Space migration between Shared and Dedicated is now consistently DEFERRED and not authorized pending a separate ADR/runbook: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:39,70,86`, `specs/corporate-kb/architecture-spine.md:216`, `specs/corporate-kb/spec.md:490`, and `specs/corporate-kb/operations.md:57`.

## Deferred real-world verification gaps — BLOCKED, not findings or PASS

1. **Application lifecycle isolation:** real selected-profile manifests/RBAC and install/upgrade/recreate/rollback/uninstall proof that application identities cannot manage GitLab workloads/PVC and that repositories, refs, MR metadata, and protected tags remain unchanged (`ADR-017-gitlab-deployment-topology.md:80`).
2. **Production chart and HA:** selected/pinned deployment chart, production network, HA/failover, and backup-appliance behavior (`ADR-017-gitlab-deployment-topology.md:41,87`; `evidence/t00/gitlab-capabilities.md:48-50`).
3. **Real Shared two-client isolation:** cross-client read/propose/merge/export/restore denial, credential rejection, absence of client Group Owners/cross-client Maintainers, privileged-bypass reconciliation, and incident quarantine (`ADR-017-gitlab-deployment-topology.md:81-82`).
4. **Shared coordinated upgrade:** two-tenant rehearsal of affected-tenant inventory, coordinated freeze, backup readiness, startup reconciliation, negative controls, staged activation, and rejection of independent per-client version change/rollback (`ADR-017-gitlab-deployment-topology.md:42,85`; `operations.md:459`).
5. **Live Dedicated second client:** config-only deployment from the same pinned core/template with separate GitLab instance, endpoints, secrets, storage, network, backups, object store, CI, and egress (`ADR-017-gitlab-deployment-topology.md:84`; `evidence/t18a/summary.md:36-40`).
6. **Clean restore and DR separation:** per-client mirror/metadata/decisions/assets/policies/grants/objects/`kb_ops` clean isolated restore for both profiles; prove platform-wide DR is not client-issued or used as a per-client restore package (`ADR-017-gitlab-deployment-topology.md:83`; `evidence/t18b/summary.md:43-48`).
7. **Full live G3 acceptance:** real connector/source update, upgrade/rollback rehearsal, independent review, completed runbooks, and owner operational acceptance (`evidence/t18b/summary.md:43-48,68`; `operations.md:557-564`).
8. **Existing-Space Shared↔Dedicated migration:** DEFERRED/BLOCKED pending a separate migration ADR and verified single-writer/freeze, exact-linkage, stable-ID, reconciliation, and no-dual-write runbook; it must not be attempted as a config-only endpoint switch (`ADR-017-gitlab-deployment-topology.md:39,86`; `architecture-spine.md:216`).

No project artifact other than this final review was modified.
