# T09 Restricted Single-Page Agent Proposal Tools Evidence Summary

- **Generated:** 2026-11-08T22:51:00.260411+00:00
- **Contracts version:** agent-tools-v2
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 11
- FAIL: 10
- BLOCKED: 4
- **Total:** 25

## Top findings

### FAIL
- `propose_create.create_with_origin_rejected.rejected` (propose_create): rejected; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `propose_create.create_with_archive_rejected.rejected` (propose_create): rejected; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `propose_edit.whole_document_replacement_rejected.rejected` (propose_edit): rejected; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `propose_edit.front_matter_change_rejected.rejected` (propose_edit): rejected; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `propose_edit.ambiguous_patch_rejected.rejected` (propose_edit): rejected; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `forbidden.merge_forbidden.merge` (forbidden_capabilities): merge is forbidden; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `forbidden.accept_forbidden.accept` (forbidden_capabilities): accept is forbidden; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `forbidden.bulk_forbidden.bulk` (forbidden_capabilities): bulk is forbidden; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `forbidden.subtree_forbidden.subtree` (forbidden_capabilities): subtree is forbidden; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`
- `prompt_injection.injection_attempting_role_change.authority_preserved` (prompt_injection): rejected; fixture `_bmad-output/test-artifacts/t09/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_agent_propose_create` (runtime): requires live sandbox and credentials
- `runtime.live_agent_anchored_patch` (runtime): requires live sandbox and credentials
- `runtime.live_agent_forbidden_capabilities` (runtime): requires live sandbox and credentials
- `runtime.live_agent_prompt_injection` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.proposal_record.valid` (schema): sample agent proposal record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `propose_create.valid_single_page_body_create.valid` (propose_create): single-page body-only create proposal accepted
- `propose_edit.valid_agent_anchored_patch.valid` (propose_edit): AgentAnchoredPatchChange with required body section accepted
- `forbidden.read_allowed.read` (forbidden_capabilities): capability read is allowed
- `forbidden.search_allowed.search` (forbidden_capabilities): capability search is allowed
- `forbidden.propose_allowed.propose` (forbidden_capabilities): capability propose is allowed
- `prompt_injection.rationale_injection_no_authority_change.no_authority_change` (prompt_injection): injected rationale/evidence does not change actor, scope, tools, or policy

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t09/run_t09_tests.py
```

Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
