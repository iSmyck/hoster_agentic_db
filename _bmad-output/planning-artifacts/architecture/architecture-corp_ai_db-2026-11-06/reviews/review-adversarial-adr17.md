# Adversarial review — AD-17 / ADR-17 GitLab deployment topology

Date: 2026-11-09  
Review type: static adversarial architecture/document review; no deployment, migration, backup, or restore was executed.  
Primary object: `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md` and `specs/corporate-kb/architecture-spine.md` AD-17.  
Method: construct alternative deployment/GO/backup units from the written rules and test them against Git-native canonical storage, repository=Space, merge-only-GO, privileged Owner incident handling, dedicated client resources, portability, and traceability.

## Verdict

**FAIL / CHANGES REQUIRED — 2 CRITICAL, 8 HIGH, 2 MEDIUM findings.**

ADR-17 makes a coherent high-level distinction between a shared GitLab service and separate canonical repositories, but its migration rule is not compatible with the existing canonical identity/proof model without additional contracts. In particular, a new GitLab instance can change repository and note identities that are embedded in immutable DecisionRecords, policies, merge trailers, dedupe keys, and authorization principals. The current verification section can also report success for backup and lifecycle implementations that the existing operations rules reject.

This verdict does not reopen owner-approved G0-D2/G0-D3 or claim that the Shared profile is intrinsically impossible. It identifies missing normative rules and acceptance oracles needed before ADR-17 can be implemented interoperably.

---

## ADR17-ADV-01 — CRITICAL: `repository_id` remapping has no canonical continuity contract

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:36`; `specs/corporate-kb/repository-provisioning.md:17,34-48`; `specs/corporate-kb/contracts/decision-record.schema.json:5,8-27,43-47,105-107`; `specs/corporate-kb/contracts/access-policy.schema.json:29-32,64-68`; `specs/corporate-kb/adr/ADR-013-merge-serialization-recovery.md:27`; `specs/corporate-kb/contracts/export-manifest.schema.json:315-317`.

**Trigger:** ADR-17 requires a new trusted instance/repository binding and says that `repository_id` after restore is not necessarily the old value, but does not define whether `repository_id` is an immutable platform-logical ID or the instance-assigned GitLab project ID. Provisioning separately names a stable repository binding and `gitlab_project_id`, while canonical contracts contain only `repository_id`.

**Two incompatible units:**

- **Unit A — stable logical ID.** Preserve the old `repository_id` forever and add a verified mapping to a new `gitlab_project_id` on the dedicated instance. Existing DecisionRecord hashes, access/approval policies, and `(repository_id,target_branch,proposal_sha)` dedupe keys remain valid.
- **Unit B — instance-native ID.** Assign the new GitLab project ID as `repository_id` and record an old→new verified mapping, which is also a reasonable reading of ADR-17. Existing canonical DecisionRecords and policies still contain the old ID, and old merge proof is required to be verified in `decision_record.repository_id`.

A and B cannot consume each other's restored state without an additional alias/rebinding protocol. B changes the meaning of hashed canonical records without changing their bytes, invalidates policy/repository equality, and partitions merge dedupe/recovery keys. Editing the records or policies to the new ID is not a workaround: it changes canonical hashes and must not be done by rewriting Git history or mutating an append-only DecisionRecord.

**Potential consequence:** restored decisions become `invalid`, policies fail activation, conservative recovery quarantines every target, or two implementations disagree about whether an old proposal was already applied. A claimed successful shared→dedicated migration can therefore lose canonical audit continuity and write availability.

**Required guard:** define an immutable platform-logical `repository_id` separate from instance-scoped `gitlab_project_id` and `gitlab_instance_id`, with a signed/versioned binding history. If rekeying is intended instead, specify a versioned authenticated alias contract covering canonical DecisionRecords, ProposalRecords, access/approval policies, export manifests, projections, locks/barriers, events, and dedupe keys. Add shared→dedicated and dedicated→shared tests that restore old decisions/policies and replay an old `(repository_id,target_branch,proposal_sha)` without a second merge.

---

## ADR17-ADV-02 — CRITICAL: migration does not preserve or alias `Decision-Note-ID`

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:36,81`; `specs/corporate-kb/contracts/gitlab-integration.md:71-73`; `specs/corporate-kb/contracts/export-manifest.schema.json:310-317`; `specs/corporate-kb/adr/ADR-013-merge-serialization-recovery.md:21-28`; `specs/corporate-kb/operations.md:413,420`.

