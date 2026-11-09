# Architecture reviewer-gate rubric walk — AD-17 / ADR-17

**Review date:** 2026-11-09  
**Mode:** read-only document review; no deployment, integration, restore, upgrade, or migration test was executed.  
**Scope:** AD-17 and its directly related deployment/provisioning/traceability changes only. Historical debt is excluded.

## Verdict

**CHANGES REQUIRED — 1 HIGH, 2 MEDIUM, 1 LOW.**

AD-17 fixes a real divergence point: it separates canonical GitLab data lifecycle from the client application namespace/release lifecycle, permits a hardened shared instance for Standard, and requires a separate same-baseline, configuration-only GitLab instance for Isolated/Dedicated. The decision is mostly concrete and preserves the repository=Space, GO-only managed merge, business-identity, and per-client credential boundaries.

The gate is nevertheless blocked by a direct contradiction about shared backups: the ADR prohibits a common backup perimeter and cross-client mixed backups, then permits an instance-wide GitLab backup containing all shared-instance clients. Shared-platform upgrade coordination and bidirectional migration proof also need completion. These are design/enforceability findings, not claims that production checks have failed or already passed.

## Reviewed sources

- `specs/corporate-kb/architecture-spine.md`, especially AD-1–AD-17 at lines 36–136.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md` at lines 1–90.
- `specs/corporate-kb/spec.md` §§4, 5, 9 and the ADR-17 owner addendum.
- `specs/corporate-kb/architecture.md` §§9 and 12.
- `specs/corporate-kb/operations.md` §2, plus the directly referenced startup/backup/restore/upgrade controls needed to assess the new operational envelope.
- `specs/corporate-kb/repository-provisioning.md`.
- `specs/corporate-kb/traceability.md`.

## Findings

### F-01 — HIGH — The instance-wide backup exception violates the accepted no-shared-backup perimeter

**References:**

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:15` — a shared instance must not become a common backup perimeter.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:35` — cross-client mixed backups are forbidden, but an instance-wide GitLab backup is then allowed as an additional platform backup.
- `specs/corporate-kb/spec.md:488` — no common backup perimeter between clients.
- `specs/corporate-kb/architecture-spine.md:100` — AD-11 requires independent client backups.
- `specs/corporate-kb/architecture-spine.md:135-136` — AD-17 says it prevents cross-client backups and that Shared does not use common backups.
- `specs/corporate-kb/operations.md:57` — repeats the additional instance-wide-backup exception.

**Problem:** An instance-wide GitLab backup is physically and administratively a cross-client backup: it can contain every client's repositories, MR metadata, audit data, and related instance state. Calling it an additional platform backup does not move it outside the shared backup/data perimeter, and no separate encryption, access, retention, or tenant-independent disposal boundary is defined for it.

**Consequence:** The accepted documents simultaneously prohibit and authorize the same mixed-client backup. This weakens per-client isolation and retention/restore reasoning and makes AD-17 non-enforceable as written: a deployment with a mixed instance-wide backup could claim ADR-17 compliance while violating AD-11, R17, and spec §9.

**Required correction:** Remove/forbid the mixed instance-wide-backup exception under the accepted invariant, or explicitly reopen that invariant and obtain an owner-approved amendment defining the platform-backup exception and its isolation, access, encryption, retention, and prohibition on per-client restore. Do not silently treat “additional platform backup” as compatible with “no common backup perimeter.”

### F-02 — MEDIUM — Shared GitLab upgrade/rollback coordination across independent client releases is not defined or verified

**References:**

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:19` — GitLab is outside each application release lifecycle.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:25` — dedicated uses the same pinned baseline/template.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:34` — Shared is explicitly a common trust/failure domain.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:71` — restore/upgrade evidence is required before production.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:76-82` — the verification list has no shared-platform upgrade/rollback scenario.
- `specs/corporate-kb/operations.md:462-468` — the generic upgrade rehearsal uses a synthetic client configuration and does not enumerate all tenants affected by a shared GitLab upgrade.

**Problem:** A shared GitLab upgrade is a platform event spanning multiple independently released client applications. The new decision does not define the affected-tenant inventory, client/GO/GitLab compatibility check, all-tenant write freeze, staged per-client reconciliation/reactivation, or rollback/data-compatibility rule. The existing generic single-client upgrade controls do not prove those shared-mode behaviors.

