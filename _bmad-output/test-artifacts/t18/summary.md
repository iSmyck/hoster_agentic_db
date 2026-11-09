# T18 Necessary Pilot Part: Pilot Hardening and Protected Deployment Evidence Summary

- **Generated:** 2026-11-08T23:51:16.969194+00:00
- **Contracts version:** pilot-harness-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 11
- FAIL (expected): 16
- FAIL (unexpected): 0
- BLOCKED: 5
- **Total:** 32

## Top findings

### FAIL (expected)
- `pilot_isolation.shared_object_storage_rejected.rejected` (pilot_isolation): isolation problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `pilot_isolation.runtime_ddl_role_rejected.rejected` (pilot_isolation): isolation problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `credential_egress_separation.merge_credential_exposed_to_ci_rejected.rejected` (credential_egress_separation): separation problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `credential_egress_separation.default_egress_open_rejected.rejected` (credential_egress_separation): separation problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `credential_egress_separation.unauthorized_production_resource_rejected.rejected` (credential_egress_separation): separation problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `runbook_rehearsal.missing_upgrade_runbook_rejected.rejected` (runbook_rehearsal): runbook problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `runbook_rehearsal.unreviewed_runbook_rejected.rejected` (runbook_rehearsal): runbook problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `backup_restore_drill.activation_before_snapshot_rejected.rejected` (backup_restore_drill): restore drill problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `backup_restore_drill.missing_closure_rejected.rejected` (backup_restore_drill): restore drill problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `security_regression.auto_merge_allowed_for_engineering_rejected.rejected` (security_regression): security/regression problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `security_regression.secret_canary_disclosure_rejected.rejected` (security_regression): security/regression problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `privileged_bypass_governance.undetected_bypass_rejected.rejected` (privileged_bypass_governance): bypass governance problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `privileged_bypass_governance.bypass_treated_as_managed_path_rejected.rejected` (privileged_bypass_governance): bypass governance problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `business_user_acceptance.engineering_user_participation_rejected.rejected` (business_user_acceptance): acceptance problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `business_user_acceptance.git_cli_used_rejected.rejected` (business_user_acceptance): acceptance problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`
- `business_user_acceptance.self_approval_rejected.rejected` (business_user_acceptance): acceptance problem detected; fixture `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_pilot_environment_isolation` (runtime): requires owner-authorized pilot environment, corpus and credentials
- `runtime.live_backup_restore_drill` (runtime): requires owner-authorized pilot environment, corpus and credentials
- `runtime.live_business_user_acceptance` (runtime): requires owner-authorized pilot environment, corpus and credentials
- `runtime.live_runbook_rehearsal` (runtime): requires owner-authorized pilot environment, corpus and credentials
- `runtime.live_second_client_preparation` (runtime): requires owner-authorized pilot environment, corpus and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.decision_record.valid` (schema): sample decision record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `pilot_isolation.fully_isolated_pilot.isolated` (pilot_isolation): pilot environment isolates Spaces, config, PostgreSQL/index, object storage, secrets, backups and egress; runtime is non-DDL; migrators only rehearsed upgrades
- `credential_egress_separation.credentials_and_egress_separated.separated` (credential_egress_separation): proposal/merge, connector, CI/index and retrieval credentials are separated; default egress closed; approved routes only; no client code branch; no unauthorized production resource
- `runbook_rehearsal.all_runbooks_rehearsed.complete` (runbook_rehearsal): startup/cutover/recovery/export/backup/restore/upgrade/rollback runbooks rehearsed with versions/refs, commands, sanitized outputs, failure handling, BLOCKED items and independent review
- `backup_restore_drill.restore_drill_valid.valid` (backup_restore_drill): backup/restore drill validates closure, rebuilds kb_authz, starts kb_ops under global freeze with barriers, and points kb_index to new validated snapshot before activation
- `security_regression.all_non_privileged_denials.hardened` (security_regression): direct push/merge/auto-merge denied for non-privileged identities; component schema isolation; runtime DDL and cross-client access denied; secret canaries clean
- `privileged_bypass_governance.owner_bypass_handled_as_incident.governed` (privileged_bypass_governance): privileged Owner bypass is detected, quarantined and handled via G0-D3 emergency runbook, not as a managed path

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t18/run_t18_tests.py
```

Live pilot environment, protected deployment, real corpus and second-client acceptance remain BLOCKED. This report contains only synthetic structural evidence; it does not claim production pilot PASS or full T18/G3 readiness.