**Trigger:** GitLab assigns `note_id` after note creation. Immutable merge commits contain the original `Decision-Note-ID`, and merged proof requires that trailer to equal the restored note's `note_id`. ADR-17 provides a mapping rule only for `repository_id`; neither its migration decision nor its verification requires original/restored MR IID and note-ID preservation or aliases. Operations says to restore MR notes/metadata but likewise does not choose an ID-preserving or alias mechanism.

**Two incompatible units:**

- **Unit A — ID-preserving importer.** Restore MRs and notes with their original identifiers, allowing direct trailer/note comparison.
- **Unit B — ordinary clean-instance importer.** Restore equivalent note bodies but GitLab assigns new note IDs. The protected tag and canonical JSON still match, while every old merge commit trailer names the original ID.

B can contain every Git object and every canonical JSON byte and still fail the normative merged linkage. Conversely, an implementation that silently ignores the new ID mismatch can falsely accept a substituted note. This was already identified as an unresolved portability issue in `_bmad-output/planning-artifacts/architecture/architecture-corp_ai_db-2026-11-06/reviews/review-adversary.md:93-103`; ADR-17 now adopts export/restore as the mode-transition mechanism without resolving it.

**Potential consequence:** all restored `merged` outcomes become unverifiable/quarantined, or a weakened reconciliation accepts forged linkage. The ADR-17 verification phrase “refs/decisions/assets closure” does not detect this unless exact original/restored note linkage is asserted.

**Required guard:** select and version either ID-preserving restore or an authenticated alias manifest containing original/restored repository IDs, MR IIDs, note IDs, note body hashes, decision IDs, and merge-commit references. Define how alias verification interacts with raw immutable commit trailers and when a missing alias is `invalid`/quarantined. Test a clean instance that deliberately assigns different MR/note IDs.

---

## ADR17-ADV-03 — HIGH: mode transition lacks a single-canonical cutover state machine

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:36,81`; `specs/corporate-kb/adr/ADR-016-repository-per-space.md:16,28`; `specs/corporate-kb/architecture-spine.md:40,52`; `specs/corporate-kb/operations.md:392-400,408-423`.

**Trigger:** ADR-17 says “versioned export/restore and new trusted binding” plus owner authorization and full reconciliation, but does not order source write freeze/deactivation, target inactive restore, binding CAS, index/AuthZ rebuild, target activation, and source retirement/rollback.

**Two incompatible units:**

- **Unit A — quiescent migration.** Suspend the source Space, freeze writes, take a consistent snapshot, restore into an inactive target, reconcile and rebuild, atomically switch the one trusted binding, then activate the target.
- **Unit B — dual-running migration.** Keep the source active for availability while restoring and activating the target, planning to “fully reconcile” later. During the transition two independently writable repositories represent the same Space.

B is not made safe by eventual reconciliation: divergent canonical histories cannot be merged back without new reviewed MR/DecisionRecord flows, and a source write after the exported HEAD is absent from the target package. It also conflicts with exactly one repository per Space and the existing restore drill's freeze/closed-user/reopen sequence.

**Potential consequence:** split-brain canonical storage, lost accepted writes, duplicate or conflicting proposals, wrong active index/grants, and rollback to a stale canonical repository.

**Required guard:** add a normative migration state machine with source `suspended/frozen`, target `restoring/unpublished`, consistent before/after HEAD and object checks, conservative `kb_ops` recovery, fresh AuthZ and full index validation, an atomic trusted-binding CAS, and target-only activation. State that source and target must never both accept writes and define rollback without reactivating a stale source. Include an in-flight merge/unknown-outcome case, not only a quiet synthetic corpus.

---

## ADR17-ADV-04 — HIGH: Shared profile conflicts with the unchanged “no shared canonical store” acceptance oracle

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:15,21-24`; `specs/corporate-kb/adr/ADR-007-client-packaging-license.md:16-17,31`; `specs/corporate-kb/spec.md:14,215,488-489`; `specs/corporate-kb/test-plan.md:352-358`; `specs/corporate-kb/integration.md:28-35`.

