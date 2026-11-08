# T01 Contract Test Evidence Summary

- **Generated:** 2026-11-08T16:32:01.453517+00:00
- **Contracts version:** t01-contract-tests-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 50
- FAIL: 0
- BLOCKED: 65
- NOT_EXECUTED: 2
- **Total:** 117

## Top findings

### BLOCKED / DESIGN_NOT_EXECUTED
- `CF-01.search_fanout` (CF-01): requires live AuthzContext service and GitLab webhook/identity sandbox
- `CF-01.cursor_replay_stale` (CF-01): requires live AuthzContext service and GitLab webhook/identity sandbox
- `CF-01.access_policy_changed_rejection` (CF-01): requires live AuthzContext service and GitLab webhook/identity sandbox
- `CF-02.longest_prefix_assignment` (CF-02): longest-prefix rule selection requires active approval policy service
- `CF-03.replacement_semantics` (CF-03): archive replacement/descendant semantics require canonical document service
- `CF-04.live_operational_canonical_forbidden` (CF-04): canonical front matter live_operational rejection requires document service
- `CF-05.lowercase_semantic_rejected` (CF-05): source_id lowercase rewrite requires canonical source service for semantic validation
- `CF-06.review_scheduled_due_removed` (CF-06): requires live GO backend, GitLab MR sandbox and idempotency registry
- `CF-06.correction_create_resolve_cancel` (CF-06): requires live GO backend, GitLab MR sandbox and idempotency registry
- `CF-06.idempotency_and_cas` (CF-06): requires live GO backend, GitLab MR sandbox and idempotency registry
- `CF-06.mr_governance` (CF-06): requires live GO backend, GitLab MR sandbox and idempotency registry
- `CF-07.bounded_agent_forbidden_writes` (CF-07): requires running GO service and agent credential sandbox
- `CF-07.agent_propose_rejected` (CF-07): requires running GO service and agent credential sandbox
- `CF-08.dry_run_staging` (CF-08): requires connector credential sandbox and immutable binding registry
- `CF-08.post_cutover_proposal` (CF-08): requires connector credential sandbox and immutable binding registry
- `CF-08.pre_cutover_forbidden` (CF-08): requires connector credential sandbox and immutable binding registry
- `CF-08.cursor_binding_exact` (CF-08): requires connector credential sandbox and immutable binding registry
- `CF-09.path_body_id_mismatch_rejected` (CF-09): requires running GO API and mutation paths
- `CF-09.error_enum_coverage` (CF-09): requires running GO API and mutation paths
- `CF-09.tool_adapter_route` (CF-09): requires running GO API and mutation paths
- ... and 45 more BLOCKED checks

### PASS (sample)
- `harness.catalog_parse` (CF-30): t01-contract-tests.yaml parses
- `CF-30.json_schema_parse` (CF-30): all .schema.json parse
- `CF-30.yaml_parse.openapi.yaml` (CF-30): openapi.yaml parses
- `CF-30.yaml_parse.agent-tools.yaml` (CF-30): agent-tools.yaml parses
- `CF-30.yaml_parse.events.yaml` (CF-30): events.yaml parses
- `CF-30.yaml_parse.t01-contract-tests.yaml` (CF-30): t01-contract-tests.yaml parses
- `CF-30.schema_refs_resolve` (CF-30): all schema $ref resolve
- `CF-30.openapi_refs_resolve` (CF-30): all OpenAPI/agent-tools $ref resolve
- `CF-30.regex_compile` (CF-30): all regex patterns compile
- `CF-30.operationIds_unique` (CF-30): OpenAPI operationIds are unique

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t01/run_contract_tests.py
```

Real GitLab/IdP/CI/hoster.ai integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural/contract evidence; it does not claim production integration PASS.
