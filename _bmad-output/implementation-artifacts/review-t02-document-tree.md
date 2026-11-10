# Code Review: T02 document tree and canonical direct read harness

**Reviewed by:** Amelia (Senior Software Engineer)  
**Date:** 2026-11-10  
**Scope:** `_bmad-output/test-artifacts/t02/`

## Summary

Fixed negative-fixture classification so intentionally invalid fixtures (`bad-*`, `malformed-*`) are reported as `FAIL_EXPECTED` instead of plain `FAIL`. After the fix:

- PASS: 104
- FAIL (expected): 5
- FAIL (unexpected): 0
- BLOCKED: 4

## Changes

1. `validators/schemas.py` — schema loading now uses `referencing.jsonschema.DRAFT202012` (same jsonschema 4.26 fix as T01/T03/T04).
2. `run_document_tests.py` — `_add_check` now detects negative fixtures by id/fixture path and sets `details["expected_negative"] = True`.
3. `reporters/json_reporter.py` — `_counts` now returns `FAIL_EXPECTED` / `FAIL_UNEXPECTED`.
4. `reporters/markdown_reporter.py` — summary renders expected vs. unexpected failures separately.

## Findings

### Blocking / Must-fix

_None._

### Medium

1. **T02 has its own reporter stack**  
   Unlike T04–T18b which reuse `harness_common.py`, T02 maintains a separate `ReportBuilder`, `Check`, and `render_summary`. This is why the expected-negative fix had to be applied in three files instead of one.  
   **Action:** Migrate T02 to `harness_common.py` to reduce maintenance duplication.

### Low

2. **Negative fixture detection is name-based**  
   Relies on "bad-" / "malformed-" substrings. A fixture metadata field (`negative: true`) would be more explicit.

## Decision

- **T02:** Approve. Synthetic acceptance passes with zero unexpected failures.

## Verification

```bash
uv run python _bmad-output/test-artifacts/t02/run_document_tests.py
```
