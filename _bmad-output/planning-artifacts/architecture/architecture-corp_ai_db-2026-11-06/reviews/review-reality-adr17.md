# AD-17 / ADR-17 deployment-topology reality check

**Review date:** 2026-11-09  
**Scope:** factual and status consistency only; no production, Kubernetes, shared multi-client, HA, chart, dedicated second-client, or restore execution was performed.  
**Verdict:** **CHANGES REQUESTED — two MEDIUM and two LOW documentation consistency findings. The pinned GitLab version and the synthetic/BLOCKED evidence claims themselves are accurate.**

## Inputs reviewed

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md`
- `specs/corporate-kb/architecture-spine.md` AD-17 and AD-11
- `specs/corporate-kb/architecture.md` deployment and ADR status sections
- `specs/corporate-kb/baseline.md`
- `specs/corporate-kb/g0-review.md`
- `specs/corporate-kb/evidence/t00/gitlab-capabilities.md`
- `specs/corporate-kb/evidence/t00/environment.md`
- `specs/corporate-kb/evidence/t18/summary.md`
- `specs/corporate-kb/evidence/t18a/summary.md`
- `specs/corporate-kb/evidence/t18b/summary.md`
- `specs/corporate-kb/repository-provisioning.md`
- `specs/corporate-kb/operations.md`
- `specs/corporate-kb/spec.md`
- `specs/corporate-kb/tasks.md`
- `specs/corporate-kb/adr/README.md`
- `specs/corporate-kb/adr/ADR-007-client-packaging-license.md`
- `docker-compose.yml`
- Pending AD-17 documentation diff against `HEAD`

## Findings

### ADR17-RR-01 — MEDIUM: the new `shared` profile conflicts with the still-active ADR-07 rejection of a shared deployment/data plane

**References:**

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:21` permits a common hardened GitLab instance for Standard.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:34` correctly acknowledges that this is a common admin/data/failure domain.
- `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:31` rejects “Единый shared deployment/data plane” for client delivery because it mixes client data/secrets and complicates isolation.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:90` links ADR-07 but does not identify a supersession or carve-out.

**Issue:** the later owner-approved AD-17/ADR-17 clearly permits a shared GitLab service, but the packaging ADR still rejects the same class of topology without explaining that its prohibition applies to a shared application/mixed-secret/mixed-canonical data plane rather than to a hardened shared GitLab instance with per-client groups, credentials, and backups. This is an unresolved rule conflict, not evidence that shared isolation has failed.

**Impact:** implementers can cite ADR-07 to reject the Standard topology or cite ADR-17 to build it, with no documented reconciliation of the previous decision.

**Required correction:** explicitly amend/supersede the ADR-07 alternative for this narrow case, or state in ADR-17 exactly which part of ADR-07 is superseded. Preserve the prohibitions on shared canonical repositories, credentials, mixed backups, and the unverified shared two-client gate.

### ADR17-RR-02 — MEDIUM: Kubernetes is introduced as an established application platform without reconciling the existing toolchain-neutral/Compose position

**References:**

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:11` states that the client application is deployed in its own Kubernetes namespace.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:19` makes Pod/StatefulSet/PVC lifecycle boundaries normative.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:34` relies on Kubernetes NetworkPolicy and namespace RBAC concepts.
- `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:24` says the ADR does not select a deployment toolchain.
- `specs/corporate-kb/spec.md:992` still refers to prepared Helm/Compose artifacts rather than selecting Kubernetes.
- `specs/corporate-kb/baseline.md:25-33` documents only local synthetic services, not a Kubernetes environment.
- `docker-compose.yml:52-66` is the existing Compose GitLab service definition using the same pinned image.

**Issue:** ADR-17 presents Kubernetes as existing context, not as an explicit new platform decision, and does not reconcile Compose or the prior toolchain-neutral decision. No Kubernetes runtime evidence is claimed, which is correct, but the platform assumption itself is new and silently changes the deployment baseline. This is not a new package/library dependency; it is an undocumented orchestrator selection.

**Impact:** a Compose-based delivery can be judged nonconforming even though Compose remains in the specification, while a Kubernetes delivery has no explicitly recorded selection boundary or validation baseline.

**Required correction:** either make the namespace/lifecycle language orchestrator-neutral, or explicitly record Kubernetes as the selected application deployment platform in the Decision/Alternatives and reconcile ADR-07 and `spec.md:992`. Keep Kubernetes/chart/HA execution BLOCKED until real evidence exists; do not infer a version, chart, or production capability.

### ADR17-RR-03 — LOW: the operations matrix can be read as claiming independent persistent state per client even in `shared` mode

**References:**

- `specs/corporate-kb/operations.md:65` assigns “независимые persistent state и per-client backups” to the GitLab platform service row covering both `shared` and `dedicated`.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:34` defines shared GitLab as a common trust/failure domain and refers to a common admin/data/failure domain.
- `specs/corporate-kb/operations.md:57` correctly requires per-client backups and separation from the application lifecycle.

