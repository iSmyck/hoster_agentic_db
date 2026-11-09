# Final focused adversarial re-review — ADR-17

Date: 2026-11-09  
Scope: only ADR17-FINAL-01 through ADR17-FINAL-04 from `review-adversarial-adr17-final.md`. No unrelated historical debt or new review area was introduced. This was a static artifact review; no runtime operation was executed.

## Verdict

**PASS — NO FINDINGS.**

All four remaining contradictions/under-specified boundaries are resolved in the current artifacts. No actionable finding remains within the requested scope.

## Disposition and evidence

| Previous finding | Disposition | Current evidence |
|---|---|---|
| **ADR17-FINAL-01 — tenant-wide mode vs per-Space overrides** | **Resolved.** Mode, logical instance, endpoint and client group are client-level invariants; mixed-mode is prohibited; per-Space copies are inherited read-only bindings; mixed-mode fixtures must be rejected. | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:43,84`; `specs/corporate-kb/repository-provisioning.md:34-40,54`; `specs/corporate-kb/spec.md:489`; `specs/corporate-kb/architecture.md:373`; `specs/corporate-kb/architecture-spine.md:136`; `_bmad-output/planning-artifacts/architecture/architecture-corp_ai_db-2026-11-06/ARCHITECTURE-SPINE.md:136` |
| **ADR17-FINAL-02 — cross-client-token ban vs platform control plane** | **Resolved.** The managed-workload prohibition now has an explicit, restricted platform instance-admin/DR exception outside client namespaces. These identities are inventoried/audited, are not client/GO identities, cannot perform normal managed read/propose/merge/export, and do not create client-facing restore units. | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:35,38,84`; `specs/corporate-kb/operations.md:134`; `specs/corporate-kb/architecture-spine.md:136`; `_bmad-output/planning-artifacts/architecture/architecture-corp_ai_db-2026-11-06/ARCHITECTURE-SPINE.md:136` |
| **ADR17-FINAL-03 — per-client identities vs per-Space credential perimeter** | **Resolved.** Every managed credential is explicitly scoped by `(tenant_id,space_id,repository_id,capability)`; group membership alone is insufficient; provisioning binds each capability to its Space repository; ADR-17 and A19 require same-client wrong-Space denial as well as cross-client denial. | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:34,84`; `specs/corporate-kb/repository-provisioning.md:57-61`; `specs/corporate-kb/operations.md:57,65`; `specs/corporate-kb/spec.md:489`; `specs/corporate-kb/test-plan.md:357` |
| **ADR17-FINAL-04 — per-client package vs independent per-Space backup/restore** | **Resolved.** The client perimeter is now explicitly an outer perimeter containing independently restorable per-Space packages with separate snapshot closure. Client-level `kb_ops` backups require explicit Space mapping and cannot merge Space closures; verification requires independent clean restore without another Space or client. Shared-backup wording is limited to client backup packages and does not prohibit the separately restricted platform DR artifact. | `specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md:41,86`; `specs/corporate-kb/repository-provisioning.md:7`; `specs/corporate-kb/operations.md:57,395-400,423`; `specs/corporate-kb/spec.md:489`; `specs/corporate-kb/test-plan.md:357`; `specs/corporate-kb/architecture-spine.md:136`; `_bmad-output/planning-artifacts/architecture/architecture-corp_ai_db-2026-11-06/ARCHITECTURE-SPINE.md:136` |

## Conclusion

The previous incompatible deployment, credential, and backup constructions no longer satisfy the current written rules. Existing-Space profile migration remains explicitly deferred and was not reopened; real deployment/restore/lifecycle evidence statuses were not changed by this document review.
