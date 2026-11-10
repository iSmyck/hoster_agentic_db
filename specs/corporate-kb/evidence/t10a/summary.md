# T10a Exact-SHA CI Index Build and Validated Preflight Artifact Evidence Summary

- **Generated:** 2026-11-10T11:25:13.576471+00:00
- **Contracts version:** index-snapshot-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 14
- FAIL (expected): 19
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 37

## Top findings

### FAIL (expected)
- `exact_sha_build.resolved_sha_mismatch.rejected` (exact_sha_build): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `exact_sha_build.ci_write_capability_rejected.rejected` (exact_sha_build): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `exact_sha_build.branch_hint_without_exact_sha.rejected` (exact_sha_build): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `preflight_artifact.activated_preflight_rejected.rejected` (preflight_artifact): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `preflight_artifact.cutover_sha_mismatch.rejected` (preflight_artifact): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `preflight_artifact.incremental_preflight_rejected.rejected` (preflight_artifact): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `index_snapshot_contract.incremental_missing_equivalence.rejected` (index_snapshot_contract): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `index_snapshot_contract.incremental_missing_inputs.rejected` (index_snapshot_contract): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `index_snapshot_contract.lexicographic_generation_ordering.rejected` (index_snapshot_contract): rejected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `eligible_content_exclusion.inbox_excluded.rejected` (eligible_content_exclusion): ineligible content detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `eligible_content_exclusion.template_excluded.rejected` (eligible_content_exclusion): ineligible content detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `eligible_content_exclusion.service_file_excluded.rejected` (eligible_content_exclusion): ineligible content detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `eligible_content_exclusion.archived_excluded.rejected` (eligible_content_exclusion): ineligible content detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `eligible_content_exclusion.deleted_excluded.rejected` (eligible_content_exclusion): ineligible content detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `eligible_content_exclusion.unverified_critical_media_excluded.rejected` (eligible_content_exclusion): ineligible content detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `eligible_content_exclusion.pending_branch_excluded.rejected` (eligible_content_exclusion): ineligible content detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `eligible_content_exclusion.rejected_branch_excluded.rejected` (eligible_content_exclusion): ineligible content detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `idempotent_rebuild.rebuild_changed_canonical_git.rejected` (idempotent_rebuild): non-idempotent behavior detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`
- `idempotent_rebuild.duplicate_created_active.rejected` (idempotent_rebuild): non-idempotent behavior detected; fixture `_bmad-output/test-artifacts/t10a/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_gitlab_exact_sha_build` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_ci_no_write` (runtime): requires live sandbox and credentials
- `runtime.live_postgres_kb_index_rebuild` (runtime): requires live sandbox and credentials
- `runtime.live_object_store_acl` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.preflight.valid` (schema): sample preflight snapshot is schema valid
- `schema.published.valid` (schema): sample published active snapshot is schema valid
- `schema.lexicographic_ordering.invalid` (schema): lexicographic generation ordering is rejected by schema
- `schema.incremental_no_evidence.invalid` (schema): incremental snapshot without equivalence_evidence is rejected by schema
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `exact_sha_build.webhook_hint_resolves_exact_sha.resolved` (exact_sha_build): CI resolves exact published main SHA via read-only credential
- `preflight_artifact.valid_inactive_preflight.inactive` (preflight_artifact): preflight artifact is inactive with snapshot_sha == cutover_sha and serving_allowed=false
- `index_snapshot_contract.valid_full_snapshot.valid` (index_snapshot_contract): snapshot contract has required SHAs, hashes, generation, profile and policy triple

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t10a/run_t10a_tests.py
```

Real GitLab/PostgreSQL/CI checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
