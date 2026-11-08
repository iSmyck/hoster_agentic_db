# T04a Durable Drafts, Guarded Navigation and Cursor-Based Git History Evidence Summary

- **Generated:** 2026-11-08T22:04:01.080165+00:00
- **Contracts version:** proposal-record-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 20
- FAIL: 0
- BLOCKED: 6
- **Total:** 26

## Top findings

### BLOCKED
- `runtime.live_gitlab_draft_branch` (runtime): requires live GitLab/GO sandbox and credentials
- `runtime.live_gitlab_save_cas` (runtime): requires live GitLab/GO sandbox and credentials
- `runtime.live_gitlab_idempotency_registry` (runtime): requires live GitLab/GO sandbox and credentials
- `runtime.live_gitlab_stale_base_diff` (runtime): requires live GitLab/GO sandbox and credentials
- `runtime.live_gitlab_history_cursor` (runtime): requires live GitLab/GO sandbox and credentials
- `runtime.live_gitlab_restore_revert_mr` (runtime): requires live GitLab/GO sandbox and credentials

### PASS (sample)
- `harness.fixtures_loaded` (harness): synthetic draft fixtures load
- `schema.proposal_record.valid` (schema): sample proposal record is schema valid
- `schema.decision_record.valid` (schema): sample decision record is schema valid
- `schema.front_matter.valid` (schema): sample front matter is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `draft_save.valid_human_save.valid` (draft_save): draft branch/commit created, main unchanged
- `draft_save.valid_agent_save.valid` (draft_save): draft branch/commit created, main unchanged
- `draft_save.missing_base_sha.missing_base_sha` (draft_save): save rejected with MISSING_BASE_SHA
- `draft_save.agent_missing_run_id.missing_base_sha` (draft_save): save rejected with MISSING_BASE_SHA

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py
```

Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural/draft evidence; it does not claim production integration PASS.
