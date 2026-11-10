# T05b Canonical DecisionRecord, Exact Merge and Conclusive Recovery Evidence Summary

- **Generated:** 2026-11-10T11:24:19.077616+00:00
- **Contracts version:** decision-record-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 8
- FAIL (expected): 9
- FAIL (unexpected): 0
- BLOCKED: 5
- **Total:** 22

## Top findings

### FAIL (expected)
- `decision.self_approval_author.rejected` (decision): rejected: self_approval=True, hash_mismatch=False, target_ok=True, missing=[]; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`
- `decision.self_approval_version_author.rejected` (decision): rejected: self_approval=True, hash_mismatch=False, target_ok=True, missing=[]; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`
- `decision.self_approval_requester.rejected` (decision): rejected: self_approval=True, hash_mismatch=False, target_ok=True, missing=[]; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`
- `decision.note_tag_hash_mismatch.rejected` (decision): rejected: self_approval=False, hash_mismatch=True, target_ok=True, missing=[]; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`
- `merge_proof.wrong_first_parent.invalid` (merge_proof): merge proof invalid; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`
- `merge_proof.missing_trailer.invalid` (merge_proof): merge proof invalid; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`
- `merge_proof.concurrent_loser_zero_writes.invalid` (merge_proof): merge proof invalid; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`
- `recovery.timeout_not_conclusive.retry_denied` (recovery): retry should be denied; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`
- `recovery.conflicted_terminal.retry_denied` (recovery): retry should be denied; fixture `_bmad-output/test-artifacts/t05b/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_gitlab_decision_note` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_protected_tag` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_merge_commit` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_per_target_serialization` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_recovery_barrier` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.decision_record.valid` (schema): sample decision record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `decision.valid_accept.valid` (decision): canonical DecisionRecord note+tag on exact proposal_sha
- `decision.valid_reject.valid` (decision): canonical DecisionRecord note+tag on exact proposal_sha
- `merge_proof.valid_merge_proof.valid` (merge_proof): merge commit first-parent=base, second-parent=proposal, trailers match, one main write
- `recovery.conclusive_failed_retry.guarded_retry_allowed` (recovery): conclusive failed permits guarded retry with same decision_id and new attempt_id

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t05b/run_t05b_tests.py
```

Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
