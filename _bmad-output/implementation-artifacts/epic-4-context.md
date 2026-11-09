# Epic 4 Context: Governed agent workflow

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Deliver the governed proposal → review → decision → merge pipeline. Every managed change flows through an exact-SHA `ProposalVersion`, a canonical human `DecisionRecord`, and a GO-controlled merge. Agents are restricted to read/search/single-page propose; races, crashes, and bypass attempts are recovered or quarantined.

**Planning gaps:** no standalone PRD or UX contract exists; requirements are extracted from `epics.md`, ADRs, and component contracts. The project-wide `implementation-readiness.md` gate is currently **FAIL** for traceability/dependency reasons that overlap this epic.

## Stories

- Story 4.1 (T05a): Exact ProposalRecord and ProposalVersion lifecycle
- Story 4.2 (T05b): Canonical DecisionRecord, exact merge and conclusive recovery
- Story 4.3 (T06): Merge-only-GO enforcement, fencing and quarantine
- Story 4.4 (T07): Exact business review and independent decisions
- Story 4.5 (T08): Scoped working context and canonical direct-read agent tools
- Story 4.6 (T09): Restricted single-page agent proposal tools
- Story 4.7 (T07b): DocOps review projections, correction tasks and UX telemetry

## Requirements & Constraints

This epic owns R06, R07, R08, R09, R10, and R16:

- **Exact proposals.** Every proposal is an MR with exact `base_sha`/`proposal_sha`, precise diff, rationale/evidence, and an append-only `ProposalRecord`. A new commit or rebase creates a new `ProposalVersion` and invalidates prior approval.
- **Canonical decisions.** Accept/reject/cancel produce one `DecisionRecord` JSON with `record_sha256` written identically to a structured MR note and protected annotated tag `kb-decisions/<decision_id>` on the exact `proposal_sha`.
- **Independent approval.** Author, requester, and version-author cannot self-approve; fresh group/path role and matching policy revisions are mandatory.
- **GO merge.** Applies exact SHAs with no squash, rebase, fast-forward, or LLM regeneration; merge commit carries Decision trailers.
- **Per-target serialization.** `HEAD == base_sha` is rechecked immediately before the external merge call; at most one verified apply succeeds per target, losers get `STALE_BASE`/conflict with zero `main` writes.
- **Conclusive recovery.** `merge_attempted` and durable per-target `recovery_required` are persisted before the first merge attempt; Git ancestry/notes/tags/trailers determine outcome. Timeout alone is never `merged` or `failed`; only conclusive `failed` allows a guarded same-decision retry.
- **Merge-only-GO.** Only the GO merge service identity can merge after a canonical decision. Direct push/direct merge/auto-merge are denied for all non-privileged identities; a privileged GitLab Owner bypass is an integrity incident with reconciliation/quarantine.
- **Deny-by-default execution.** Across all channels, accept/reject/cancel/merge/grants, arbitrary Git, shell/SQL/filesystem, and Tool Creation are rejected even for admin chat users.
- **Restricted agent tools.** Agents may only read/search and propose a curated single-page body create or `AgentAnchoredPatchChange` with a required body section. Bulk/subtree/attachments/front-matter/whole-document replacement/approval/merge are forbidden.
- **Business review.** Shows exact `base_sha`/`proposal_sha`, affected files, full diff, machine-significant changes (front matter, links, archive, attachments), rationale/evidence, and author/version-author/requester/run attribution.
- **Scoped agent context.** Page/subtree/Space scope carries stable page ID plus exact SHA and explicit bounds; direct reads go through GO at exact revision.
- **DocOps.** `valid_until` drives revision-bound projections; "нашёл ошибку" creates a GO-owned `docops-correction-task-v1` with `open/in_review/resolved/cancelled` lifecycle, exact `document_revision_sha`, evidence hash, and optional linked MR.
- **Lifecycle clarity.** UI distinguishes `draft`, `in_review`, `published`, `indexed`, `archived`, `conflicted`, `recovery_required`, and quarantine.
- **Errors.** Unified `{code, message, request_id, retryable}` shape with sanitized details and anti-enumeration `NOT_FOUND`.

## Technical Decisions

- **Git-native canonical.** MRs are proposals; protected annotated tags and MR notes are canonical DecisionRecords; merge commits are durable publications.
- **GO owns canonical writes.** The Git Orchestrator monolith coordinates merge, owns `kb_ops`, and is the only managed identity with merge permission.
- **Append-only records.** `ProposalRecord` and `DecisionRecord` are append-only and hash-bound; `Idempotency-Key == decision_id`.
- **Full SHA semantics.** Complete lowercase Git SHAs; ordering by ancestry, never lexicographic.
- **Credential separation.** Proposal/read, merge, connector, and CI identities are separated; merge credential is unreachable from UI/browser/agent/connector/CI.
- **Fencing.** A per-target lock/fencing token serializes the merge critical section; the lock is never held during review or inference.
- **Recovery barrier.** Unresolved accepts block new merges until target-wide Git-derived reconciliation proves every outcome.
- **Agent tool contract.** `agent-tools-v2` exposes only curated single-page body create and `AgentAnchoredPatchChange`; server-side GO enforces the same limits independently of the schema.
- **Correction task boundary.** GO-owned `kb_ops` operational record, not canonical content or decision; content fixes still require MR/human decision/GO merge.

## UX & Interaction Patterns

- Business users and approvers move through catalog → document → editor → agent → diff → decision → merge in one interface without Git/CLI.
- Review shows the exact diff and separately highlights machine-significant changes; an unreliable preview blocks apply/merge.
- Accept/reject/cancel/edit are bound to the exact `proposal_sha`; an edit creates a new `ProposalVersion` and resets approval.
- `STALE_BASE` is surfaced as «Документ изменился» with a diff and a path to start new work from the fresh revision.
- Pending/group review queues use bounded pagination and longest-normalized-prefix assignment; reload preserves work.
- Agent sidebar exposes page/subtree/Space scope with visible context limits and citations; long reads return explicit bounds and cursors.

## Cross-Story Dependencies

- E04.1 depends on E03.1/E03.2 (durable drafts/history and lossless editor adapter).
- E04.2 depends on E04.1 (exact ProposalRecord/ProposalVersion).
- E04.3 depends on E04.2 (canonical decision/merge/recovery).
- E04.4 depends on E04.2; it requires no index, preflight, or cutover story.
- E04.5 depends on E04.4 plus E02.1/E02.3 (canonical reads and per-Space authorization).
- E04.6 depends on E04.3 and E04.5.
- E04.7 depends on E04.4 and the `docops-correction-task-v1` contract.
- Epic 4 is a prerequisite for E05 (published retrieval needs exact merge evidence), E06 (cutover uses GO merge/DecisionRecord lifecycle), E07, and E08.