**Issue:** “independent persistent state” is accurate only if it means independence from the application release lifecycle. Read as per-client persistent state, it contradicts the explicitly shared GitLab state/admin plane. The wording does not falsely claim a runtime PASS, but it obscures the actual isolation boundary.

**Impact:** an operator may assume shared clients have independent GitLab persistent state rather than only separate repositories, credentials, export/restore packages, and backup perimeters.

**Required correction:** state “persistent state independent of the application release lifecycle; shared-instance state remains a common data/failure domain” and retain per-client backup separation.

### ADR17-RR-04 — LOW: the external Reference Architecture mapping is not resolvable from project evidence

**Reference:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:7`.

**Issue:** the ADR cites “Reference architecture клиентских AI-решений внешнего трека v1.0” and RA-1/RA-3/RA-4/RA-10 without a path, link, or other retrievable source. A workspace search finds these identifiers only in this ADR. This review cannot confirm that those requirements exist or support the Kubernetes and Shared/Dedicated claims. This is an evidence-traceability gap, not a conclusion that the external document or requirements are invented.

**Impact:** the only cited external-track authority for the new topology cannot be independently checked against the project record.

**Required correction:** provide a sanitized, reviewable source reference and the relevant requirement text/mapping, or remove the unverifiable citation and rely on the recorded owner decision and internal R/I/AD links.

## Verified factual/status points

### Pinned GitLab baseline remains unchanged

- ADR-17 preserves GitLab CE `19.5.3-ce.0`: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:38`.
- The selected baseline is exactly GitLab CE `19.5.3-ce.0`, revision `0d4c9a9a2fa`: `specs/corporate-kb/baseline.md:12`.
- T00 evidence records the same version and synthetic-only sandbox scope: `specs/corporate-kb/evidence/t00/gitlab-capabilities.md:5` and `specs/corporate-kb/evidence/t00/environment.md:25`.
- G0-D2 approved the `19.5.3` role-based profile, not a different edition/version: `specs/corporate-kb/g0-review.md:15`.
- The existing Compose service uses `gitlab/gitlab-ce:19.5.3-ce.0`: `docker-compose.yml:53`.
- No AD-17 text claims that `19.5.3` is the latest/current GitLab release or invents a newer version, chart version, HA capability, or EE feature.

### T00 evidence is not misrepresented as deployment/HA/shared-production proof

