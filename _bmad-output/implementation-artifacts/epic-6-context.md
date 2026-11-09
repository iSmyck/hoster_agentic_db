# Epic 6 Context: Migration & portability

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Move external content into the Git-native managed knowledge base through a safe, reviewable pipeline; activate the corpus at an exact frozen SHA; and ensure the whole Space remains portable, mirrorable and restorable on a clean isolated instance. No source content becomes canonical without a validated dry-run, admission gates and explicit cutover sign-off; after activation every change flows through GO/MR/human decision/GO merge. No separate PRD or UX contract exists in planning artifacts, so this context is drawn from the approved epics and architecture spine.

## Stories

- Story 6.1 (T12a): Deterministic dry-run import and admission gates
- Story 6.2 (T12b): Controlled cutover and activation using the E05 preflight artifact
- Story 6.3 (T13a): Complete portable export with exact refs and closure
- Story 6.4 (T13b): Mirror/metadata backup, rebuild and conservative clean restore

## Requirements & Constraints

- Dry-run import must be deterministic and write-zero-canonical: it returns path→stable-ID mapping, tree, provenance, source versions/hashes, relative links/anchors, attachment manifests, ownership mapping, original/extracted hashes and explicit losses/errors. Replaying the same source/config reproduces the manifest; changed inputs create new evidence rather than mutating old evidence.
- Admission gates run before corpus or preview admission: stable source owner and completed data barrier are mandatory; every PII hit requires human disposition; critical/handwritten media is blocked until required human transcription/verification exists; traversal, symlinks, absolute/ambiguous paths, executable HTML/MDX/XSS, secrets, invalid UTF-8, oversized/decompression-bomb inputs and mutable/unhashed attachments are rejected.
- Pre-cutover bulk push is allowed only into unpublished `main` while user access is closed and no published index exists. It requires separate import authorization, expert validation and a signed CutoverRecord binding Space, exact `cutover_sha`, evidence, sign-off stable identity and UTC timestamp.
- Cutover is an exact-SHA, non-auto-merge lifecycle: write freeze first, verify `HEAD == cutover_sha`, establish protected validation/cutover tags and MR-only/merge-only-GO rules with negative direct-push proof, request and verify a full inactive preflight index artifact (`snapshot_sha=cutover_sha`, `serving_allowed=false`), then create a separate published request/run/snapshot with new IDs but the same SHA/closure/policy/hashes, and only activate Space/user access after the validated published pointer is observable. HEAD drift after sign-off requires a new CutoverRecord.
- Post-cutover, all updates—engineering fixes, repeated imports, source updates—use GO/MR/human DecisionRecord/GO merge. Direct push, auto-merge, bulk bypass and history rewrite are forbidden. Curated local edits are preserved; source-managed updates require reviewed MR.
- Ownership modes govern source relationships: `migrated` ignores the old source as a writer; `source_managed` denies local edits and requires reviewed MR for every update; `curated` turns external changes into a reviewable three-way proposal/conflict; `live_operational` remains typed read-only with `snapshot_time` and never creates a wiki page, MR, index entry or sync cursor.
- Portability export is a complete authorized package: Git clone with explicit full object SHAs and refs, decisions manifest, assets manifest, policy bundle/revisions and grants mapping. Cross-Space history and secrets are excluded; per-batch authorization is required; missing/rejected/mutable/hash-mismatched assets block any "complete" claim.
- Backup covers Git mirror of all refs/objects, protected decision/cutover tags, GitLab MR/note/audit metadata, immutable objects, nonsecret config and a separately controlled secrets recovery policy. GO-owned correction-task operational state is backed up separately from its durable non-Git-derived store.
- Restore must be proven on a clean isolated instance with no inherited active grants, pointer or operational rows: rebuild `kb_authz` from Git policy plus fresh IdP data, Git-derived `kb_ops` from MRs/notes/tags/history/source registry under a global merge freeze with conservative per-target barriers, and `kb_index` from Git plus immutable assets and approved config. Correction tasks are restored separately with hash/event-sequence/perimeter checks and linked-MR reconciliation. Unknown merge outcomes remain quarantined; missing assets, grants or closure block READY.
- Rebuild semantics are conservative: unknown outcomes are not cleared by an empty database, terminal label, superseded decision or generic TTL; file/dump existence alone is not a restore PASS.

## Technical Decisions

- Git-native canonical storage: Markdown + front matter in GitLab, full commit SHA as revision, MR as proposal, canonical DecisionRecord in append-only structured MR note plus protected annotated tag `kb-decisions/<decision_id>` on `proposal_sha`, and CutoverRecord on exact `main_sha`.
- Two-phase publication without auto-merge: dry-run → controlled unpublished bulk → freeze → protected rules → inactive preflight → separate published artifact → activation. After cutover all managed writes flow through GO.
- Source determines the update contract: `migrated`, `source_managed`, `curated` and `live_operational` modes with distinct write, merge and cursor semantics.
- Dedicated deployment and full portability package: each client has isolated repositories, config, PostgreSQL/index, object storage, secrets and backups; differences are only versioned config/adapters.
- Canonical DecisionRecord and recoverable projection: `decision_id` UUID, `record_sha256`, merge commit with `Decision-ID`, `Decision-Note-ID`, `Decision-Hash` and `Approved-by` trailers, and a durable per-target `recovery_required` barrier that only conclusive Git-derived reconciliation can clear.
- Index only from eligible published `main`: inactive preflight never serves retrieval, published artifact becomes active only through a single CI/index writer per `(space_id, profile_id)` using fence/CAS pointer promotion.
- Schema ownership: Identity/AuthZ adapter owns `kb_authz`, GO owns `kb_ops`, CI/index workers own `kb_index`; cross-schema writes and foreign keys are forbidden.
- Idempotency: every mutation carries an `Idempotency-Key`; reuse with a different actor, route, path or payload is rejected with zero writes.

## UX & Interaction Patterns

- Lifecycle states must be explicit and distinct: `draft`, `in_review`, `published`, `indexed`, `archived`, `conflicted`, plus `recovery_required`, quarantine, inactive preflight and `INDEX_NOT_READY`.
- Dry-run feedback must expose losses/errors/security/PII/media blockers rather than look like success. Source sync UI shows no-op/outstanding/conflict/tombstone, seen/proposed/merged lag and stale/owner feedback.
- Errors use a unified `{code, message, request_id, retryable}` shape with sanitized details; timeout and recovery barriers must not be presented as published success or as a prompt for blind retry.

## Cross-Story Dependencies

- T12a depends on E02.3 per-Space authorization and E03.1 exact revisions; it may run in parallel with T05/T10 but never creates canonical writes.
- T12b depends on T12a validated dry-run, E04.2/T05 GO/MR/DecisionRecord merge lifecycle, and E05.2 published lifecycle consuming E05.1 preflight artifact. This is a one-way artifact dependency from E05 to E06.
- T13a follows E04.2 and E06.2.
- T13b follows E06.3 and E06.2 and reuses the E04.7 `docops-correction-task-v1` contract for correction-task backup/restore/reconciliation.
