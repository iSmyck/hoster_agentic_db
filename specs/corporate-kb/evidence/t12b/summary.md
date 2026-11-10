# T12b Controlled Cutover and Activation Evidence Summary

- **Generated:** 2026-11-10T11:25:40.614586+00:00
- **Contracts version:** index-snapshot-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 11
- FAIL (expected): 18
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 33

## Top findings

### FAIL (expected)
- `cutover_record.missing_cutover_sha.rejected` (cutover_record): CutoverRecord rejected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `cutover_record.missing_signoff_identity.rejected` (cutover_record): CutoverRecord rejected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `write_freeze.activation_without_freeze_rejected.rejected` (write_freeze): freeze precondition failed; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `write_freeze.user_access_open_during_freeze_rejected.rejected` (write_freeze): freeze precondition failed; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `write_freeze.published_index_exists_before_cutover_rejected.rejected` (write_freeze): freeze precondition failed; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `head_verification.head_drift_requires_new_record.rejected` (head_verification): HEAD mismatch or drift detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `head_verification.head_mismatch_before_signoff_rejected.rejected` (head_verification): HEAD mismatch or drift detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `protected_rules.missing_validation_tag.rejected` (protected_rules): protection gap detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `protected_rules.direct_push_not_blocked.rejected` (protected_rules): protection gap detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `protected_rules.merge_not_only_go.rejected` (protected_rules): protection gap detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `preflight_to_published_order.published_without_preflight_validation_rejected.rejected` (preflight_to_published_order): invalid transition detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `preflight_to_published_order.preflight_activated_rejected.rejected` (preflight_to_published_order): invalid transition detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `preflight_to_published_order.reused_published_id_rejected.rejected` (preflight_to_published_order): invalid transition detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `activation.activation_before_observable_pointer_rejected.rejected` (activation): activation precondition failed; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `activation.user_access_opened_without_activation_rejected.rejected` (activation): activation precondition failed; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `bypass.activation_before_published_rejected.rejected` (bypass): out-of-order cutover detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `bypass.published_before_protection_rejected.rejected` (bypass): out-of-order cutover detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`
- `bypass.protection_before_head_rejected.rejected` (bypass): out-of-order cutover detected; fixture `_bmad-output/test-artifacts/t12b/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_gitlab_protected_tags` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_mr_only_rules` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_negative_direct_push` (runtime): requires live sandbox and credentials
- `runtime.live_go_cutover_record` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.preflight.valid` (schema): sample cutover preflight snapshot is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `cutover_record.valid_cutover_record.valid` (cutover_record): CutoverRecord binds Space, exact cutover_sha, evidence, sign-off stable identity and UTC timestamp
- `write_freeze.freeze_before_any_later_step.frozen` (write_freeze): write freeze established first with user access closed and no published index
- `head_verification.head_equals_cutover_sha.exact` (head_verification): HEAD equals cutover_sha before protection and activation
- `protected_rules.protected_tags_and_mr_only_rules.protected` (protected_rules): protected validation/cutover tags and MR-only/merge-only-GO rules with negative direct-push proof
- `preflight_to_published_order.preflight_validated_then_published.ordered` (preflight_to_published_order): inactive preflight validated before separate published artifact with new IDs and same SHA
- `activation.activation_after_published_pointer_observable.active` (activation): Space/user access activated only after published pointer is observable

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t12b/run_t12b_tests.py
```

Real GitLab/GO/object-store/IdP checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
