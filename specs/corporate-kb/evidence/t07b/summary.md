# T07b DocOps Review Projections, Correction Tasks and UX Telemetry Evidence Summary

- **Generated:** 2026-11-08T22:51:00.607935+00:00
- **Contracts version:** docops-correction-task-v1
- **Baseline commit:** 152b00ff6aaa7b95c7b958d822bf54e8a54d1650
- **Spec baseline commit:** d2c0d072a757808ea891fbf6414f00147679f7a7
- **Environment:** synthetic_local_no_gitlab
- **Sensitive data present:** False

## Counts

- PASS: 13
- FAIL: 3
- BLOCKED: 3
- **Total:** 19

## Top findings

### FAIL
- `review_projection.mismatched_canonical.invalid` (review_projection): rejected; fixture `_bmad-output/test-artifacts/t07b/fixtures/scenarios.yaml`
- `telemetry.raw_document_leak.rejected` (telemetry): rejected; fixture `_bmad-output/test-artifacts/t07b/fixtures/scenarios.yaml`
- `telemetry.raw_query_leak.rejected` (telemetry): rejected; fixture `_bmad-output/test-artifacts/t07b/fixtures/scenarios.yaml`

### BLOCKED
- `runtime.live_docops_review_projection` (runtime): requires live sandbox and credentials
- `runtime.live_docops_correction_task_lifecycle` (runtime): requires live sandbox and credentials
- `runtime.live_docops_telemetry_redaction` (runtime): requires live sandbox and credentials

### PASS (sample)
- `harness.fixture_loaded` (harness): synthetic fixtures load
- `schema.correction_task.valid` (schema): sample correction task is schema valid
- `schema.review_metadata.valid` (schema): sample review metadata is schema valid
- `schema.regex_compile` (schema): all schema regex patterns compile
- `schema.refs_resolve` (schema): all schema $ref resolve
- `review_projection.valid_due_projection.valid` (review_projection): DocOps review metadata projection matches canonical revision and valid_until rules
- `review_projection.removed_projection.valid` (review_projection): DocOps review metadata projection matches canonical revision and valid_until rules
- `correction_task.create_open.valid` (correction_task): correction-task lifecycle transition is valid with exact revision SHA
- `correction_task.open_to_in_review.valid` (correction_task): correction-task lifecycle transition is valid with exact revision SHA
- `correction_task.in_review_to_resolved.valid` (correction_task): correction-task lifecycle transition is valid with exact revision SHA

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/t07b/run_t07b_tests.py
```

Real GitLab/GO/integration checks remain BLOCKED until their sandboxes and credentials exist. This report contains only synthetic structural evidence; it does not claim production integration PASS.
