---
title: 'KBI.3.3 Auto-merge policy engine'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '2e50ae6979a2bafc34a3ea1c7de7acd5fc26c58b'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-3-context.md'
  - '{project-root}/specs/corporate-kb/adr/ADR-018-source-sync-auto-merge-policy.md'
warnings: []
deferred:
  - summary: >-
      ADR-018 §2.4–2.6 FM access/owner/status keys, content-standard, CONFLICT_WITH_CURATED,
      and POLICY_BUNDLE_MISMATCH are not evaluated here. KBI.4 owns content-standard and queue.
    evidence: |-
      _policy checks ownership, tombstone, bounds, trusted/auto_merge/validation_required only.
    location: >-
      src/kb-ingestion/app/services/source_sync.py
    severity: medium
  - summary: >-
      HttpGOClient auto_merge is untested; create_app wires StubGOClient. Live GitLab/GO not claimed.
    evidence: |-
      Default wiring is StubGOClient. No live GO evidence.
    location: >-
      src/kb-ingestion/app/main.py
    severity: low
  - summary: >-
      Revert-MR rollback after auto-merge is not implemented (ADR verification list). Recovery is KBI.4/GO.
    evidence: |-
      StubGOClient.auto_merge records decision+merge only.
    location: >-
      src/kb-ingestion/app/adapters/go_client.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Trusted source не может обновлять KB без human DecisionRecord, а untrusted/curated не защищены.

**Approach:** Policy на каждом non-noop delta. Auto-merge только если trusted+auto_merge+!validation_required, ownership source_managed|migrated, bounds OK, не curated/live_operational, delete имеет tombstone. Иначе MR `human_review`. Curated → `CURATED_DOCUMENT_PROTECTED` без GO. Bounds → `BOUND_EXCEEDED` fallback. GO stub: proposal для human_review и merged; auto-merge пишет DecisionRecord `actor_type=source_sync`.

## Boundaries & Constraints

**Always:**
- Auto-merge iff: trusted, auto_merge, validation_required=false, ownership in {source_managed,migrated}, files≤max_files_per_sync, lines≤max_lines_changed, not curated, not live_operational, delete has tombstone=true.
- Proposal создаётся для human_review и merged (audit). Refused (curated/live_operational/tombstone) не создаёт proposal.
- Auto-merge: stub merge + decision `actor_type=source_sync`, `rationale="auto-merge per source policy"`.
- curated target → outcome `refused`, code `CURATED_DOCUMENT_PROTECTED`, merge нет.
- live_operational → `LIVE_OPERATIONAL_FORBIDDEN`, refused.
- Bounds exceed → все non-noop этого run `human_review`, code `BOUND_EXCEEDED`.
- delete без tombstone → `TOMBSTONE_REQUIRED`, не auto-merge.
- `proposal_data.actor_type=source_sync`. Trailers Source-Sync-Id, Source-Version, Sync-Run-Id в decision_data.
- `proposal_data.origin` schema `source-origin-v1`.
- GO submit/merge failure → 502 `GO_SUBMIT_FAILED`; cursor item не commit.

**Never:**
- Не auto-merge structure/curated/untrusted/live_operational. Не human DecisionRecord на auto-merge path. Не live GitLab. Не менять ADR-018.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| trusted auto | auto_merge config, source_managed upsert | merged, actor_type=source_sync, trailers | N/A |
| migrated | ownership_mode migrated | merged | N/A |
| validation | validation_required true | human_review, proposal, not merged | N/A |
| bounds files | files over max | human_review BOUND_EXCEEDED | N/A |
| bounds lines | lines over max | human_review BOUND_EXCEEDED | N/A |
| curated | ownership_mode curated | refused CURATED_DOCUMENT_PROTECTED, no GO | N/A |
| live_operational | ownership_mode live_operational | refused LIVE_OPERATIONAL_FORBIDDEN, no GO | N/A |
| delete no tombstone | action=delete tombstone=false | refused TOMBSTONE_REQUIRED | N/A |
| GO down | StubGOClient.fail_message | отказ | 502 GO_SUBMIT_FAILED |
| GO empty id | return_empty_id | отказ | 502 GO_SUBMIT_FAILED |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/services/source_sync.py` — `_policy`, `_apply_change`, `_proposal_payload`.
- `src/kb-ingestion/app/adapters/go_client.py` — GOClient.auto_merge; StubGOClient decisions/merges; HttpGOClient untested.
- `src/kb-ingestion/tests/test_source_sync.py` — 3.3 rows.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/services/source_sync.py` -- _policy -- ADR-018 trusted/bounds/curated/tombstone
- `src/kb-ingestion/app/adapters/go_client.py` -- auto_merge + DecisionRecord -- actor_type=source_sync
- `src/kb-ingestion/tests/test_source_sync.py` -- матрица 3.3 -- доказательство

**Acceptance Criteria:**
- Given auto_merge=true and validation_required=false, when policy accepts, then GO merges without human DecisionRecord and records actor_type=source_sync.
- Given migrated ownership, when policy accepts, then merged.
- Given diff exceeding file or line bounds, when auto-merge attempted, then fallback to MR + human review.
- Given curated document, when auto-merge attempted, then CURATED_DOCUMENT_PROTECTED without GO call.
- Given live_operational, when auto-merge attempted, then LIVE_OPERATIONAL_FORBIDDEN.
- Given delete without tombstone, when processed, then TOMBSTONE_REQUIRED.
- Given GO submit failure, when sync runs, then 502 GO_SUBMIT_FAILED.

## Spec Change Log

- 2026-11-17: policy engine; stub auto_merge + DecisionRecord; curated/bounds/tombstone.
- 2026-11-17 review: migrated; live_operational; trailers; origin source-origin-v1; empty GO id 502; queued job marked failed.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: high 0, medium 4 patched + 1 deferred, low patched/deferred
- findings:
  - `[medium]` `[patch]` trailers untested — asserted Source-Sync-Id/Source-Version/Sync-Run-Id
  - `[medium]` `[patch]` live_operational untested — LIVE_OPERATIONAL_FORBIDDEN
  - `[medium]` `[patch]` migrated ownership untested — auto-merge allowed
  - `[medium]` `[patch]` empty GO id would merge with blank id — GO_SUBMIT_FAILED 502
  - `[low]` `[patch]` origin source-origin-v1 missing from proposal_data — added
  - `[low]` `[reject]` create GO proposal for curated — refused must not call GO (AC)
  - `[medium]` `[defer]` FM keys, content-standard, CONFLICT_WITH_CURATED, POLICY_BUNDLE_MISMATCH — KBI.4
  - `[low]` `[defer]` HttpGOClient live untested
  - `[low]` `[defer]` revert-MR rollback

## Auto Run Result

- Policy auto-merges trusted source_managed/migrated within bounds; curated/live_operational/tombstone refuse without GO; bounds and validation_required stay human_review with a proposal.
- Files: `services/source_sync.py`, `adapters/go_client.py`, `tests/test_source_sync.py`
- Review: patched trailers/origin/migrated/live_operational/empty-id; deferred ADR content-standard and live GO.
- Follow-up review: `true`. Residual: KBI.4 FM/data barrier; live GO.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 165 passed; ruff clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (165)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
