# Epic 2 Context: Managed documents & access

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Epic 2 establishes the foundational document model and access perimeter for the corporate knowledge base. It delivers a Git-backed document tree with stable opaque IDs, canonical whole/section direct reads by exact revision SHA, and a per-Space identity and authorization layer that feeds all later UI, agent, and tool operations. Completing this epic makes Spaces navigable and readable with a trusted, stable identity context, while drafting, review, merge, indexing, and migration remain the responsibility of downstream epics.

**Planning artifact gaps:** no separate PRD, product brief, or UX/design contract was found in the planning artifacts directory. Requirements and UX patterns were extracted from `epics.md` and the architecture spine; the implementation-readiness gate previously flagged forward-dependency claims in E02.1, and the current epic text already narrows E02.1 to the R01–R03 document/read scope.

## Stories

- Story 2.1 (T02): Git-backed document tree and canonical direct read
- Story 2.2 (T03a): Stable identity core and nested group snapshots
- Story 2.3 (T03b): Per-Space policy enforcement and revocation

## Requirements & Constraints

This epic covers the read-side document model and the identity/authorization prerequisites for everything that follows:

- Unified catalog/document/agent interface, stable document model with opaque UUIDs, stable links by ID, versioned attachments, and WYSIWYG preservation.
- Canonical direct read of whole documents or sections with explicit bounds, cursor, truncation flag, and exact revision SHA; no silent text loss.
- Shared stable identity and unified Space ACL across UI, API, tools, files, history, export, and search.
- Pending, rejected, and preflight content must stay out of the published search corpus.
- One repository equals one Space: a single ACL/history/export perimeter; `access` in front matter does not create ACL.
- Rebuildable projections and single-writer schemas: authorization is enforced before any title, snippet, chunk, file, or history payload is exposed.
- Explicit user-visible states: `draft`, `in_review`, `published`, `indexed`, `archived`, `conflicted`; `recovery_required`, quarantine, and inactive preflight must not be masked as published/indexed.
- Versioned attachments share the Space ACL and must be referenced by immutable `{object_id, version, sha256, size, media_type, source_ref}` tuples, never by mutable current URLs.

E02.1 is intentionally limited to R01–R03 direct-read/document-model scope; full R05/A04 enforcement is split into E02.2 and E02.3.

## Technical Decisions

- **Git-native canonical storage.** Markdown + closed front matter in GitLab is the canonical document; full commit SHA is the revision. MRs represent proposals; canonical DecisionRecords live in structured MR notes and protected annotated tags.
- **One repository = one Space.** A Space is the single unit of ACL, blobs, history, protected branch, credentials, cutover, index, and export perimeter.
- **Stable identity.** `stable_id` is AD `objectGUID`, OpenLDAP `entryUUID`, or OIDC `sub`; email/login are not identity keys. Nested group membership is resolved completely into epoch-matched snapshots.
- **Per-Space authorization.** `AuthzContext-v2` carries an independent repository binding, policy bundle, access/approval revision SHAs, group snapshot, and revocation epoch for each Space. No shared top-level policy or group binding is allowed.
- **Path-scoped policy.** Policy path matching uses longest-normalized-prefix selection; parent-prefix groups are not unioned. Mapping between absolute and relative policy paths is lossless (`/` ↔ empty prefix, `/pricing` ↔ `pricing`); `..`, ambiguous separators, backslashes, and absolute document paths are rejected.
- **Document identity.** `document_id` is an opaque UUID independent of path; body and front-matter links form a single stable-ID graph. Duplicate IDs, cycles, orphans, swapped targets, and ambiguous links are validation errors that block publication/indexing.
- **Direct read semantics.** Whole-document or section reads return the exact revision SHA, path/heading context, section anchors with occurrence counts for repeated headings, bounds, cursor, and an explicit `truncated` flag.
- **Attachment model.** Every attachment revision is immutable and carries the full tuple `{object_id, version, sha256, size, media_type, source_ref}` under the same Space ACL.
- **Error contract.** Errors use `{code, message, request_id, retryable}` with sanitized details. Anti-enumeration applies `NOT_FOUND` where a denial would reveal the existence of a protected object.
- **Revocation.** Group refresh ≤ 15 minutes, revocation SLO ≤ 30 minutes; provider/IdP outage fails closed rather than extending cached allow indefinitely.

## UX & Interaction Patterns

- **Unified managed experience.** Business readers, authors, and approvers move through catalog → document → editing → agent → diff → decision → merge without Git/CLI or a second business application.
- **Feature-flag isolation.** Managed KB is enabled by feature flag; existing personal Notes and ordinary chats stay unchanged and are not silently converted to managed group grants.
- **Tree and read UI.** Russian UI labels, stable deep links, breadcrumbs, explicit truncation reasons and continuation cursors, and clear distinction between `draft`, `in_review`, `published`, `indexed`, `archived`, and `conflicted` states.
- **Policy-aware UX.** Per-Space policy bundles, group-assigned review queues, mover/leaver handling, and revocation-aware state transitions are visible consistently across UI, API, tools, and deferred operations.

## Cross-Story Dependencies

- E02.1 depends on the E01.1 contract harness and two-Space fixtures.
- E02.2 depends on E02.1's canonical document/read model.
- E02.3 depends on E02.2's stable identity/group snapshots and on E02.1's canonical reads.
- E02 is a prerequisite for E03 (Save & history) and E04 (Governed agent workflow). E05 (Published knowledge pipeline) starts after E02/E03.
