# T15 Safe Source Registry, Three-Way Updates and Durable Cursors Evidence Summary

- **Generated:** 2026-11-10T11:25:42.071431+00:00
- **Contracts version:** source-registry-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 23
- FAIL (expected): 10
- FAIL (unexpected): 0
- BLOCKED: 3
- **Total:** 36

## Top findings

### FAIL (expected)
- `source_registry.migrated_missing_origin_rejected.rejected` (source_registry): registry entry problem detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `source_registry.source_managed_origin_mode_mismatch_rejected.rejected` (source_registry): registry entry problem detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `cursor_durability.merged_without_proposal_durability_rejected.rejected` (cursor_durability): cursor durability problem detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `cursor_durability.proposed_without_durable_mr_rejected.rejected` (cursor_durability): cursor durability problem detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `same_hash_noop.same_hash_duplicate_proposal_rejected.rejected` (same_hash_noop): duplicate proposal detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `one_outstanding_proposal.second_outstanding_proposal_rejected.rejected` (one_outstanding_proposal): multiple outstanding proposals detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `ownership_modes.source_managed_local_edit_rejected.rejected` (ownership_modes): ownership mode violation detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `ownership_modes.live_operational_write_rejected.rejected` (ownership_modes): ownership mode violation detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `source_deletion_tombstone.silent_deletion_rejected.rejected` (source_deletion_tombstone): silent deletion detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`
- `crash_replay.fabricated_replay_rejected.rejected` (crash_replay): replay problem detected; fixture `_bmad-output/test-artifacts/t15/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_source_connector` (runtime): requires live source sandbox and credentials
- `runtime.live_gitlab_merge` (runtime): requires live source sandbox and credentials
- `runtime.live_object_store_cursor` (runtime): requires live source sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.proposal_record.valid` (schema): sample source proposal record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `source_registry.migrated_with_origin.valid` (source_registry): source registry records stable binding with mode-appropriate origin
- `source_registry.source_managed_with_origin.valid` (source_registry): source registry records stable binding with mode-appropriate origin
- `source_registry.curated_without_origin.valid` (source_registry): source registry records stable binding with mode-appropriate origin
- `source_registry.live_operational_read_only.valid` (source_registry): source registry records stable binding with mode-appropriate origin
- `cursor_durability.seen_after_durable_metadata.valid` (cursor_durability): cursor advances only after durable evidence
- `cursor_durability.proposed_after_durable_mr_and_record.valid` (cursor_durability): cursor advances only after durable evidence

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t15/run_t15_tests.py
```

Real source connector integration remains BLOCKED pending owner selection, sandbox and credentials. This report contains only synthetic structural evidence; it does not claim production source integration PASS.
