# Code Review: T04a/T04b harness schema-loading fix

**Reviewed by:** Amelia (Senior Software Engineer)  
**Date:** 2026-11-10  
**Scope:** `_bmad-output/test-artifacts/t0*/validators/schemas.py`  
**Trigger:** Synthetic harnesses for T04a/T04b were entirely BLOCKED on schema load (`Draft202012Validator` has no `detect` attribute).

## Summary

Fix replaces `default_specification=self.DRAFT` (`Draft202012Validator` class) with `default_specification=DRAFT202012` (`referencing.jsonschema` specification) in all early-harness schema validators. After the change:

- T01: 50 PASS / 65 BLOCKED
- T02: 104 PASS / 5 FAIL / 4 BLOCKED  
- T03a: 36 PASS / 6 BLOCKED
- T03b: 50 PASS / 5 BLOCKED
- T04a: 20 PASS / 6 BLOCKED
- T04b: 24 PASS / 5 BLOCKED

BLOCKED counts are expected live-integration gates. No unexpected FAILs introduced by this fix.

## Findings

### Blocking / Must-fix

_None._

### High

1. **T02 negative fixtures not marked expected-fail**  
   `bad-archived-no-archive.md`, `bad-unarchived-with-archive.md` and `malformed-heading.md` produce plain `FAIL` instead of `FAIL_EXPECTED`. The fixtures are intentionally invalid, so the harness should either expect failure or flip the assertion to "rejected".  
   **Action:** Either mark these cases `expected_negative: true` in the harness, or change the AC so that invalid fixtures are expected to be rejected.  
   **Owner:** T02 (already in review; out of scope for T04a/T04b).

### Medium

2. **Duplicated `SchemaValidator` across harnesses**  
   Six near-identical `SchemaValidator` classes exist (t01/t02/t03a/t03b/t04a/t04b). They differ only in docstrings and minor formatting. This is acceptable while each harness is self-contained, but increases maintenance cost when jsonschema/referencing APIs change.  
   **Action:** Consider promoting the class to `harness_common.py` and importing it. If retained as-is, add a unit test that imports each and verifies at least one schema loads.

3. **T04a/T04b still rely on `reporters` package copied per-harness**  
   Each harness has its own `reporters/` subtree. The fix had to be applied in `validators/schemas.py`, but the same duplication risk exists in reporter code.

### Low

4. **Type hint inconsistency**  
   `self.validators: dict[str, Draft202012Validator]` is fine, but the class still exposes `DRAFT = Draft202012Validator` only for validator instantiation. Consider renaming to `VALIDATOR_CLS` for clarity.

5. **No automated regression guard**  
   There is no CI step that runs all harnesses on `uv run`. A single `jsonschema` minor upgrade silently broke six harnesses.  
   **Action:** Add a top-level test target (e.g., `uv run python scripts/run_g1_harnesses.py`) that fails on any unexpected FAIL or schema-load BLOCKED.

## Decision

- **T04a/T04b:** Approve the schema-loading fix. Synthetic acceptance now passes; live integration remains correctly BLOCKED.
- **T01/T03a/T03b:** Collateral fix is correct and improves suite health; no regressions.
- **T02:** Fix exposed pre-existing negative-fixture classification issue; do not mark T02 done until that is resolved.

## Verification Commands

```bash
uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py
uv run python _bmad-output/test-artifacts/t04b/run_editor_tests.py
```