**Consequence:** An operator could apply an otherwise valid single-client upgrade runbook to the shared instance and interrupt or expose every tenant while client applications remain on independent release schedules. “Same pinned baseline” alone does not define a safe upgrade transition.

**Required correction:** Add a shared-platform upgrade/rollback control and a two-client rehearsal covering affected-tenant discovery, version compatibility, coordinated freeze, backup/restore readiness, staged per-client reconciliation and reopen, and rollback behavior. Keep real execution BLOCKED until measured evidence exists.

### F-03 — MEDIUM — The migration decision is bidirectional, but its verification and canonical-authority handoff are incomplete

**References:**

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:36` — transition between `shared` and `dedicated` uses export/restore, a new trusted binding, and full reconciliation.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:81` — only `shared → dedicated` is verified.
- `specs/corporate-kb/operations.md:410-422` — generic restore includes freeze and staged reopen, but does not explicitly define retirement/noncanonical status of the old mode-specific repository binding.

**Problem:** `dedicated → shared` has no explicit verification row. In addition, ADR-17 does not explicitly bind the migration to one authoritative cutover sequence: source write freeze before the exact export snapshot, one active trusted binding, old-source deactivation/noncanonical designation, and only then target reopen. Generic conservative restore controls are necessary but do not by themselves prove that two mode-specific repositories cannot remain independently writable.

**Consequence:** The reverse migration can be declared covered without being tested, and an incomplete handoff can leave old and restored repositories with ambiguous canonical authority, contrary to AD-1's single-canonical-copy objective.

**Required correction:** Define and verify both migration directions. Require an exact source snapshot under write freeze, explicit repository mapping, refs/decisions/assets/policies closure, conservative recovery, one active trusted binding, old-source deactivation/noncanonical status before target activation, and no copied plaintext secrets. Production migration remains separately owner-authorized and BLOCKED until real evidence exists.

### F-04 — LOW — Application-lifecycle verification omits install/upgrade/recreate paths named by the decision

**References:**

- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:19` — prohibits application update/rollback/uninstall from installing or deleting GitLab resources.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:55` — positive consequence also covers application recreate.
- `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:76` — verification covers only uninstall/rollback plus static absence of GitLab workloads/PVC.
- `specs/corporate-kb/operations.md:57` — explicitly names install/upgrade/rollback/uninstall.

**Problem:** The verification set does not exercise install, upgrade, or namespace/application recreate. Static manifest inspection alone also does not detect a release hook/job that mutates external GitLab through its API.

**Consequence:** A later application release could reintroduce lifecycle coupling through an upgrade hook or external API mutation while the listed ADR-17 verification still passes.

**Required correction:** Exercise install, upgrade, rollback, uninstall, and application/namespace recreate against synthetic GitLab state. Assert unchanged repositories, MR metadata, protected tags, storage, credentials, and backup bindings, and reject release hooks/jobs that manage GitLab resources or mutate canonical state outside the approved GO path.

## Rubric walk

