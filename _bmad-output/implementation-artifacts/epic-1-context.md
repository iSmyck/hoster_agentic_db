# Epic 1 Context: Contract sandbox & defect prevention

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Build a thin, reproducible QA harness that runs against two synthetic repository-per-Space fixtures and produces executable validation reports for the current contracts: document front matter, access/approval policies, ProposalRecords, DecisionRecords, AuthzContext, and index snapshots. The harness must give QA usable deterministic defect evidence before feature work starts, and must remain a lightweight adapter over existing contracts and CI rather than becoming a new runtime service, canonical store, or general-purpose testing platform.

**Gaps encountered:** No standalone PRD, product brief, or UX contract were found in the planning artifacts. Epic 1 scope is therefore drawn from `epics.md` and the architecture spine.

## Stories

- Story 1.1 (T01): Reproducible two-Space sandbox and executable defect evidence

## Requirements & Constraints

- Provide a documented reproducible command that provisions only the two synthetic repository-per-Space fixtures and contract runners needed by the delivery stories.
- Validate deterministic serialization, full-SHA semantics, and hash semantics for front matter, ProposalRecord, DecisionRecord, index snapshot, AuthzContext, and policy schemas against approved fixtures.
- Exercise the CF-01–CF-30 contract vectors and user-value acceptance scenarios; invalid IDs, revisions, policy bundles, stale contexts, malformed payloads, and forbidden capabilities must be rejected explicitly and without writes.
- Produce validation reports that record exact versions, environment, commands, expected/actual results, and raw SHA-256 for every executed check.
- Every failure must provide a minimal reproduction fixture, stable IDs/SHAs, sanitized mismatch details, and rerun instructions.
- Passed, failed, BLOCKED, and unexecuted checks must remain explicitly distinct; prepared but unexecuted vectors stay DESIGN_NOT_EXECUTED.
- All surfaced API/tool errors must use the unified `{code, message, request_id, retryable}` shape with sanitized optional details; `LIMIT_EXCEEDED` must include effective bounds and a valid continuation cursor when more authorized results exist.
- Cursor/truncation semantics: `truncated=false` is equivalent to `reason=none` plus `next_cursor=null`; `truncated=true` requires a non-none reason and a next cursor.
- Identical retries must preserve operation identity without duplicate side effects; doubles used for local state-machine checks must be labelled as unit evidence and never reported as real GitLab/IdP/PostgreSQL/CI/hoster.ai integration acceptance.
- Machine output must be retained in `_bmad-output/test-artifacts/t01`; sanitized review evidence must be stored in `specs/corporate-kb/evidence/t01/`.
- Incompatible contract changes require an explicit `schema_version`, migration, and rollback decision; silently changing canonical or hash semantics is not allowed.
- No production corpus, migration, credentials, or deployment is authorized by this epic; fixtures are disposable.

## Technical Decisions

- Canonical storage is Git-native: Markdown + closed front matter in GitLab, full commit SHA as revision, MR as proposal, canonical DecisionRecord JSON in append-only structured MR note plus protected annotated tag `kb-decisions/<decision_id>` on `proposal_sha`.
- GO is a separate ports-and-adapters monolith that owns canonical writes/merge coordination; the QA harness must not introduce a second write path or canonical store.
- Release evidence must fix corpus SHA, code/config/model/tool-schema versions, dataset, and sanitized results; deterministic negative tests are required and LLM judge alone is not acceptance.
- ID conventions: `space_id` is a stable lowercase slug; `document_id` is an opaque UUID independent of path; `decision_id` is a UUID and idempotency key; IDs are never reused. Revisions use full lowercase SHA; ordering is by Git ancestry, never lexicographic.
- Time/text: UTC RFC 3339, UTF-8, lower_snake_case enums, Russian UI labels.
- API conventions: `/api/kb/v1` prefix; mutations require `Idempotency-Key` bound to actor + route + payload hash; reused key with different payload returns `IDEMPOTENCY_KEY_REUSED` with zero writes.
- Relevant versioned contracts: `document-front-matter-v2`, `authz-context-v2`, `agent-tools-v2`, `export-manifest-v2`, `index-snapshot-v1`, `docops-review-metadata-v1`, and `docops-correction-task-v1`.
- CF-30 is intentionally DESIGN_NOT_EXECUTED: the test catalog covers CF-01–CF-30, but design coverage does not equal executed verification.

## Cross-Story Dependencies

- E00 (baseline audit and G0 design review) must be complete before Epic 1 starts.
- The E01.1 contract harness and two-Space fixtures are prerequisites for E02.1 (Git-backed tree/direct read), E02.2 (stable identity), E02.3 (per-Space policy), E03.1 (durable drafts/history), and later epics that rely on reproducible contract validation.
