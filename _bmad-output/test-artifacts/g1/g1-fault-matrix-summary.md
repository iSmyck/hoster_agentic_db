# G1 API Fault-Matrix Synthetic Evidence

- **Generated:** 2026-11-12T11:52:30.004218+00:00
- **Environment:** synthetic_stub_gitlab
- **Command:** `uv run python _bmad-output/test-artifacts/g1/run_g1_fault_matrix.py`

## Scope

This report covers the synthetic closure of G1 API fault-matrix gates 
A05–A10 / A27–A30 plus concurrency/idempotency scenarios. 
It exercises invalid state transitions, actor mismatches, self-approval, 
idempotency violations, concurrent decision races, malformed payloads, 
reject/cancel/supersede semantics, and merge recovery barriers against 
the GO FastAPI TestClient with an in-memory stub GitLab adapter.

Live GitLab/PostgreSQL acceptance is **not** covered here; it remains 
optional and requires ``G1_ALLOW_DESTRUCTIVE_RESET=1``.

## Counts

- PASS: 20
- FAIL: 0
- TOTAL: 20

## Checks

| ID | Status | Expected | Actual |
|---|---|---|---|
| TestFaultMatrixInvalidStateTransitions.test_merge_before_decision_rejected | PASS | test passes | passed |
| TestFaultMatrixInvalidStateTransitions.test_merge_after_rejected_decision_rejected | PASS | test passes | passed |
| TestFaultMatrixActorMismatch.test_decision_actor_spoofing_rejected | PASS | test passes | passed |
| TestFaultMatrixActorMismatch.test_proposal_author_binding_rejects_spoofed_author | PASS | test passes | passed |
| TestFaultMatrixSelfApproval.test_author_cannot_accept_own_proposal | PASS | test passes | passed |
| TestFaultMatrixIdempotency.test_proposal_idempotency_key_reused_with_different_sha | PASS | test passes | passed |
| TestFaultMatrixIdempotency.test_decision_idempotency_key_reused_with_different_action | PASS | test passes | passed |
| TestFaultMatrixConcurrentDecisions.test_second_decision_for_same_proposal_rejected | PASS | test passes | passed |
| TestFaultMatrixConcurrentDecisions.test_second_decision_idempotent_when_identical_key | PASS | test passes | passed |
| TestFaultMatrixMalformedPayload.test_invalid_proposal_sha_returns_422 | PASS | test passes | passed |
| TestFaultMatrixMalformedPayload.test_short_proposal_sha_returns_422 | PASS | test passes | passed |
| TestFaultMatrixRejectDecision.test_rejected_decision_persisted_and_blocks_merge | PASS | test passes | passed |
| TestFaultMatrixCancelSupersede.test_supersede_rejected_with_accepted_and_merge | PASS | test passes | passed |
| TestFaultMatrixCancelSupersede.test_supersede_wrong_prior_decision_rejected | PASS | test passes | passed |
| TestFaultMatrixCancelSupersede.test_supersede_without_prior_decision_rejected | PASS | test passes | passed |
| TestFaultMatrixCancelSupersede.test_supersede_already_merged_proposal_rejected | PASS | test passes | passed |
| TestFaultMatrixConcurrentMergeBarrier.test_recovery_required_blocks_new_merge_on_same_target | PASS | test passes | passed |
| TestFaultMatrixConcurrentMergeBarrier.test_base_mismatch_blocks_merge | PASS | test passes | passed |
| TestFaultMatrixErrorShape.test_domain_error_includes_code_message_request_id_retryable | PASS | test passes | passed |
| TestFaultMatrixErrorShape.test_adapter_error_includes_unified_shape | PASS | test passes | passed |

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/g1/run_g1_fault_matrix.py
```
