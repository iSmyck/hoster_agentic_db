# T13b Mirror/Metadata Backup, Rebuild and Conservative Clean Restore Evidence Summary

- **Generated:** 2026-11-08T23:41:40.869325+00:00
- **Contracts version:** docops-correction-task-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 15
- FAIL (expected): 22
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 41

## Top findings

### FAIL (expected)
- `git_mirror_refs_objects.missing_protected_tag_rejected.incomplete` (git_mirror_refs_objects): mirror incomplete; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `git_mirror_refs_objects.missing_object_rejected.incomplete` (git_mirror_refs_objects): mirror incomplete; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `metadata_backup.missing_mr_metadata_rejected.inconsistent` (metadata_backup): metadata backup problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `metadata_backup.inconsistent_metadata_rejected.inconsistent` (metadata_backup): metadata backup problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `object_backup.mutable_object_rejected.rejected` (object_backup): object backup problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `object_backup.hash_mismatch_object_rejected.rejected` (object_backup): object backup problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `secrets_separation.secrets_in_ordinary_backup_rejected.rejected` (secrets_separation): secrets separation problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `secrets_separation.missing_secrets_recovery_policy_rejected.rejected` (secrets_separation): secrets separation problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `kb_authz_rebuild.inherited_grants_not_truth.rejected` (kb_authz_rebuild): kb_authz rebuild problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `kb_authz_rebuild.stale_idp_rejected.rejected` (kb_authz_rebuild): kb_authz rebuild problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `kb_ops_rebuild.no_global_freeze_rejected.rejected` (kb_ops_rebuild): kb_ops rebuild problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `kb_ops_rebuild.unknown_outcomes_auto_cleared_rejected.rejected` (kb_ops_rebuild): kb_ops rebuild problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `kb_index_rebuild.canonical_git_mutation_rejected.rejected` (kb_index_rebuild): kb_index rebuild problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `kb_index_rebuild.active_pointer_as_truth_rejected.rejected` (kb_index_rebuild): kb_index rebuild problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `correction_task_backup_reconciliation.event_sequence_mismatch_rejected.rejected` (correction_task_backup_reconciliation): correction-task reconciliation problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `correction_task_backup_reconciliation.fabricated_canonical_write_rejected.rejected` (correction_task_backup_reconciliation): correction-task reconciliation problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `correction_task_backup_reconciliation.deleted_canonical_write_rejected.rejected` (correction_task_backup_reconciliation): correction-task reconciliation problem detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `clean_isolated_instance.inherited_active_pointer_rejected.rejected` (clean_isolated_instance): inherited state detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `clean_isolated_instance.inherited_operational_rows_rejected.rejected` (clean_isolated_instance): inherited state detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `conservative_rebuild.file_dump_existence_not_pass.rejected` (conservative_rebuild): rebuild optimism detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `conservative_rebuild.missing_assets_block_ready.rejected` (conservative_rebuild): rebuild optimism detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`
- `conservative_rebuild.missing_grants_block_ready.rejected` (conservative_rebuild): rebuild optimism detected; fixture `_bmad-output/test-artifacts/t13b/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_gitlab_mirror` (runtime): requires live sandbox and credentials
- `runtime.live_postgres_backup_restore` (runtime): requires live sandbox and credentials
- `runtime.live_object_store_backup` (runtime): requires live sandbox and credentials
- `runtime.live_idp_rebuild` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.correction_task_open.valid` (schema): sample open correction task is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `git_mirror_refs_objects.complete_mirror_with_protected_tags.complete` (git_mirror_refs_objects): Git mirror contains all refs/objects and protected decision/cutover tags with exact full SHAs
- `metadata_backup.gitlab_metadata_captured.complete` (metadata_backup): GitLab MR/note/audit metadata captured and consistent
- `object_backup.immutable_object_versions_match.valid` (object_backup): immutable/versioned objects match assets manifest hashes
- `secrets_separation.no_secrets_in_ordinary_backup.separate` (secrets_separation): secrets stored only under separately controlled recovery policy; ordinary backup has no secrets
- `kb_authz_rebuild.rebuild_from_git_policy_and_fresh_idp.valid` (kb_authz_rebuild): kb_authz rebuilt from Git policy plus fresh IdP data with no inherited active grants
- `kb_ops_rebuild.rebuild_under_global_merge_freeze_with_barriers.valid` (kb_ops_rebuild): Git-derived kb_ops rebuilt under global merge freeze with conservative per-target barriers

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t13b/run_t13b_tests.py
```

Real backup/restore/rebuild on GitLab/PostgreSQL/object-store/IdP remains BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
