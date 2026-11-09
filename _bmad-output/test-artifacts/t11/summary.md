# T11 Approved hoster.ai Studio Inference Lifecycle Evidence Summary

- **Generated:** 2026-11-08T23:53:07.524208+00:00
- **Contracts version:** hoster-inference-lifecycle-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 17
- FAIL (expected): 12
- FAIL (unexpected): 0
- BLOCKED: 5
- **Total:** 34

## Top findings

### FAIL (expected)
- `route_inventory.missing_dimension_rejected.rejected` (route_inventory): route inventory problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `route_inventory.unapproved_connection_rejected.rejected` (route_inventory): route inventory problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `streaming_tool_calls.authorization_missing_before_dispatch.rejected` (streaming_tool_calls): streaming/tool-call problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `streaming_tool_calls.partial_content_executed.rejected` (streaming_tool_calls): streaming/tool-call problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `malformed_unsafe_inputs.prompt_injection_merge_rejected.rejected` (malformed_unsafe_inputs): unsafe input detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `malformed_unsafe_inputs.privilege_expansion_rejected.rejected` (malformed_unsafe_inputs): unsafe input detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `retry_cancel_disconnect.retry_changed_payload_rejected.rejected` (retry_cancel_disconnect): retry/event problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `egress_perimeter.unapproved_endpoint_rejected.rejected` (egress_perimeter): egress/perimeter problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `egress_perimeter.pii_leaves_perimeter_rejected.rejected` (egress_perimeter): egress/perimeter problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `egress_perimeter.offline_unapproved_asset_rejected.rejected` (egress_perimeter): egress/perimeter problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `lifecycle_metrics.hidden_fallback_detected.rejected` (lifecycle_metrics): metrics problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`
- `lifecycle_metrics.missing_cost_attribution.rejected` (lifecycle_metrics): metrics problem detected; fixture `_bmad-output/test-artifacts/t11/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_hoster_chat_inference` (runtime): requires live hoster.ai sandbox and credentials
- `runtime.live_hoster_embeddings_inference` (runtime): requires live hoster.ai sandbox and credentials
- `runtime.live_hoster_vision_inference` (runtime): requires live hoster.ai sandbox and credentials
- `runtime.live_streaming_tool_call` (runtime): requires live hoster.ai sandbox and credentials
- `runtime.live_revocation_closes_stream` (runtime): requires live hoster.ai sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.proposal_record.valid` (schema): sample proposal record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `route_inventory.chat_route_complete.complete` (route_inventory): route records approved connection, model/version, data profile, capabilities and index-profile linkage
- `route_inventory.embeddings_route_complete.complete` (route_inventory): route records approved connection, model/version, data profile, capabilities and index-profile linkage
- `streaming_tool_calls.sequential_tool_calls_correlated.safe` (streaming_tool_calls): streaming tool calls preserve correlation/citations, assemble typed args and validate authz before dispatch
- `streaming_tool_calls.parallel_tool_calls_both_authorized.safe` (streaming_tool_calls): streaming tool calls preserve correlation/citations, assemble typed args and validate authz before dispatch
- `malformed_unsafe_inputs.malformed_json_rejected.rejected` (malformed_unsafe_inputs): unsafe input rejected with VALIDATION_ERROR
- `malformed_unsafe_inputs.unknown_fields_rejected.rejected` (malformed_unsafe_inputs): unsafe input rejected with VALIDATION_ERROR

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t11/run_t11_tests.py
```

Real hoster.ai studio endpoint, model inventory, credentials and egress remain BLOCKED. This report contains only synthetic structural evidence; it does not claim production inference PASS.
