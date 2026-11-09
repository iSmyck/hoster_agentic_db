# T16 One Owner-Selected Real Source Connector Evidence Summary

- **Generated:** 2026-11-09T00:01:33.448567+00:00
- **Contracts version:** connector-design-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 14
- FAIL (expected): 14
- FAIL (unexpected): 0
- BLOCKED: 5
- **Total:** 33

## Top findings

### FAIL (expected)
- `feasibility_inventory.missing_rate_limits_rejected.rejected` (feasibility_inventory): inventory problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `feasibility_inventory.unselected_connector_claimed_ready_rejected.rejected` (feasibility_inventory): inventory problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `connector_identity_provenance.missing_stable_remote_id_rejected.rejected` (connector_identity_provenance): identity/provenance problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `connector_identity_provenance.wrong_space_mapping_rejected.rejected` (connector_identity_provenance): identity/provenance problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `connector_capabilities.auto_merge_capability_rejected.rejected` (connector_capabilities): forbidden capability detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `connector_capabilities.index_pointer_capability_rejected.rejected` (connector_capabilities): forbidden capability detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `access_revocation.hint_treated_as_authority_rejected.rejected` (access_revocation): revocation handling problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `deletion_retry_dedupe.duplicate_creates_second_proposal_rejected.rejected` (deletion_retry_dedupe): deletion/retry/dedupe problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `deletion_retry_dedupe.poison_missing_dead_letter_rejected.rejected` (deletion_retry_dedupe): deletion/retry/dedupe problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `attachments_object_acl.mutable_url_rejected.rejected` (attachments_object_acl): attachment/object problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `attachments_object_acl.missing_object_rejected.rejected` (attachments_object_acl): attachment/object problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `attachments_object_acl.object_acl_fail_rejected.rejected` (attachments_object_acl): attachment/object problem detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `secrets_hygiene.token_in_log_rejected.rejected` (secrets_hygiene): secret leak detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`
- `secrets_hygiene.signed_url_in_document_rejected.rejected` (secrets_hygiene): secret leak detected; fixture `_bmad-output/test-artifacts/t16/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_sharepoint_connector` (runtime): requires owner-selected source, sandbox and credentials
- `runtime.live_bitrix_connector` (runtime): requires owner-selected source, sandbox and credentials
- `runtime.live_kayako_connector` (runtime): requires owner-selected source, sandbox and credentials
- `runtime.live_source_sandbox` (runtime): requires owner-selected source, sandbox and credentials
- `runtime.live_object_store_acl` (runtime): requires owner-selected source, sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.proposal_record.valid` (schema): sample connector proposal record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `feasibility_inventory.sharepoint_selected_inventory_complete.complete` (feasibility_inventory): selected source inventory complete; other connectors not claimed ready
- `connector_identity_provenance.stable_identity_and_provenance.valid` (connector_identity_provenance): connector preserves stable remote ID, immutable version/hash, source owner and provenance; maps to configured Space
- `connector_capabilities.proposal_only_no_forbidden.valid` (connector_capabilities): connector sends proposal-only requests to GO and has no forbidden capabilities
- `access_revocation.healthy_access.fail_closed` (access_revocation): revoked credentials, changed ACL hints or revoked group membership fail closed; hints treated as hints only
- `access_revocation.revoked_credentials_fail_closed.fail_closed` (access_revocation): revoked credentials, changed ACL hints or revoked group membership fail closed; hints treated as hints only
- `access_revocation.acl_hint_not_authority.fail_closed` (access_revocation): revoked credentials, changed ACL hints or revoked group membership fail closed; hints treated as hints only

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t16/run_t16_tests.py
```

Real source connector integration remains BLOCKED pending owner selection of SharePoint/Bitrix24/Kayako, real sandbox and credentials. This report contains only synthetic design-readiness evidence; it does not claim production connector PASS.
