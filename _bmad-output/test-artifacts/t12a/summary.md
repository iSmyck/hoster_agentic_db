# T12a Deterministic Dry-Run Import and Admission Gates Evidence Summary

- **Generated:** 2026-11-08T23:41:39.751763+00:00
- **Contracts version:** front-matter-v2/source-origin-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 12
- FAIL (expected): 24
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 40

## Top findings

### FAIL (expected)
- `deterministic_manifest.changed_input_new_manifest.rejected` (deterministic_manifest): non-deterministic or mutated manifest detected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `deterministic_manifest.changed_config_new_manifest.rejected` (deterministic_manifest): non-deterministic or mutated manifest detected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `admission_gates.missing_stable_owner.rejected` (admission_gates): admission gate rejected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `admission_gates.incomplete_data_barrier.rejected` (admission_gates): admission gate rejected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `admission_gates.pii_requires_disposition.rejected` (admission_gates): admission gate rejected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `admission_gates.critical_media_blocked.rejected` (admission_gates): admission gate rejected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `admission_gates.handwritten_media_blocked.rejected` (admission_gates): admission gate rejected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `path_to_id_mapping.nfd_path_rejected.rejected` (path_to_id_mapping): invalid path mapping rejected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `path_to_id_mapping.absolute_path_rejected.rejected` (path_to_id_mapping): invalid path mapping rejected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `path_to_id_mapping.source_id_lowercase_rewrite_rejected.rejected` (path_to_id_mapping): invalid path mapping rejected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.traversal_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.symlink_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.ambiguous_path_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.executable_html_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.executable_mdx_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.secret_in_content_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.invalid_utf8_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.oversized_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.decompression_bomb_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `security_blockers.mutable_unhashed_attachment_blocked.blocked` (security_blockers): security blocker fired; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `zero_canonical_writes.any_canonical_write_rejected.rejected` (zero_canonical_writes): canonical side effect detected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `zero_canonical_writes.branch_created_rejected.rejected` (zero_canonical_writes): canonical side effect detected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `zero_canonical_writes.mr_created_rejected.rejected` (zero_canonical_writes): canonical side effect detected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`
- `zero_canonical_writes.active_index_pointer_rejected.rejected` (zero_canonical_writes): canonical side effect detected; fixture `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_source_dry_run` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_import` (runtime): requires live sandbox and credentials
- `runtime.live_object_store_acl` (runtime): requires live sandbox and credentials
- `runtime.live_pii_scan` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.front_matter.valid` (schema): sample migrated front matter is schema valid
- `schema.source_origin.valid` (schema): sample source origin is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `deterministic_manifest.same_source_config_same_manifest.deterministic` (deterministic_manifest): same source/config replay produces identical manifest SHA
- `admission_gates.stable_owner_and_barrier_complete.admitted` (admission_gates): stable owner, complete data barrier, no uncleared PII and no unverified critical media
- `admission_gates.pii_dispositioned_allowed.admitted` (admission_gates): stable owner, complete data barrier, no uncleared PII and no unverified critical media
- `path_to_id_mapping.stable_path_to_uuid.valid` (path_to_id_mapping): repository-relative NFC paths map to stable IDs and preserve source ID case
- `path_to_id_mapping.source_id_case_preserved.valid` (path_to_id_mapping): repository-relative NFC paths map to stable IDs and preserve source ID case

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t12a/run_t12a_tests.py
```

Real source/GitLab/object-store/IdP checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
