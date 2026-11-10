# Code Review: T05a/T05b/T06 proposal/decision/merge enforcement harnesses

**Reviewed by:** Amelia (Senior Software Engineer)  
**Date:** 2026-11-10  
**Scope:** `_bmad-output/test-artifacts/t05a/`, `t05b/`, `t06/`

## Summary

All three harnesses run cleanly on synthetic fixtures:

- T05a: 11 PASS / 9 FAIL_EXPECTED / 4 BLOCKED
- T05b: 8 PASS / 9 FAIL_EXPECTED / 5 BLOCKED
- T06: 5 PASS / 9 FAIL_EXPECTED / 5 BLOCKED

No unexpected FAILs. Expected-negative cases correctly reject invalid proposal/decision/enforcement states. Live GitLab/GO checks remain BLOCKED as designed.

## Findings

### Blocking / Must-fix

_None._

### High

1. **Synthetic fixtures do not exercise the real GitLab/GO adapter**  
   This is by design for T05/T06, but the gap between synthetic merge-proof validation and actual `go-merge-service` behavior is large. The live integration stories in sprint-status (`runtime.live_gitlab_*`) must close before acceptance.

### Medium

2. **Duplicate scenario classification pattern**  
   Each harness repeats the same `expected_negative` tagging logic. A shared base validator class in `harness_common.py` would reduce duplication.

3. **T05a/T05b/T06 do not validate against the actual service code**  
   The harnesses validate contract invariants, not the `src/git-orchestrator/` implementation. Ensure epic-10/I06 and epic-4/T07b also have passing tests that exercise the real service paths.

### Low

4. **Hard-coded actor names in fixtures**  
   `user-sales-1`, `ci-bot`, `go-merge-service` are repeated across YAML files. Centralizing a synthetic identity catalog would make fixture maintenance easier.

## Decision

- **T05a/T05b/T06:** Approve. Synthetic acceptance passes; expected-negative cases are correctly classified; live integration is correctly BLOCKED.
- No source-code changes required for these harnesses.

## Verification Commands

```bash
uv run python _bmad-output/test-artifacts/t05a/run_t05a_tests.py
uv run python _bmad-output/test-artifacts/t05b/run_t05b_tests.py
uv run python _bmad-output/test-artifacts/t06/run_t06_tests.py
```