**Trigger:** ADR-17 declares that a shared GitLab instance is not a shared canonical store because repositories are separate. Existing integration rules make GitLab the owner of canonical documents, MRs, notes, decisions, and policies. A19 still requires “no shared canonical store,” R17 still calls for dedicated deployment, ADR-07 still rejects a single shared deployment/data plane, and the owner addendum expressly says R01–R18 and A01–A36 are unchanged.

**Two incompatible acceptance units:**

- **Unit A — Shared.** Two clients use separate private groups/repositories, credentials, and backups on one GitLab instance. It satisfies ADR-17 but physically shares the GitLab canonical metadata/data service.
- **Unit B — Dedicated.** Each client receives a separate GitLab instance, satisfying the literal A19 “no shared canonical store” and ADR-07 shared-data-plane rejection.

Both can be justified from different unchanged texts, but they produce opposite A19/GO outcomes. The issue is not merely terminology: canonical MR notes and DecisionRecords are GitLab metadata, so “repository isolation” and “no shared canonical store” are not self-evidently equivalent.

**Potential consequence:** one reviewer approves Standard/Shared while another blocks it under A19/R17; implementation and G3 evidence become non-comparable, and a physical shared canonical data plane can be passed by redefining “store” to mean only a repository.

**Required guard:** explicitly supersede or narrow the conflicting ADR-07/A19 wording. If Shared is intended, define the invariant as “no shared canonical repository/ref/history/MR/decision/grant/backup perimeter; shared GitLab service is an accepted shared trust/failure domain,” and state which A19 profile proves which isolation level. Keep the Dedicated-only security profile distinct rather than claiming physical isolation equivalence.

---

## ADR17-ADV-05 — HIGH: tenant-wide mode conflicts with per-Space mode/instance provisioning fields

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:20-25,37`; `specs/corporate-kb/repository-provisioning.md:7,32-50,54-55`.

**Trigger:** ADR-17 says the tenant profile selects one of two modes and gives each client a private group. The per-Space provisioning record independently contains `gitlab_mode` and `gitlab_instance_id`, and creation order approves the profile per Space. No invariant says every Space of a client must have the same mode/instance or defines a temporary mixed-mode migration exception.

**Two incompatible units:**

- **Unit A — client-scoped topology.** Every Space for client A is `shared` on one logical instance under one `kb-client-a` group.
- **Unit B — Space-scoped topology.** Sales is `shared`, HR is `dedicated`, using two instances and potentially two same-named client groups, because each Space registry row validly selects its own mode and instance.

B changes the meaning of “one group per client,” client-scoped credential boundaries, backup/restore perimeter, and outage scope while appearing valid in the provisioning registry. It can also be an intentional migration layout, but ADR-17 does not distinguish that temporary state from steady state.

**Potential consequence:** ambiguous tenant routing and ownership, split client credentials/backups, duplicate logical group identities, and deployments that both claim ADR-17 conformance with incompatible isolation guarantees.

**Required guard:** make mode and logical instance a client-level invariant referenced by every Space, or explicitly specify mixed-mode topology and its credential/backup/group model. If mixed mode is allowed only during migration, encode a time-bounded migration state and prohibit it as a steady-state configuration.

---

## ADR17-ADV-06 — HIGH: new IdP bindings can break stable principals and self-approval after migration

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:25,36,81`; `specs/corporate-kb/integration.md:67-68,325-330`; `specs/corporate-kb/architecture-spine.md:70,76,106`; `specs/corporate-kb/operations.md:415,418,420`.