| Criterion | Result | Assessment |
|---|---|---|
| Fixes a real divergence point | **PASS** | ADR-17 lines 11–15 identify the data/release-lifecycle coupling and the different Standard versus Isolated/Dedicated isolation needs. The rejected alternatives at lines 44–49 address the relevant topology choices rather than restating old decisions. |
| Clear owner decision and scope | **PASS** | `architecture-spine.md:132-136` gives AD-17 concrete Binds/Prevents/Rule content. ADR-17 lines 19–38 map Standard to `shared` and Isolated/Dedicated to `dedicated`, require the same pinned baseline/template, separate dedicated resources, and forbid client code branches. |
| Enforceable controls | **FAIL** | Manifest restrictions, tenant fields, credential matrix, negative tests, and restore checks are useful controls, but F-01 makes the backup perimeter internally contradictory. F-02/F-03 leave required lifecycle paths without complete guards. |
| Prevents the stated problems | **PARTIAL** | Externalizing GitLab workloads/PVC and separating client credentials/repositories addresses application deletion coupling and incompatible client forks. The mixed-backup exception reintroduces a cross-client data/backup perimeter, and shared upgrade coordination remains unspecified. |
| Preserves AD-1–AD-16 | **PARTIAL** | Repository=Space, MR/GO-only managed merge, DecisionRecord refs, business users without GitLab accounts, dedicated PostgreSQL/index/objects, and rebuildable projections remain intact. F-01 conflicts with AD-11; F-03 must be closed to make AD-1 single-canon preservation explicit during profile migration. No other new AD regression was found in scope. |
| Preserves R01–R18 / I01–I14 | **PARTIAL** | R05/R06 identity and merge boundaries, R14 portability, R17 config-only repeatability, R18 evidence, and I02/I04/I09/I10 are generally retained. F-01 directly conflicts with the independent-backup language in R17/spec §9. No requirement IDs or acceptance IDs were silently renumbered. |
| REQUIREMENT / DESIGN / UNKNOWN / BLOCKED discipline | **PASS** | The accepted owner topology is normative; concrete production resources remain deployment/owner choices. ADR-17 lines 38 and 82, `spec.md:14`, `architecture.md:478`, and `operations.md:15-22,41` correctly avoid converting local synthetic evidence into production PASS. |
| Operational envelope | **PARTIAL** | Provisioning, credential separation, privileged governance, backup/restore, outage handling, capacity monitoring, and owner authorization are represented. F-01–F-04 leave backup consistency, shared upgrade/rollback, reverse migration/canonical handoff, and full application-lifecycle verification incomplete. |
| Repository provisioning | **PASS with F-03 follow-up** | `repository-provisioning.md:7,34-50,54-68` carries `gitlab_mode`, trusted logical instance binding, repository=Space, service roles, protection/cutover order, and backup registration without creating production resources. Profile migration needs the stronger authority handoff described above. |
| Traceability | **PASS** | `traceability.md:23-36,45-53` links ADR-17 to applicable R/I rows; R05/R14/R17/R18 carry AD-17. `traceability.md:83,165,201-202` retains A19 and T18/T18a/T18b ownership, and lines 250/254 preserve DESIGN/BLOCKED evidence discipline. No new normative acceptance assignment is fabricated. |
| No production-evidence overclaim | **PASS** | ADR-17 line 38 limits T00 evidence and line 82 marks real shared/dedicated deployment, chart/HA, and restore drills BLOCKED. This review makes no production readiness claim. |

## Preserved decisions explicitly checked

- **Canonical storage and repository=Space:** ADR-17 lines 15 and 24 retain one repository per Space and prohibit shared canonical history across clients.
- **GO/business approval boundary:** ADR-17 lines 27–33 retain separate proposal/merge identities, only the corresponding client's GO merge identity with normal managed merge permission, no business GitLab users, and G0-D3 privileged-incident handling.
- **Dedicated repeatability:** ADR-17 line 25 requires the same pinned version/edition and versioned configuration template, separate instance/endpoints/IdP bindings/secrets/tokens/storage/network/backups/restore environment, and no client code branch.
- **Trusted tenant context:** ADR-17 line 37 and `repository-provisioning.md:39-41` prevent browser/agent selection of tenant, instance, or Space authority.
- **Portability/rebuild evidence:** mirrors, MR metadata, decisions/assets/policies/grants, immutable objects, configuration, and durable operational state remain in the stated per-client package; projections remain rebuildable under the existing recovery controls.
- **Historical approval boundary:** `spec.md:14`, `architecture.md:460,478`, and `traceability.md:250` keep ADR-17 owner approval separate from the historical G0 record.

## Residual verification gaps after design correction

These remain verification work, not evidence of production capability:

1. Real hardened shared GitLab with two synthetic clients, including credential rejection and GitLab-level cross-client authorization tests.
2. Real dedicated config-only deployment from the pinned baseline/template with separate endpoints, secrets, storage, network, backups, and restore environment.
3. Production chart/deployment and HA evaluation; neither is established by local T00 runtime evidence.
4. Clean isolated per-client restore in both profiles, including negative controls and no other-client content.
5. Shared-platform two-client upgrade/rollback rehearsal and both profile-migration directions once F-02/F-03 are resolved.
6. Owner-approved RPO/RTO, retention, capacity, budget, maintenance-window, and incident-escalation thresholds. Until then they remain OWNER_TBD/UNKNOWN as applicable, not PASS criteria.

No production instance, corpus, secret, migration, destructive action, external egress, or paid call is authorized by this review.
