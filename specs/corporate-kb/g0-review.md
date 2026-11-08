# G0 owner review — baseline and design decisions

Status: **APPROVED — G0 passed**  
Review date: 2026-11-08  
Approver: Anton Smychkin, project owner  
Inputs: `baseline.md`, `architecture-spine.md`, `repository-provisioning.md`, `delivery-estimates.md`, `evidence/t00/capability-matrix.md`, `evidence/t00/openwebui-oidc-runtime.md`, `evidence/t00/ldap-capabilities.md`, `evidence/t00/independent-review.md`, ADR-003–ADR-016.

No item below is approved unless explicitly marked APPROVED. A technical PASS is not owner approval.

## Decision record

| ID | Decision | Owner decision and conditions | Status |
|---|---|---|---|
| G0-D1 | Open WebUI `v0.13.0` / commit `c38885a1a737da4968f157092f304f3b5481d0bf` as baseline | Accept with mandatory identity/execution/migration adapters and documented upstream risks. | **APPROVED** |
| G0-D2 | GitLab CE `19.5.3` role-based profile | Accept: no direct push, Maintainer-only merge, only GO Maintainer, protected decision tags, CE role semantics rather than per-user grants. | **APPROVED** |
| G0-D3 | Privileged GitLab admin/Owner bypass risk | Restrict privileged accounts, enable audit and out-of-band reconciliation, maintain an explicit break-glass runbook. Do not claim absolute merge-only-GO for admins. | **APPROVED** |
| G0-D4 | Identity adapter is mandatory | Accept: stock LDAP/OIDC JIT alone is insufficient; issuer+sub/entryUUID and ownership-aware snapshots are required. | **APPROVED** |
| G0-D5 | Deny-by-default execution adapter | Accept: stock arbitrary Python/tool approval is not a security boundary. | **APPROVED** |
| G0-D6 | External migration owner | Accept: runtime migrations disabled; one migrator role owns DDL and verifies head before traffic. | **APPROVED** |
| G0-D7 | PostgreSQL 18.6 + pgvector 0.8.7 as retrieval baseline candidate | Accept candidate; production model, quality thresholds and SLO remain separate owner decisions. | **APPROVED** |
| G0-D8 | Editor direction | **TipTap adapter**: preserve WYSIWYG editing; add canonical serializer, front-matter boundary, immutable attachment metadata, full source diff and browser/IME/accessibility/XSS gates. Realtime collaborative editing/CRDT remains out of MVP. Concurrent authors receive conflict detection, exact/fresh revisions, full difference review and a new ProposalVersion instead of shared realtime state or automatic conflict merge. | **APPROVED** |
| G0-D9 | Frontend toolchain risks | Accept Vitest and direct 6 GiB Vite build for T01; svelte-check, ESLint and build-script debt is tracked explicitly and not called healthy. | **APPROVED** |
| G0-D10 | License/branding posture | Preserve Open WebUI branding. No white-label or commercial distribution until owner/legal clearance. Internal exception/enterprise options are not presumed. | **APPROVED** |
| G0-D11 | Hoster.ai endpoints/model IDs and production quality thresholds deferral | Defer to T11 with T11 BLOCKED until real inputs and thresholds exist. | **APPROVED** |
| G0-D12 | Approve architecture/design package for epic planning | Approved by owner on 2026-11-08 after baseline/evidence review; deferred gates remain mandatory. | **APPROVED** |
| G0-D13 | Repository-per-Space provisioning proposal | Approve `repository-provisioning.md`; actual namespaces, corpus mapping and production cutover schedule remain owner inputs. | **APPROVED** |
| G0-D14 | Identity transport profile | **LDAP is required in MVP.** OpenLDAP/LDAPS/StartTLS runtime checks are complete (8/8). Production AD and live subscription/SLO checks remain follow-up work. | **APPROVED** |
| G0-D15 | Browser editor validation deferral | Browser/IME/accessibility/XSS/full managed preview is deferred to the explicit T04 gate after the TipTap adapter exists. No editor/UI PASS is claimed. | **APPROVED** |
| G0-D16 | Object-store ACL runtime deferral | Immutable version probes passed 5/6; cross-bucket ACL failed in LocalStack and is untested on the production engine. Recheck in T13/T16; no ACL/export/restore PASS is claimed. | **APPROVED** |
| G0-D17 | Estimation assumptions | Accept `delivery-estimates.md` only as LOW/VERY LOW confidence scenarios; real team capacity is confirmed during sprint planning. | **APPROVED** |

## Editor options

### Option A — TipTap adapter

Keep WYSIWYG editing; add canonical serializer, front-matter boundary, immutable attachment metadata, full source diff and browser/IME/accessibility/XSS gates. Realtime collaborative editing/CRDT remains out of MVP. Concurrent authors receive conflict detection, exact/fresh revisions, full difference review and a new ProposalVersion instead of shared realtime state or automatic conflict merge.

- Pro: best fit for existing UX and upstream Notes seams.
- Con: largest adapter scope; current headless fidelity fails without adapter.

### Option B — CodeMirror canonical source

Use CodeMirror raw Markdown, existing preview and full diff; no WYSIWYG editing in the first slice. Realtime collaborative editing/CRDT is outside MVP for every option.

- Pro: strongest byte/front-matter fidelity; raw round-trip and full diff passed, but headless preview failed for Cyrillic links.
- Con: relaxes the expected WYSIWYG UX and requires owner acceptance.

### Option C — Hybrid

CodeMirror remains canonical editor; TipTap or preview is derived and read-only or tightly scoped.

- Pro: avoids canonical ambiguity.
- Con: highest UI complexity and must still prove accessibility/UX.

Owner selected **Option A — TipTap adapter** at G0-D8. The WYSIWYG-without-realtime-CRDT wording above is the owner-approved clarification of the same decision, preserving the original approver/date and recorded in the [approved Sprint Change Proposal](../../_bmad-output/planning-artifacts/sprint-change-proposal-2026-11-08.md) §4.6; it does not reopen G0 or add collaborative editing to MVP.

## Required approval evidence

For every APPROVED item the record includes approver, date, decision, conditions, evidence links and follow-up tasks.

For every REJECTED/DEFERRED item record the reason and unblock condition.

## Current blocking conclusion

T00 evidence collection and owner review are complete for the selected baseline, including real GitLab, CI Runner, OpenLDAP/OIDC, PostgreSQL role/recovery, Notes/chats and partial object-store checks. Deferred gates remain mandatory and are not claimed as PASS.

**T00 DONE. G0 APPROVED.** Epic planning may start. Product implementation must follow task dependencies and the approved editor, identity, migration, recovery and packaging controls.