**Trigger:** Dedicated mode uses separate IdP bindings. Stable identity is issuer-scoped OIDC `sub` (or directory-scoped objectGUID/entryUUID), while DecisionRecords and merge trailers bind human `actor_stable_id`. The migration rule defines repository mapping only; its verification omits stable identity/group alias closure. Operations requires explicit group mapping but does not define principal-ID migration.

**Two incompatible units:**

- **Unit A — identity-preserving migration.** The dedicated instance uses a new client binding to the same issuer/directory and preserves stable IDs and external group IDs.
- **Unit B — new-issuer migration.** The dedicated instance uses a new IdP issuer. The same people receive new issuer-scoped stable IDs, with an operational group mapping but no canonical principal alias.

In B, a user can approve their own pre-migration proposal because the old `author_stable_id` differs from the new approver `stable_id`; the textual self-approval comparison no longer recognizes the same human. New DecisionRecords and `Approved-by` trailers can be internally consistent while violating the business invariant. Historical authorship/grants also become disconnected.

**Potential consequence:** self-approval bypass, incorrect review queues/grants, attribution discontinuity, and failed mover/leaver/revocation behavior after an otherwise “successful” migration.

**Required guard:** require identity-preserving IdP migration or a verified versioned principal-alias protocol keyed by issuer/directory and stable subject, never email. Apply aliases consistently to self-approval, ProposalRecords, DecisionRecords, `Approved-by`, group/grant mapping, queues, revocation epochs, and export. Add a pre-migration-author/same-human-new-issuer negative test.

---

## ADR17-ADV-07 — HIGH: absolute cross-client token ban contradicts the shared platform control plane

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:27-35`; `specs/corporate-kb/operations.md:27-28,65,132-142,307-318`.

**Trigger:** ADR-17 categorically prohibits cross-client tokens, yet also requires the platform to own group/repository protections and privileged accounts across a shared instance and permits an additional instance-wide GitLab backup. A platform instance-admin/protection/backup token is intrinsically cross-client.

**Two incompatible units:**

- **Unit A — strictly partitioned credentials.** Separate platform-owned per-client group/protection credentials satisfy the token ban, but cannot perform the permitted instance-wide backup or instance-level administration as one control plane.
- **Unit B — platform control-plane credential.** A restricted instance-admin credential manages protections and instance-wide backup for every client, satisfying those platform duties but violating the unqualified cross-client-token prohibition.

The existing G0-D3 model allows privileged Owner accounts as an incident risk; ADR-17 needs to scope that exception rather than simultaneously requiring and forbidding it.

**Potential consequence:** either required platform operations cannot be implemented, or an overbroad admin token is informally treated as an exception and defeats the stated credential boundary.

**Required guard:** limit the prohibition to tenant/runtime credentials and define a separate platform control-plane credential class with exact duties, non-tenant ownership, least privilege, inventory, audit, emergency authorization, and incident/quarantine propagation. If instance-wide backup uses local/root-only tooling rather than a token, state that explicitly; otherwise define the intentional exception.

---

## ADR17-ADV-08 — HIGH: per-client identities do not prove the existing per-Space credential perimeter

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:27-31,77`; `specs/corporate-kb/adr/ADR-016-repository-per-space.md:17-22,28`; `specs/corporate-kb/contracts/gitlab-integration.md:21-28`; `specs/corporate-kb/repository-provisioning.md:16-20,57-61`.

**Trigger:** ADR-17 requires identities to be separate by client and capability, while repository=Space includes GO/agent/connector/CI credentials in the repository perimeter. Its verification tests only cross-client credential rejection.

**Two incompatible units:**

- **Unit A — client/group-scoped identities.** One GO merge identity and one CI identity per client are granted at the client group level and inherited by every Space repository. This is separate per client and capability.
- **Unit B — project/Space-scoped identities.** Credentials are separate per client, capability, and repository; a credential for Space A is rejected by Space B even within the same client.

A has a materially larger read/merge blast radius and does not demonstrate the credential part of the repository=Space perimeter. B is compatible with that perimeter, but both can pass the ADR-17 cross-client-only test.

