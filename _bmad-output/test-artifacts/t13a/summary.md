# T13a Complete Portable Export with Exact Refs and Closure Evidence Summary

- **Generated:** 2026-11-10T11:25:33.411615+00:00
- **Contracts version:** export-manifest-v2
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 12
- FAIL (expected): 13
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 29

## Top findings

### FAIL (expected)
- `export_authorization.unauthorized_batch_rejected.rejected` (export_authorization): unauthorized batch detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `export_authorization.all_batches_require_authorization.rejected` (export_authorization): unauthorized batch detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `git_clone_refs.short_sha_rejected.rejected` (git_clone_refs): ref problem detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `git_clone_refs.missing_ref_rejected.rejected` (git_clone_refs): ref problem detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `decisions_manifest.note_record_hash_mismatch_rejected.rejected` (decisions_manifest): decision integrity problem detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `decisions_manifest.fabricated_merge_rejected.rejected` (decisions_manifest): decision integrity problem detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `assets_manifest.hash_mismatch_rejected.rejected` (assets_manifest): asset problem detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `assets_manifest.mutable_url_rejected.rejected` (assets_manifest): asset problem detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `assets_manifest.missing_asset_rejected.rejected` (assets_manifest): asset problem detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `policy_bundle.missing_policy_revision_rejected.rejected` (policy_bundle): policy bundle incomplete; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `grants_mapping.secrets_in_grants_rejected.rejected` (grants_mapping): grants mapping problem detected; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `closure.incomplete_assets_block_complete.incomplete` (closure): closure incomplete; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`
- `closure.unauthorized_batch_block_complete.incomplete` (closure): closure incomplete; fixture `_bmad-output/test-artifacts/t13a/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_gitlab_export` (runtime): requires live sandbox and credentials
- `runtime.live_object_store_export` (runtime): requires live sandbox and credentials
- `runtime.live_decision_note_tag_export` (runtime): requires live sandbox and credentials
- `runtime.live_grants_export` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.export_manifest.valid` (schema): sample export manifest is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `export_authorization.authorized_batches_proceed.authorized` (export_authorization): every export batch passes fresh Space+history authorization
- `git_clone_refs.explicit_full_shas_and_refs.explicit` (git_clone_refs): Git clone includes explicit full object SHAs and refs; protected decision tags marked protected
- `decisions_manifest.accepted_decision_with_exact_refs.valid` (decisions_manifest): decisions manifest has exact decision_id, proposal_sha, record_sha256, note/tag linkage and correct merge evidence
- `decisions_manifest.rejected_decision_with_closure.valid` (decisions_manifest): decisions manifest has exact decision_id, proposal_sha, record_sha256, note/tag linkage and correct merge evidence
- `assets_manifest.immutable_assets_hash_verified.valid` (assets_manifest): assets manifest contains immutable attachments with verified hashes
- `policy_bundle.complete_policy_closure.complete` (policy_bundle): policy bundle includes access/approval revision SHAs and content/grants hashes

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t13a/run_t13a_tests.py
```

Real GitLab/object-store/IdP checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
