# T03b Per-Space Policy Enforcement and Revocation Evidence Summary

- **Generated:** 2026-11-08T21:55:52.433111+00:00
- **Contracts version:** authz-context-v2
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** 788e299a5316c7d5df685a8f11b043ff36135a10
- **Environment:** synthetic_local_no_idp
- **Sensitive data present:** False

## Counts

- PASS: 50
- FAIL: 0
- BLOCKED: 5
- **Total:** 55

## Top findings

### BLOCKED
- `runtime.live_authz_context_issuance` (runtime): requires live AuthZ/IdP/GO sandbox and credentials
- `runtime.live_policy_activation` (runtime): requires live AuthZ/IdP/GO sandbox and credentials
- `runtime.live_revocation_epoch_sync` (runtime): requires live AuthZ/IdP/GO sandbox and credentials
- `runtime.live_longest_prefix_enforcement` (runtime): requires live AuthZ/IdP/GO sandbox and credentials
- `runtime.live_error_response_shape` (runtime): requires live AuthZ/IdP/GO sandbox and credentials

### PASS (sample)
- `harness.fixtures_loaded` (harness): synthetic policy fixtures load
- `policy.approval.sales_approval_valid.schema` (policy): approval policy is schema valid
- `policy.approval.sales_approval_valid.duplicate_prefixes` (policy): no duplicate normalized prefixes
- `policy.access.sales_access_valid.schema` (policy): access policy is schema valid
- `policy.access.sales_access_valid.space_binding` (policy): access policy binds exactly one repository_id to one space_id and bundle
- `policy.approval.pricing_approval_valid.schema` (policy): approval policy is schema valid
- `policy.approval.pricing_approval_valid.duplicate_prefixes` (policy): no duplicate normalized prefixes
- `policy.access.pricing_access_valid.schema` (policy): access policy is schema valid
- `policy.access.pricing_access_valid.space_binding` (policy): access policy binds exactly one repository_id to one space_id and bundle
- `policy.approval.invalid_space_id.schema` (policy): approval policy is correctly rejected by schema

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t03b/run_policy_tests.py
```

Real IdP/AuthZ/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural/policy evidence; it does not claim production integration PASS.