- The 42 checks were performed on a real synthetic sandbox, not production: `specs/corporate-kb/evidence/t00/gitlab-capabilities.md:5,13`.
- T00 explicitly says no GitLab HA, backup appliance, or production network was tested: `specs/corporate-kb/evidence/t00/gitlab-capabilities.md:48-50`.
- ADR-17 repeats those limitations and marks unavailable checks BLOCKED: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:38`.
- The repository-per-Space and merge/protection probes do not establish shared multi-client isolation, Kubernetes lifecycle safety, chart correctness, or clean dedicated restore.

### T18/T18a/T18b synthetic results are not live deployment or restore proof

- T18 uses `synthetic_local_no_gitlab`: `specs/corporate-kb/evidence/t18/summary.md:7`; live pilot, restore, runbook, and second-client preparation checks are BLOCKED at lines 38-43; production pilot/full G3 readiness is disclaimed at line 63.
- T18a uses `synthetic_local_no_gitlab`: `specs/corporate-kb/evidence/t18a/summary.md:7`; the real second-client environment, object store, CI runner, and network perimeter are BLOCKED at lines 36-40; line 60 expressly disclaims production dedicated deployment PASS.
- T18b uses `synthetic_local_no_gitlab`: `specs/corporate-kb/evidence/t18b/summary.md:7`; live second-client restore, correction backup/restore, upgrade rehearsal, independent G3 review, and external source update are BLOCKED at lines 43-48; full T18/G3 remains BLOCKED at line 68.
- Their synthetic PASS rows therefore do not contradict ADR-17’s real-evidence BLOCKED status.

### Required real checks remain BLOCKED in the AD-17 documentation set

- ADR-17 marks real shared production instance, dedicated deployment, chart/HA, and restore drills BLOCKED: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:82`.
- The specification owner addendum marks production deployment, shared two-client isolation, and restore drills BLOCKED: `specs/corporate-kb/spec.md:14`.
- The architecture ADR map marks production instances, shared two-client isolation, dedicated deployment, and restore drills BLOCKED: `specs/corporate-kb/architecture.md:478`.
- Operations remains `DESIGN NOT EXECUTED`, defines mock evidence as non-PASS, and keeps real restore without clean GitLab/metadata/object storage BLOCKED: `specs/corporate-kb/operations.md:15,41,408`.
- G3 second-client, clean restore, upgrade, and owner-acceptance boxes remain unchecked: `specs/corporate-kb/operations.md:556-563`.
- The live tracker retains live second-client and G3 checks as BLOCKED despite synthetic task-harness DONE states: `specs/corporate-kb/tasks.md:38-40`.

### Topology and provisioning claims remain design, not production assignment

- AD-17 does not assign production instances or rollout: `specs/corporate-kb/architecture-spine.md:136`.
- ADR-17 leaves instance, endpoint, placement, network perimeter, and owner to deployment configuration: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:23`.
- Repository provisioning preserves repository=Space and adds only logical `gitlab_mode`/`gitlab_instance_id` fields: `specs/corporate-kb/repository-provisioning.md:16-20,39-41`.
- Actual instance/profile, namespaces, corpus mapping, and production cutover remain owner decisions: `specs/corporate-kb/repository-provisioning.md:88-95`.
- ADR-17 is accurately recorded as a separate 2026-11-09 owner decision rather than retroactively included in the 2026-11-08 G0 record: `specs/corporate-kb/architecture.md:460`, `specs/corporate-kb/tasks.md:56`, and `specs/corporate-kb/g0-review.md:6`.

### Dependency review

- The AD-17 documentation changes do not add a package, library, product service, chart, image, or pinned dependency.
- Existing GitLab CE remains the only GitLab product/version in the topology.
- The unrelated pending application/ingestion implementation changes were not treated as AD-17 evidence or as AD-17 dependency changes.
- The only technology-selection inconsistency found within AD-17 scope is the Kubernetes assumption in ADR17-RR-02.

## Residual verification gaps — all remain BLOCKED, not PASS

1. Real application-namespace install/upgrade/rollback/uninstall proof that GitLab repositories, MR metadata, protected tags, and storage are unchanged.
2. Selected production deployment chart and its pinned configuration; no chart is validated by T00/T18/T18a/T18b.
3. GitLab HA topology, failover, backup appliance, and production network behavior.
4. Real shared two-client GitLab isolation: read/propose/merge/export/restore denials, cross-client credential rejection, Group Owner/admin inventory, and privileged-bypass reconciliation.
5. Live dedicated second-client deployment from the same pinned core/template with independent endpoints, secrets, storage, network, backups, object store, CI, and egress.
6. Clean isolated per-client mirror + MR metadata + decisions/assets/policies/grants + immutable objects + required `kb_ops` restore for both profiles.
7. Shared-to-dedicated migration with explicit repository-ID mapping, full reconciliation, conservative recovery, and no copied plaintext secrets.
8. Retrieval of the cited external Reference Architecture v1.0 source and validation of RA-1/RA-3/RA-4/RA-10.

No project artifact other than this review was modified.
