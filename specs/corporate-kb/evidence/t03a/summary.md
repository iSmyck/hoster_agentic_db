# T03a Stable Identity Core and Nested Group Snapshots Evidence Summary

- **Generated:** 2026-11-08T21:55:52.113933+00:00
- **Contracts version:** authz-context-v2
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** 788e299a5316c7d5df685a8f11b043ff36135a10
- **Environment:** synthetic_local_no_idp
- **Sensitive data present:** False

## Counts

- PASS: 36
- FAIL: 0
- BLOCKED: 6
- **Total:** 42

## Top findings

### BLOCKED
- `runtime.live_ldap_nested_groups` (runtime): requires live IdP/LDAP/AD/GO sandbox and credentials
- `runtime.live_oidc_jit_provisioning` (runtime): requires live IdP/LDAP/AD/GO sandbox and credentials
- `runtime.live_ad_object_guid` (runtime): requires live IdP/LDAP/AD/GO sandbox and credentials
- `runtime.live_keycloak_rename` (runtime): requires live IdP/LDAP/AD/GO sandbox and credentials
- `runtime.live_empty_group_revocation` (runtime): requires live IdP/LDAP/AD/GO sandbox and credentials
- `runtime.live_policy_epoch_sync` (runtime): requires live IdP/LDAP/AD/GO sandbox and credentials

### PASS (sample)
- `harness.fixtures_loaded` (harness): synthetic identity and group fixtures load
- `identity.stable_id.oidc_valid` (identity): oidc identity has stable key
- `identity.stable_id.ad_valid` (identity): ad identity has stable key
- `identity.stable_id.ldap_valid` (identity): ldap identity has stable key
- `identity.stable_id.oidc_missing_sub` (identity): identity missing stable key or using email/login as key
- `identity.stable_id.ad_missing_object_guid` (identity): identity missing stable key or using email/login as key
- `identity.stable_id.ldap_missing_entry_uuid` (identity): identity missing stable key or using email/login as key
- `identity.stable_id.email_only` (identity): identity missing stable key or using email/login as key
- `identity.stable_id.oidc_empty_issuer` (identity): identity missing stable key or using email/login as key
- `groups.cycle.nested_groups` (group): cycle(s) detected: []

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t03a/run_identity_tests.py
```

Real LDAP/IdP/AD/CI/hoster.ai integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural/identity evidence; it does not claim production integration PASS.
