# T07 Exact Business Review and Independent Decisions Evidence Summary

- **Generated:** 2026-11-10T11:25:12.534533+00:00
- **Contracts version:** decision-record-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 11
- FAIL (expected): 6
- FAIL (unexpected): 0
- BLOCKED: 5
- **Total:** 22

## Top findings

### FAIL (expected)
- `review.unreliable_preview_blocks_apply.blocked` (review): blocked; fixture `_bmad-output/test-artifacts/t07/fixtures/scenarios.yaml`
- `csrf_origin.missing_origin.rejected` (csrf_origin): rejected; fixture `_bmad-output/test-artifacts/t07/fixtures/scenarios.yaml`
- `csrf_origin.origin_mismatch.rejected` (csrf_origin): rejected; fixture `_bmad-output/test-artifacts/t07/fixtures/scenarios.yaml`
- `csrf_origin.missing_csrf.rejected` (csrf_origin): rejected; fixture `_bmad-output/test-artifacts/t07/fixtures/scenarios.yaml`
- `lifecycle.recovery_required_not_masked.not_masked` (lifecycle): masked; fixture `_bmad-output/test-artifacts/t07/fixtures/scenarios.yaml`
- `lifecycle.conflicted_not_masked.not_masked` (lifecycle): masked; fixture `_bmad-output/test-artifacts/t07/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_browser_exact_diff` (runtime): requires live sandbox and credentials
- `runtime.live_browser_csrf_origin` (runtime): requires live sandbox and credentials
- `runtime.live_browser_independent_decisions` (runtime): requires live sandbox and credentials
- `runtime.live_browser_lifecycle_views` (runtime): requires live sandbox and credentials
- `runtime.live_browser_preview_reliability` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.decision_record.valid` (schema): sample decision record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `review.complete_review.exact_and_reliable` (review): review shows exact base/proposal SHA, full diff, reliable preview
- `review.stale_base_review.blocked` (review): apply/merge blocked due to stale base or unreliable preview
- `review.independent_decision.exact_and_reliable` (review): review shows exact base/proposal SHA, full diff, reliable preview
- `csrf_origin.valid_origin_and_csrf.valid` (csrf_origin): request has matching Origin and valid CSRF token
- `lifecycle.draft_state.distinguished` (lifecycle): state 'draft' is shown explicitly, not masked
- `lifecycle.in_review_state.distinguished` (lifecycle): state 'in_review' is shown explicitly, not masked

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t07/run_t07_tests.py
```

Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
