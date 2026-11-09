# T18a Repeatable Config-Only Dedicated Deployment Evidence Summary

- **Generated:** 2026-11-09T00:01:34.191209+00:00
- **Contracts version:** dedicated-deployment-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 12
- FAIL (expected): 14
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 30

## Top findings

### FAIL (expected)
- `resource_isolation.shared_database_rejected.rejected` (resource_isolation): resource isolation problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `resource_isolation.cross_client_read_not_blocked_rejected.rejected` (resource_isolation): resource isolation problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `config_only_delivery.code_edit_rejected.rejected` (config_only_delivery): config-only delivery problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `config_only_delivery.client_branch_rejected.rejected` (config_only_delivery): config-only delivery problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `migration_ownership.runtime_ddl_rejected.rejected` (migration_ownership): migration ownership problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `migration_ownership.cross_schema_write_rejected.rejected` (migration_ownership): migration ownership problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `migration_ownership.empty_db_as_proof_rejected.rejected` (migration_ownership): migration ownership problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `cold_startup.unapproved_download_rejected.rejected` (cold_startup): cold startup problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `cold_startup.unapproved_fallback_rejected.rejected` (cold_startup): cold startup problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `cold_startup.missing_offline_assets_rejected.rejected` (cold_startup): cold startup problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `credential_egress_separation.merge_credential_leaked_rejected.rejected` (credential_egress_separation): credential/egress problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `credential_egress_separation.open_default_egress_rejected.rejected` (credential_egress_separation): credential/egress problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `credential_egress_separation.unapproved_route_used_rejected.rejected` (credential_egress_separation): credential/egress problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`
- `readiness_states.preflight_masked_as_published_rejected.rejected` (readiness_states): readiness state problem detected; fixture `_bmad-output/test-artifacts/t18a/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_second_client_environment` (runtime): requires owner-authorized second-client infrastructure
- `runtime.live_object_store` (runtime): requires owner-authorized second-client infrastructure
- `runtime.live_ci_runner` (runtime): requires owner-authorized second-client infrastructure
- `runtime.live_network_perimeter` (runtime): requires owner-authorized second-client infrastructure

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `resource_isolation.second_client_fully_isolated.valid` (resource_isolation): second client has separate repositories, config, DB, index, objects, secrets, backups, mirrors, perimeter and egress
- `resource_isolation.cross_client_read_blocked.valid` (resource_isolation): second client has separate repositories, config, DB, index, objects, secrets, backups, mirrors, perimeter and egress
- `config_only_delivery.config_only_second_client.valid` (config_only_delivery): second client deployed from same pinned core plus config/adapters without code edits or client branch
- `migration_ownership.runtime_non_ddl_migrations_disabled.valid` (migration_ownership): runtime workers have migrations disabled and non-DDL roles; only authorized migrator verifies heads before traffic
- `cold_startup.cold_startup_ready.valid` (cold_startup): cold startup verifies offline assets, SBOM and config; no unapproved download or fallback
- `credential_egress_separation.credentials_separated_egress_closed.valid` (credential_egress_separation): proposal/merge, connector, CI/index and retrieval credentials separated; default egress closed except approved routes
- `readiness_states.published_state.valid` (readiness_states): readiness distinguishes published, indexed and unavailable; inactive preflight not masked

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t18a/run_t18a_tests.py
```

Real second-client environment, object store, CI and network perimeter remain BLOCKED pending owner authorization. This report contains only synthetic config/isolation evidence; it does not claim production dedicated deployment PASS.
