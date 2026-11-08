# Implementation readiness gate

Date: 2026-11-08  
Verdict: **FAIL**  
Tracking generation: **not started**

## Findings

### 1. Story-level traceability is incomplete

`epics.md` does not include I01–I14 in story-level `Requirements` blocks, and split story IDs T03a/T03b, T04a/T04b, T07b, etc. have no complete reverse mapping to invariants and acceptance criteria in `traceability.md`.

A28 is missing from E04.2 despite belonging to T05/crash recovery. A09 is assigned to E03.1 although A09 requires concurrent accept serialization, not only stale-save conflict.

**Fix:** `bmad-correct-course` for requirement/story realignment, then update `epics.md`, `traceability.md` and acceptance ownership before rerunning the gate.

### 2. Acceptance criteria introduce forward dependencies

- E02.1 claims full authorized tree/read before E02.2/E02.3 implement identity and policy enforcement.
- E03.1 claims A09 without the concurrent merge path.
- E07.3 claims A19/second client while the second-client implementation is in E08.4.
- Full and supporting acceptance coverage is not separated.

**Fix:** `bmad-correct-course` to split or reorder stories and remove unsupported acceptance claims. Do not mark those criteria complete in downstream tasks.

### 3. E04.7 requires an unrecorded correction-task contract

The story creates an approver correction task/MR, but the API contracts define only `GET /spaces/{space_id}/docops/review-queue` and `valid_until` projection metadata. There is no task lifecycle, storage, owner, idempotency or correction-task schema in `openapi.yaml` or `docops-review-metadata.schema.json`.

**Fix:** `bmad-architecture` for the contract and `bmad-correct-course` to remove or formally record this scope. T07b must be added to the tracker only after the contract exists.

### 4. Normative conflicts are unresolved

- `spec.md` excludes break-glass, while G0-D3 accepts privileged Owner bypass and an explicit runbook. `epics.md` repeats both statements.
- G0-D8 selects TipTap with WYSIWYG/collaboration, while `spec.md` excludes realtime CRDT from MVP and `epics.md` also declares collaboration/CRDT out of scope.
- `g0-review.md` and `baseline.md` say APPROVED/DONE, but `traceability.md` and `architecture.md` still contain G0 OPEN.

**Fix:** `bmad-correct-course` for normative/ADR synchronization and `bmad-project-context` for stale status documents. The approved option must be explicit in all artifacts.

## Passed checks

- Architecture and UX decisions are extensively recorded in ADR, architecture-spine and component documents.
- No PRD is required by this readiness gate.
- Epic-level dependency declarations are acyclic; T19/T20 remain deferred.

## Required next action

Fix the findings above before generating `sprint-status.yaml`. Then rerun this gate and `bmad-sprint-planning` generation only after PASS.
