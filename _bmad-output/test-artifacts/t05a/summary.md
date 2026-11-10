# T05a Exact ProposalRecord and ProposalVersion Lifecycle Evidence Summary

- **Generated:** 2026-11-10T11:24:25.050540+00:00
- **Contracts version:** proposal-record-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 11
- FAIL (expected): 9
- FAIL (unexpected): 0
- BLOCKED: 4
- **Total:** 24

## Top findings

### FAIL (expected)
- `proposal_lifecycle.missing_base_sha.rejected` (proposal_lifecycle): rejected: missing ['base_sha']; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`
- `proposal_lifecycle.agent_missing_run_id.rejected` (proposal_lifecycle): rejected: missing ['run_id (required for agent actor)']; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`
- `proposal_lifecycle.base_equals_proposal_sha.rejected` (proposal_lifecycle): rejected: missing ['base_sha != proposal_sha']; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`
- `idempotency.same_key_different_payload.collision` (idempotency): key reused with different payload hash 2222222222222222222222222222222222222222222222222222222222222222; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`
- `archive_restore.archive_flag_without_archive.violation` (archive_restore): archive flag and archive field mismatch detected; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`
- `archive_restore.active_document_with_archive_object.violation` (archive_restore): archive flag and archive field mismatch detected; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`
- `limits.evidence_count_exceeded.limit_exceeded` (limits): limit exceeded: ['evidence_count'], writes=0; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`
- `limits.rationale_too_long.limit_exceeded` (limits): limit exceeded: ['rationale_length'], writes=0; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`
- `limits.idempotency_key_too_long.limit_exceeded` (limits): limit exceeded: ['idempotency_key_length'], writes=0; fixture `_bmad-output/test-artifacts/t05a/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_gitlab_proposal_branch` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_proposal_version_cas` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_idempotency_registry` (runtime): requires live sandbox and credentials
- `runtime.live_gitlab_archive_restore` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.proposal_record.valid` (schema): sample proposal record is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `proposal_lifecycle.valid_human_proposal.valid` (proposal_lifecycle): new ProposalVersion created with exact base/proposal SHA
- `proposal_lifecycle.valid_agent_proposal.valid` (proposal_lifecycle): new ProposalVersion created with exact base/proposal SHA
- `proposal_lifecycle.version_evolution.valid` (proposal_lifecycle): new ProposalVersion created with exact base/proposal SHA
- `idempotency.same_key_same_payload.replay` (idempotency): same key + same payload returns existing ProposalVersion, no duplicate
- `archive_restore.archived_document.invariant` (archive_restore): archived=true iff archive field present; restore creates new reviewed version
- `archive_restore.restore_creates_reviewed_version.invariant` (archive_restore): archived=true iff archive field present; restore creates new reviewed version

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t05a/run_t05a_tests.py
```

Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
