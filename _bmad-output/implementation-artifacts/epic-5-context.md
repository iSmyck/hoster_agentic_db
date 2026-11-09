---
epic: 5
title: "Published knowledge pipeline"
status: done
stories:
  - 5-1-t10a-exact-sha-ci-index-build-and-validated-preflight-artifact
  - 5-2-t10b-published-retrieval-search-cursors-and-monotonic-publication-lifecycle
source: _bmad-output/planning-artifacts/epics.md
updated: 2026-11-09
---

# Epic 5: Published knowledge pipeline

## Mission

Build a deterministic, read-only index and retrieval layer that consumes only eligible, published `main` revisions. Produce validated inactive preflight artifacts for cutover, then publish active snapshots through a fenced, monotonic pointer lifecycle. Exact-SHA builds, ancestry/dependency closure, ACL guards and per-Space/profile CAS publication ensure late jobs, pending proposals, inactive preflights and revoked content never serve answers.

## Scope boundaries

**In scope:**
- CI index runner triggered by GitLab events or periodic HEAD reconciliation, using read-only credentials.
- Full and incremental `index-snapshot-v1` builds with separate `snapshot_sha`, document revision SHA, content/dependency hashes, `main_generation`, `index_profile_version` and per-Space policy triple.
- Inactive preflight artifact with `snapshot_sha == cutover_sha` and `serving_allowed=false`.
- Separate published request/run/snapshot with new IDs but same SHA/closure/policy/hashes.
- Single-writer per `(space_id, profile_id)` fence/CAS pointer publication across generations.
- Per-Space exact and semantic retrieval with citations, fresh re-authorization, `LIMIT_EXCEEDED` cursor continuation, and explicit `INDEX_NOT_READY` / stale errors.
- Rebuild from Git + immutable assets after `kb_index` loss.

**Out of scope / deferred:**
- Space activation and user access enablement (owned by E06.2 cutover).
- Import, dry-run and source sync (E06.1).
- Real hoster.ai inference lifecycle and quality thresholds (E07/T11).
- Production embedding model/chunking/reranker selection; pgvector+FTS remains the validated candidate.
- OpenSearch or broker without measured need.

## Stories

### Story 5.1 (T10a): Exact-SHA CI index build and validated preflight artifact

**Owner:** Retrieval platform engineer  
**Requirements:** R02, R04, R11, R18; I01, I02, I08, I09, I10, I11, I12, I14  
**Acceptance ownership:** Full/direct — A12, A22, A35; Supporting — A03, A31  

**Key acceptance:**
- CI resolves exact published `main` SHA; webhooks are hints only.
- Only eligible canonical content enters the projection; `inbox`, templates, service files, archived/deleted pages and unverified critical media are excluded.
- Incremental builds require complete dependency closure, empty `missing_inputs`, matching perimeter/generation/profile/policy and evidence of an independently validated full run on the same `main_sha`.
- Preflight artifact stays inactive (`serving_allowed=false`) and never enables user access or retrieval.
- CI has no Git write/merge capability; indexing failures do not roll back canonical merges.

### Story 5.2 (T10b): Published retrieval, search cursors and monotonic publication lifecycle

**Owner:** Retrieval platform engineer / business reader  
**Requirements:** R03, R04, R05, R11, R16, R18; I01, I02, I06, I08, I09, I10, I11, I12, I13, I14  
**Acceptance ownership:** Full/direct — A02, A03, A11, A21, A22, A25, A32, A35; Supporting — A31  

**Key acceptance:**
- Published lifecycle creates a new non-preflight request/run/snapshot with the same SHA/closure/policy/hashes and repeats full validation before pointer eligibility.
- Concurrent old/new publishers use one fence/CAS register per `(space_id, profile_id)`; late jobs are marked superseded and cannot roll back the active pointer.
- Search fan-out is limited to active published snapshots; every candidate and payload is re-authorized; citations include Space, stable document ID, full revision SHA and section/range.
- Cursors bind the complete ordered per-Space snapshot, profile, policy/group/revocation and actor-epoch set; stale bindings stop with explicit errors.
- UI distinguishes `published` from `indexed`, exposes inactive preflight and `INDEX_NOT_READY`, and never silently truncates.

## Requirements covered

**Primary:** R04 (published-only retrieval), R11 (rebuildable versioned index).  
**Supporting:** R02 (document model/front matter), R03 (canonical direct read), R05 (Space ACL), R16 (limited execution), R18 (regression/evaluation).

## Dependencies

**Hard prerequisites:**
- E02.3 per-Space policy enforcement and revocation.
- E03.1 exact revision / save-to-branch behavior.

**Order within epic:**
- T10a (build/preflight artifact) before T10b (serving/pointer lifecycle).

**Consumers:**
- E06.2 cutover/activation consumes the validated T10a preflight artifact.
- E07/T14 evaluation uses published retrieval results.

## Evidence expectations

- Real GitLab/PostgreSQL/CI exact-SHA builds; T00 synthetic gates are baseline only.
- Full/incremental equivalence and dependency closure cases.
- Validated inactive preflight artifact with `serving_allowed=false`.
- Concurrent pointer CAS/fencing tests showing zero stale writes.
- Per-Space exact/semantic retrieval, citations, `LIMIT_EXCEEDED` continuation, stale/profile/cursor rejection.
- ACL/revocation/archive/pending/unverified-media exclusions.
- Clean `kb_index` rebuild from Git + immutable assets.
- Sanitized evidence in `specs/corporate-kb/evidence/t10/`; machine output in `_bmad-output/test-artifacts/t10/`.

## Gaps and blockers

- **Implementation-readiness gate FAIL:** `epics.md` story-level `Requirements` blocks omit I01–I14, and split story IDs lack complete reverse mapping to `traceability.md` invariants/acceptance criteria. A `bmad-correct-course` pass is required before sprint planning reruns the gate.
- **T10 depends on T03/T04 and E02.3:** per-Space authorization and exact revision semantics must be complete first.
- **No production model/quality thresholds:** pgvector+FTS is the validated candidate; final embedding/chunking/reranker remain owner/config decisions.
- **No real hoster.ai inputs:** inference quality acceptance stays in E07/T11; E05/T10 supplies retrieval only.
- **Object-store ACL unresolved:** LocalStack cross-bucket ACL failed at T00/T13; any retrieval evidence involving immutable attachments must record this as BLOCKED if real object-store checks are unavailable.
