# T06 Merge-Only GO Enforcement, Fencing and Quarantine Evidence Summary

- **Generated:** 2026-11-10T11:24:19.061530+00:00
- **Contracts version:** merge-enforcement-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 5
- FAIL (expected): 9
- FAIL (unexpected): 0
- BLOCKED: 5
- **Total:** 19

## Top findings

### FAIL (expected)
- `enforcement.direct_push_human.security_rejected` (enforcement): denied: user-sales-1 push, main_writes=0; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`
- `enforcement.direct_merge_human.security_rejected` (enforcement): denied: user-sales-1 merge, main_writes=0; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`
- `enforcement.ci_bot_merge.security_rejected` (enforcement): denied: ci-bot merge, main_writes=0; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`
- `enforcement.connector_merge.security_rejected` (enforcement): denied: connector-1 merge, main_writes=0; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`
- `enforcement.go_merge_without_decision.decision_invalid` (enforcement): denied: go-merge-service merge, main_writes=0; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`
- `enforcement.owner_bypass.owner_bypass_quarantine` (enforcement): privileged bypass detected and quarantined; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`
- `fencing.invalid_fencing_token.blocked` (fencing): blocked; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`
- `fencing.recovery_required_flag.blocked` (fencing): blocked; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`
- `fencing.target_quarantine.blocked` (fencing): blocked; fixture `_bmad-output/test-artifacts/t06/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_gitlab_direct_push_denial` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_direct_merge_denial` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_go_merge_service_identity` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_fencing_token` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_owner_bypass_reconciliation` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `enforcement.go_merge_after_decision.allowed` (enforcement): only GO merge service merges after canonical decision
- `fencing.valid_fencing_token.ok` (fencing): valid fencing token, no recovery, no quarantine

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t06/run_t06_tests.py
```

Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
