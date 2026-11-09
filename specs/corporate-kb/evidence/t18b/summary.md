# T18b Full G3 Backup/Restore/Upgrade and Full Operational Acceptance Evidence Summary

- **Generated:** 2026-11-09T00:01:34.567762+00:00
- **Contracts version:** g3-acceptance-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 14
- FAIL (expected): 21
- FAIL (unexpected): 0
- BLOCKED: 5
- **Total:** 40

## Top findings

### FAIL (expected)
- `clean_restore.activation_before_validation_rejected.rejected` (clean_restore): clean restore problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `clean_restore.missing_kb_authz_rebuild_rejected.rejected` (clean_restore): clean restore problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `clean_restore.missing_assets_closure_rejected.rejected` (clean_restore): clean restore problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `correction_backup.fabricated_decision_rejected.rejected` (correction_backup): correction backup problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `correction_backup.deleted_canonical_write_rejected.rejected` (correction_backup): correction backup problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `correction_backup.second_canonical_write_path_rejected.rejected` (correction_backup): correction backup problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `unknown_merge_quarantine.unknown_auto_cleared_rejected.rejected` (unknown_merge_quarantine): quarantine problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `unknown_merge_quarantine.missing_assets_blocks_ready.rejected` (unknown_merge_quarantine): quarantine problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `unknown_merge_quarantine.missing_correction_backup_blocks_ready.rejected` (unknown_merge_quarantine): quarantine problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `metrics_alerts_runbooks.missing_runbook_rejected.rejected` (metrics_alerts_runbooks): metrics/alerts/runbooks problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `metrics_alerts_runbooks.secrets_in_telemetry_rejected.rejected` (metrics_alerts_runbooks): metrics/alerts/runbooks problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `metrics_alerts_runbooks.missing_rpo_rejected.rejected` (metrics_alerts_runbooks): metrics/alerts/runbooks problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `upgrade_rollback.upgrade_failure_not_blocked_rejected.rejected` (upgrade_rollback): upgrade/rollback problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `upgrade_rollback.missing_rollback_rejected.rejected` (upgrade_rollback): upgrade/rollback problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `upgrade_rollback.missing_seams_rejected.rejected` (upgrade_rollback): upgrade/rollback problem detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `cross_client_negative.cross_client_read_allowed_rejected.rejected` (cross_client_negative): cross-client access detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `cross_client_negative.cross_client_write_allowed_rejected.rejected` (cross_client_negative): cross-client access detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `full_g3_acceptance.missing_second_client_rejected.rejected` (full_g3_acceptance): G3 acceptance gap detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `full_g3_acceptance.missing_real_connector_rejected.rejected` (full_g3_acceptance): G3 acceptance gap detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `full_g3_acceptance.auto_merge_rejected.rejected` (full_g3_acceptance): G3 acceptance gap detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`
- `full_g3_acceptance.missing_independent_review_rejected.rejected` (full_g3_acceptance): G3 acceptance gap detected; fixture `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_second_client_restore` (runtime): requires E08.4 second client, E08.2 real connector and independent owner review
- `runtime.live_correction_backup_restore` (runtime): requires E08.4 second client, E08.2 real connector and independent owner review
- `runtime.live_upgrade_rehearsal` (runtime): requires E08.4 second client, E08.2 real connector and independent owner review
- `runtime.live_independent_g3_review` (runtime): requires E08.4 second client, E08.2 real connector and independent owner review
- `runtime.live_external_source_update` (runtime): requires E08.4 second client, E08.2 real connector and independent owner review

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.correction_task_open.valid` (schema): sample open correction task is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `clean_restore.clean_restore_ready.valid` (clean_restore): clean restore validates refs/metadata/decisions/assets/hashes, rebuilds kb_authz, kb_ops under freeze, kb_index snapshot before activation
- `correction_backup.correction_backup_reconciles_cleanly.valid` (correction_backup): correction backup validates hashes/event-sequence/perimeter and reconciles without fabricating/deleting/resolving tasks or creating second write path
- `unknown_merge_quarantine.known_outcome_ready.valid` (unknown_merge_quarantine): unknown merge outcomes quarantined; missing assets/closure/correction backup blocks READY
- `unknown_merge_quarantine.unknown_quarantined_not_ready.valid` (unknown_merge_quarantine): unknown merge outcomes quarantined; missing assets/closure/correction backup blocks READY
- `metrics_alerts_runbooks.coverage_complete_telemetry_clean.valid` (metrics_alerts_runbooks): runbooks/metrics/alerts cover required areas; telemetry redacted; owner-approved RPO/RTO/retention/cadence recorded
- `upgrade_rollback.upgrade_rehearsal_complete.valid` (upgrade_rollback): upgrade/rollback rehearsal checks pins, SBOM/license, branding, migration order, cold startup, seams and blocks upgrade on failure

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t18b/run_t18b_tests.py
```

Full T18/G3 acceptance remains BLOCKED until E08.4 second-client deployment, E08.2 real connector evidence, completed runbooks and independent owner review exist. This report contains only synthetic structural evidence.
