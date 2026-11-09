---
title: 'T13a Complete portable export with exact refs and closure'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/export-manifest.schema.json
  - specs/corporate-kb/contracts/decision-record.schema.json
  - specs/corporate-kb/contracts/index-snapshot.schema.json
  - specs/corporate-kb/components/git-orchestrator.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-6-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that a portable export is a complete authorized package with explicit Git refs, decisions manifest, assets manifest, policy bundle/revisions, grants mapping, and closure; and that missing/rejected/mutable/hash-mismatched assets block any "complete" claim.

**Approach:** Create a T13a harness that exercises synthetic YAML fixtures for export authorization, Git clone with explicit refs, decisions/assets/policy/grants manifests, exact refs, and incomplete-package rejection.

## Boundaries & Constraints

**Always:**
- Export is a complete authorized package: Git clone with explicit full object SHAs and refs, decisions manifest, assets manifest, policy bundle/revisions and grants mapping.
- Cross-Space history and secrets are excluded.
- Per-batch authorization is required; unauthorized batches are rejected.
- Missing, rejected, mutable, or hash-mismatched assets block any "complete" claim.
- DecisionRecords/MR metadata are included with exact refs and closure.

**Never:**
- Do not use real GitLab/object-store credentials or production corpus.
- Do not include secrets, tokens, private chats, or cross-Space history in the export.
- Do not claim "complete" when closure, hashes, or authorization checks fail.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Export authorization | Per-batch authorization check | Authorized batch proceeds; unauthorized rejected | Unauthorized batch exported → FAIL |
| Git clone refs | Explicit full object SHAs and refs | All required refs/objects listed with exact SHAs | Missing/short SHA → FAIL |
| Decisions manifest | Accepted/rejected/cancelled MRs, tags, trailers | Exact decision_id, proposal_sha, record_sha256 | Fabricated/unsigned decision → FAIL |
| Assets manifest | Immutable attachments with hashes/sizes/versions | All assets present and hash-verified | Missing/mutable/hash mismatch → FAIL |
| Policy bundle | Access/approval/policy revision SHAs | Closure over all revisions | Missing revision → FAIL |
| Grants mapping | Authz grants from Git policy + IdP | Stable identity/group mapping included; secrets excluded | Secrets included → FAIL |
| Closure | Complete closure check | Package marked complete only when all checks pass | Incomplete package marked complete → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t13a/run_t13a_tests.py` — main harness.
- `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml` — synthetic export/fixture scenarios.
- `specs/corporate-kb/contracts/export-manifest.schema.json` — export manifest contract.
- `specs/corporate-kb/contracts/decision-record.schema.json` — canonical DecisionRecord.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t13a/run_t13a_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t13a/export-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t13a/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `6-3-t13a-...` → `done`.

**Acceptance Criteria:**
- [x] Given an authorized export request, the package includes Git clone with explicit full object SHAs and refs.
- [x] Given a decisions manifest, it includes accepted/rejected/cancelled outcomes with exact decision_id, proposal_sha, record_sha256, MR note, and protected tag refs.
- [x] Given an assets manifest, every attachment has immutable `{object_id,version,sha256,size,media_type,source_ref}` and hash-verification passes.
- [x] Given policy bundle and grants mapping, all access/approval/policy revision SHAs and stable identity/group mappings are present; secrets are excluded.
- [x] Given missing, rejected, mutable, or hash-mismatched assets or unauthorized batches, the package is marked incomplete and no "complete" claim is made.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns; validators operate on synthetic YAML fixtures against the `export-manifest-v2` contract. Live GitLab/object-store/IdP checks remain BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness builds a synthetic export package descriptor and validates closure over refs, decisions, assets, policies, and grants. It explicitly marks packages incomplete when any required element is missing, mutable, or hash-mismatched. Real object-store ACL and GitLab metadata export remain BLOCKED per G0-D16.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t13a/run_t13a_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t13a/run_t13a_tests.py` -- expected: writes `export-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t13a/export-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t13a/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
