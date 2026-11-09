# Epic 3 Context: Save & history

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Give business authors durable, branch-based drafts and a lossless editing experience while keeping the Git repository as the single source of truth. Every save creates or updates an attributed draft branch without touching `main`; concurrent edits surface explicit conflicts instead of silently overwriting content. History, diff and restore are read directly from Git revisions, and restore always produces a reviewed revert-MR rather than rewriting history. The epic also hardens the browser editor so that canonical Markdown, front matter, stable links, attachment metadata and Cyrillic input survive a WYSIWYG round-trip.

> **Planning gap:** no PRD, product brief or standalone UX/design contract was found in the planning artifacts. The goal and constraints below are derived from `epics.md`, the architecture spine, and the applied sprint-change proposal. The implementation-readiness gate that covers this epic is currently FAIL; the related sprint-change proposal has been applied but does not by itself grant readiness PASS.

## Stories

- Story 3.1: Durable drafts, guarded navigation and cursor-based Git history
- Story 3.2: Lossless TipTap adapter and browser editor gate

## Requirements & Constraints

This epic covers the document model, Git revisions, serialization and recovery concerns that sit between reading and governed merge:

- Drafts must be durable across browser or service restarts. A transient unsaved buffer must never be mistaken for a durable draft.
- Manual and autosave operations must be idempotent and must leave `main` untouched. The current target `base_sha` is rechecked before each save.
- Concurrent edits that start from the same base must be detected when the target advances. The second author receives a human-readable stale-base conflict with a diff view and must start new work from the fresh revision. Last-write-wins, automatic conflict merge and silent metadata/attachment replacement are forbidden.
- History and diff must come from real Git attribution and ancestry. Paged history must expose an explicit truncation reason and next cursor; the cursor binds the per-Space history snapshot, scope, policy/group/revocation and actor epochs.
- Restore must select the exact displayed revision and create a reviewed revert-MR with a new commit. Stale cursor, ambiguous revision, unauthorized historical object or cross-Space reference is rejected without exposure or canonical writes.
- The editor must preserve every supported canonical construct through parse → edit → serialize → parse round-trips, including the front-matter boundary, stable document IDs and links, table alignment, Cyrillic text, ownership/origin, archive metadata and immutable attachment tuples. Any unintended normalization fails the story.
- Browser-level checks for Russian IME/composition, keyboard navigation, screen-reader labels, focus, executable HTML/MDX and XSS must be explicit completion criteria.
- Explicit user states (`draft`, `in_review`, `published`, `indexed`, `archived`, `conflicted`) must be distinguishable. Recovery barriers, quarantine and inactive preflight must never be presented as published or indexed.
- Concurrent author handling in this epic is limited to stale-save conflict and fresh-revision workflow. True concurrent accept/merge serialization is owned by Epic 4.

## Technical Decisions

- The canonical store is Markdown + closed front matter in GitLab. Revisions are full commit SHAs; no short SHAs or lexicographic ordering.
- Drafts live on attributed user branches created by the Git Orchestrator. `main` is never written directly by a user save.
- Exact-SHA semantics apply: a save/proposal is anchored to a fresh `base_sha`; if target HEAD has moved, the operation is refused with a stale-base error and zero writes.
- A new commit or rebase on a proposal branch creates a new ProposalVersion and invalidates any prior approval.
- Restore is implemented as a revert-MR or new commit, never as history rewrite.
- Front matter uses the v2 schema: stable opaque UUID, title/parent, ownership mode, origin where required, stable-ID `links[]`, `valid_until`, archive pairing and immutable attachment tuples.
- Stable links form a single graph by document ID within a Space; rename/move preserves UUID and deep links.
- Paths are repository-relative NFC; `..`, ambiguous separators, absolute paths and backslashes are rejected.
- The TipTap adapter is the owner-selected WYSIWYG path. It must produce a canonical serializer, full source diff and reliable preview. Realtime collaborative editing/CRDT is out of MVP scope.
- Projections are rebuildable and owned by single writers; the Git Orchestrator owns `kb_ops`, CI/index workers own `kb_index`, and the Identity/AuthZ adapter owns `kb_authz`.

## UX & Interaction Patterns

- Authors move between catalog, document, editor, diff and review within one interface without Git/CLI.
- The editor warns on unsaved navigation and distinguishes the transient buffer from the last durable draft SHA.
- Concurrent authors see a clear conflict state, the difference against the fresh revision, and a path to create a new ProposalVersion from the updated base.
- Review and history views show exact revisions, ancestry, attribution and full source diff. Unreliable preview blocks apply/merge.
- Restore is initiated from history and always leads to a reviewed MR; the UI does not allow direct commits to `main`.
- Russian IME/composition ordering and text are preserved; keyboard and screen-reader paths expose usable labels, focus and actions.

## Cross-Story Dependencies

- Story 3.1 depends on the canonical document/read model and per-Space policy/revocation from Epic 2.
- Story 3.2 depends on the durable draft/save/history path built in Story 3.1.
- Epic 4 (governed agent workflow) consumes the drafts and history produced here, but Epic 3 does not depend on Epic 4 for its own acceptance.