**Potential consequence:** a Space-A service credential can read or merge Space-B repositories of the same client, bypassing the intended isolation and making token theft or adapter confusion cross-Space rather than single-Space.

**Required guard:** require authorization scope per `(client,Space/repository,capability)` even if account objects are reused for operational reasons. Prohibit inherited group-wide privileges unless the design explicitly amends ADR-16. Add same-client/cross-Space token-denial tests for proposal, merge, CI read, mirror, and export credentials.

---

## ADR17-ADV-09 — HIGH: per-client backup verification can mix Spaces and lose snapshot/restore independence

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:35,79`; `specs/corporate-kb/adr/ADR-016-repository-per-space.md:17-22,28`; `specs/corporate-kb/operations.md:373-388,392-400,408-425`.

**Trigger:** ADR-17 specifies a per-client mirror/package and checks only that no other client is included. Existing rules make mirror backup/restore part of each repository=Space perimeter, require per-Space exact snapshots, forbid an implicit mixed multi-Space snapshot, and open restored targets independently.

**Two incompatible units:**

- **Unit A — client aggregate backup.** One group-level job bundles all of a client's repositories, metadata, objects, and operational state into a client snapshot and restores them together. It is strictly per-client and excludes other clients.
- **Unit B — nested per-Space packages.** A client backup perimeter contains independently consistent per-Space mirrors/manifests/positions and supports restoring one Space without mixing or affecting another.

A can pass the literal ADR-17 verification while having inter-Space drift and no independent Space recovery. B satisfies the existing snapshot protocol; the two packages and restore tooling are not interchangeable.

**Potential consequence:** a mixed-time canonical snapshot is declared complete, one Space cannot be restored independently, or a restore of Space A overwrites/leaks Space-B state within the same client.

**Required guard:** require per-Space subpackages with exact repository/HEAD/ref/policy/object/operational positions inside the per-client outer perimeter. Verify independent and combined restores, same-client cross-Space negative controls, before/after HEAD drift, and no shared mutable backup target.

---

## ADR17-ADV-10 — HIGH: the application-lifecycle prohibition is not testable at the stated boundary

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:19,76`; `specs/corporate-kb/architecture.md:371-379`; `specs/corporate-kb/operations.md:57`.

**Trigger:** The decision covers update/rollback/uninstall and any coupling to GitLab's release lifecycle. Verification checks only that application-namespace manifests contain no GitLab workloads/PVC and that a synthetic uninstall/rollback leaves data unchanged. “Application deployment” is not defined as a child chart, umbrella release, GitOps application, operator, or external pipeline, and update plus API-driven deletion are omitted.

**Two incompatible units:**

- **Unit A — independent platform release.** GitLab has a separately owned release and backup lifecycle; the application release contains no GitLab resources or lifecycle hooks.
- **Unit B — umbrella-coupled release.** The child application chart contains no GitLab resources and passes the stated manifest test, but a parent Helm/GitOps release owns GitLab in another namespace and prunes it on application uninstall. Alternatively, a non-GitLab post-delete Job calls the GitLab API to delete the client group.

B violates the architectural intent yet can pass the narrow child-manifest/uninstall test if the parent or API path is outside the tested harness. Concurrent legitimate GitLab writes can also make “storage unchanged” fail without any lifecycle coupling unless the test freezes and hashes a defined evidence set.

**Potential consequence:** canonical repositories, metadata, tags, or storage are deleted during an application release operation despite a recorded verification PASS.

**Required guard:** define the release/ownership boundary and forbid parent-owner references, cascade/finalizer coupling, lifecycle hooks, and release-driven GitLab API mutations. Test install, upgrade, rollback, and uninstall for child and umbrella/GitOps/operator paths, with GitLab audit evidence and before/after hashes of all refs, MR metadata, protected tags, and storage inventory under a controlled write freeze.

---

