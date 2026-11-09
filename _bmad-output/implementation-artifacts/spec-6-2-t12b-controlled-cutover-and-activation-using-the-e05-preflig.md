---
title: 'T12b Controlled cutover and activation using the E05 preflight artifact'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/index-snapshot.schema.json
  - specs/corporate-kb/contracts/decision-record.schema.json
  - specs/corporate-kb/components/git-orchestrator.md
  - specs/corporate-kb/components/retrieval-indexing.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-6-context.md
  - _bmad-output/implementation-artifacts/spec-5-1-t10a-exact-sha-ci-index-build-and-validated-preflight-artifact.md
  - _bmad-output/implementation-artifacts/spec-5-2-t10b-published-retrieval-search-cursors-and-monotonic-publication-lifecycle.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that cutover follows an exact-SHA, non-auto-merge lifecycle: write freeze, HEAD verification, protected tags/MR-only rules, inactive preflight validation, separate published artifact creation, and activation only after the published pointer is observable.

**Approach:** Create a T12b harness that exercises synthetic YAML fixtures for the CutoverRecord, freeze→HEAD→protection→preflight→published→activation order, negative direct-push proof, and refusal to bypass the sequence.

## Boundaries & Constraints

**Always:**
- Cutover is an exact-SHA lifecycle: write freeze first, verify `HEAD == cutover_sha`, establish protected validation/cutover tags and MR-only/merge-only-GO rules.
- A signed CutoverRecord binds Space, exact `cutover_sha`, evidence, sign-off stable identity and UTC timestamp.
- A full inactive preflight artifact (`snapshot_sha=cutover_sha`, `serving_allowed=false`) is requested and verified before publication.
- A separate published request/run/snapshot is created with new IDs but the same SHA/closure/policy/hashes; activation happens only after the validated published pointer is observable.
- After activation all managed writes flow through GO/MR/human DecisionRecord/GO merge.

**Never:**
- Do not use real GitLab/GO credentials or production corpus.
- Do not auto-merge, direct-push, bulk-bypass, or activate before preflight validation.
- Do not allow HEAD drift after sign-off without a new CutoverRecord.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CutoverRecord | Space, exact cutover_sha, evidence, sign-off | Valid CutoverRecord with all bindings | Missing field/mismatch → FAIL |
| Write freeze | User access closed, no published index | Freeze established before protection | Activation before freeze → FAIL |
| HEAD verification | HEAD == cutover_sha | Verified exact SHA | Drift/mismatch → FAIL |
| Protected rules | Validation/cutover tags, MR-only/merge-only-GO | Rules active with negative direct-push proof | Direct push succeeds → FAIL |
| Preflight→published order | Inactive preflight validated first | Separate published IDs, same SHA/closure/policy | Preflight activated or IDs reused → FAIL |
| Activation | Published pointer observable | Space/user access enabled | Activation before published pointer → FAIL |
| Bypass | Any skip/freeze/activation order | Rejected with zero canonical writes | Bypass succeeds → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t12b/run_t12b_tests.py` — main harness.
- `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml` — synthetic cutover/activation/fixture scenarios.
- `specs/corporate-kb/contracts/index-snapshot.schema.json` — preflight/published artifact contract.
- `specs/corporate-kb/contracts/decision-record.schema.json` — canonical DecisionRecord.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t12b/run_t12b_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t12b/cutover-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t12b/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `6-2-t12b-...` → `done`.

**Acceptance Criteria:**
- [x] Given a validated dry-run and T10a preflight artifact, cutover creates a CutoverRecord binding Space, exact cutover_sha, evidence, sign-off stable identity and UTC timestamp.
- [x] Given a cutover request, write freeze is established first, user access is closed, and no published index exists.
- [x] Given a frozen repository, HEAD is verified to equal cutover_sha; drift requires a new CutoverRecord.
- [x] Given verified HEAD, protected validation/cutover tags and MR-only/merge-only-GO rules are established with a negative direct-push proof.
- [x] Given protected rules, a full inactive preflight artifact is requested and verified before any published artifact is created.
- [x] Given validated preflight, a separate published request/run/snapshot is created with new IDs but the same SHA/closure/policy/hashes, and Space/user access is activated only after the published pointer is observable.
- [x] Given any attempted bypass of the freeze→HEAD→protection→preflight→published→activation order, the operation is rejected with zero canonical writes.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns; validators operate on synthetic YAML fixtures. Live GitLab/GO/object-store/IdP checks remain BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the cutover state machine and enforces the exact-SHA lifecycle order. It validates the one-way artifact dependency from T10a preflight to T12b published/activation without reimplementing the index engine. Real GitLab protected-tag/MR-only enforcement remains BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t12b/run_t12b_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t12b/run_t12b_tests.py` -- expected: writes `cutover-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t12b/cutover-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t12b/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
