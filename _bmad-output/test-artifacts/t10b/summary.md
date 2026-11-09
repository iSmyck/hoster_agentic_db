# T10b Published Retrieval, Search Cursors and Monotonic Publication Lifecycle Evidence Summary

- **Generated:** 2026-11-08T23:25:35.089491+00:00
- **Contracts version:** index-snapshot-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 17
- FAIL (expected): 13
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 34

## Top findings

### FAIL (expected)
- `publication_lifecycle.reused_snapshot_id_rejected.rejected` (publication_lifecycle): rejected; fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `publication_lifecycle.preflight_activated_rejected.rejected` (publication_lifecycle): rejected; fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `publication_lifecycle.validation_not_repeated_rejected.rejected` (publication_lifecycle): rejected; fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `pointer_cas_fencing.cas_succeeds_but_rows_zero_rejected.rejected` (pointer_cas_fencing): stale writer rejected (INDEX_GENERATION_CONFLICT); fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `per_space_retrieval.stale_snapshot_rejected.rejected` (per_space_retrieval): stale/unauthorized content detected (STALE_INDEX_CANDIDATE); fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `per_space_retrieval.unauthorized_candidate_rejected.rejected` (per_space_retrieval): stale/unauthorized content detected (AUTHZ_GROUP_STALE); fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `per_space_retrieval.cross_space_leak_rejected.rejected` (per_space_retrieval): stale/unauthorized content detected (SECURITY_REJECTED); fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `per_space_retrieval.missing_citation_fields_rejected.rejected` (per_space_retrieval): stale/unauthorized content detected (SECURITY_REJECTED); fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `cursor_binding.missing_actor_epoch_rejected.rejected` (cursor_binding): stale/incomplete cursor rejected; fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `cursor_binding.stale_policy_revision_rejected.rejected` (cursor_binding): stale/incomplete cursor rejected; fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `cursor_binding.limit_exceeded_without_next_cursor_rejected.rejected` (cursor_binding): stale/incomplete cursor rejected; fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `index_not_ready.optimistic_success_rejected.rejected` (index_not_ready): bad outcome detected; fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`
- `index_not_ready.silent_truncation_rejected.rejected` (index_not_ready): bad outcome detected; fixture `_bmad-output/test-artifacts/t10b/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_postgres_active_pointer` (runtime): requires live sandbox and credentials
- `runtime.live_retrieval_exact_semantic` (runtime): requires live sandbox and credentials
- `runtime.live_cursor_revocation_stream` (runtime): requires live sandbox and credentials
- `runtime.live_hoster_ai_inference` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.preflight.valid` (schema): sample preflight snapshot is schema valid
- `schema.published.valid` (schema): sample published active snapshot is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `publication_lifecycle.preflight_to_published_new_ids_same_sha.valid` (publication_lifecycle): published lifecycle creates new IDs with same SHA/closure/policy/hashes and repeats validation
- `pointer_cas_fencing.single_writer_cas_succeeds.valid` (pointer_cas_fencing): CAS/fencing pointer publication updates exactly one row for the single writer
- `pointer_cas_fencing.stale_fence_rejected.valid` (pointer_cas_fencing): CAS/fencing pointer publication updates exactly one row for the single writer
- `pointer_cas_fencing.old_generation_overwrite_rejected.valid` (pointer_cas_fencing): CAS/fencing pointer publication updates exactly one row for the single writer
- `pointer_cas_fencing.non_writer_publisher_rejected.valid` (pointer_cas_fencing): CAS/fencing pointer publication updates exactly one row for the single writer

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t10b/run_t10b_tests.py
```

Real GitLab/PostgreSQL/retrieval checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