## ADR17-ADV-11 — MEDIUM: ADR-17 backup verification is weaker than the mandatory platform-backup content

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:35,79`; `specs/corporate-kb/spec.md:498-500,688`; `specs/corporate-kb/operations.md:373-390,408-425`.

**Trigger:** The ADR-17 checklist names mirrors, MR notes/metadata, manifests, objects, configuration, and required `kb_ops` backups. Its verification can pass without explicitly proving GitLab audit metadata, the separate secrets recovery policy, Open WebUI users/sessions/chats/models procedures, and the correction-task current/events/evidence/idempotency restore with linked-MR reconciliation. Existing spec/operations require those controls and distinguish a Space export from a full platform backup.

**Two incompatible units:**

- **Unit A — ADR-checklist-only backup.** Restores Git knowledge and generic required `kb_ops` data with no other client, satisfying the literal ADR-17 bullet.
- **Unit B — operations-complete backup.** Additionally proves audit metadata, separate encrypted secrets recovery, upstream state scope, and the dedicated correction-task backup/reconciliation protocol.

A and B both can be called a clean per-client restore if only ADR-17 verification is used, but A does not meet the existing T18/G3 operational restore requirement.

**Potential consequence:** false restore confidence, loss of operational correction state or audit evidence, inability to recover credentials/upstream service state, and an ADR-17 PASS that contradicts operations G3.

**Required guard:** classify Space export, knowledge backup, and full platform backup separately and enumerate which procedure owns each component. Extend ADR-17 verification with the existing audit/secrets/upstream/correction controls and their negative cases; do not put plaintext secrets into export to satisfy the check.

---

## ADR17-ADV-12 — MEDIUM: new Shared and migration rehearsals have no explicit acceptance/task owner

**Location:** `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:70-82`; `specs/corporate-kb/spec.md:14,684-692,734`; `specs/corporate-kb/test-plan.md:352-359`; `specs/corporate-kb/traceability.md:79,83,193-202`; `specs/corporate-kb/operations.md:556-563`.

**Trigger:** ADR-17 requires shared two-client isolation, dedicated config-only deployment, and shared→dedicated migration rehearsals. The addendum leaves A01–A36 unchanged. A19's detailed test remains dedicated delivery with no shared canonical store, G3 says second dedicated instance, and T18a/T18b traceability contains no explicit Shared two-client or bidirectional migration scenario.

**Two incompatible delivery units:**

- **Unit A — existing acceptance only.** Implements A19 as the documented second dedicated client and A15 as a normal clean restore, claiming T18/G3 without ever running two clients on one GitLab instance or changing modes.
- **Unit B — ADR-17 verification.** Additionally runs shared two-client isolation and shared→dedicated migration with repository mapping and conservative recovery.

B performs materially new work that has no clear normative acceptance/task mapping, while A can point to existing traceability and omit it. The documents therefore do not make the new ADR-17 verification unavoidable.

**Potential consequence:** the highest-risk new topology and migration behavior is skipped despite an accepted ADR, or evidence is attached inconsistently to A15/A19/T18 without comparable gates.

**Required guard:** explicitly map shared two-client isolation and both migration directions to existing A15/A19/T18a/T18b with updated steps, or introduce owner-approved acceptance IDs and dependencies. Update test-plan, operations G3, and traceability together; retain BLOCKED status until real evidence exists.

---

## Checked boundary: client Group Owner restriction itself

No independent contradiction is asserted merely because ADR-17 denies client Group Owner/instance-admin privileges in managed Shared mode. The existing engineering model still works if client engineers use non-Maintainer GitLab identities for engineering MR/review, only GO is Maintainer, final apply is GO-only, and platform-owned privileged accounts retain the G0-D3 out-of-band incident path (`specs/corporate-kb/spec.md:247-251`; `specs/corporate-kb/baseline.md:213-224`; `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:33,78`). The defect is the unscoped platform control-plane credential contradiction in ADR17-ADV-07, not the Developer-level engineering workflow itself.

## Review limit

This was a document-only adversarial review. No synthetic deployment, two-client isolation, migration, restore, or lifecycle test was run, and no runtime result is promoted to PASS. Production and unavailable integration checks remain BLOCKED under `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:82`.
