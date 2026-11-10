# Code Review: T07–T18b synthetic harness suite

**Reviewed by:** Amelia (Senior Software Engineer)  
**Date:** 2026-11-10  
**Scope:** `_bmad-output/test-artifacts/t07/` through `t18b/`

## Summary

All T07–T18b harnesses execute cleanly on synthetic fixtures with zero unexpected failures:

| Story | PASS | FAIL_EXPECTED | BLOCKED |
|-------|------|---------------|---------|
| T07 business review | 11 | 6 | 5 |
| T08 scoped working context | 10 | 4 | 4 |
| T09 single-page agent proposals | 11 | 10 | 4 |
| T10a exact-SHA CI index | 14 | 19 | 4 |
| T10b published retrieval | 17 | 13 | 4 |
| T11 hoster inference | 17 | 12 | 5 |
| T12a dry-run import | 12 | 24 | 4 |
| T12b controlled cutover | 11 | 18 | 4 |
| T13a portable export | 12 | 13 | 4 |
| T13b backup/rebuild | 15 | 22 | 4 |
| T14 quality/safety eval | 15 | 14 | 4 |
| T15 source registry | 23 | 10 | 3 |
| T16 real source connector | 14 | 14 | 5 |
| T17 evidence-gated extraction | 21 | 14 | 4 |
| T18 pilot hardening | 11 | 16 | 5 |
| T18a config-only deployment | 12 | 14 | 4 |
| T18b G3 backup/restore/upgrade | 14 | 21 | 5 |

BLOCKED counts are expected live-integration gates (GitLab, IdP, CI, hoster.ai, browser).

## Findings

### Blocking / Must-fix

_None._

### High

1. **Live acceptance remains outstanding**  
   Every T07–T18b story has BLOCKED runtime checks. G1 live closure depends on sandboxes/credentials that are still pending per sprint-status action items.

2. **No shared negative-case catalog**  
   Each harness re-declares invalid actor names, bad SHAs, malformed records, etc. Centralizing synthetic fixtures would reduce drift.

### Medium

3. **T10a/T10b retrieval harnesses do not exercise actual pgvector**  
   They validate contract invariants and cursor semantics but do not verify the `src/retrieval/` service. Service-level tests live under `src/retrieval/tests/` and should be reviewed separately.

4. **T16/T17 connector/extraction harnesses use placeholder source fixtures**  
   Owner-selected source and sample formats are still pending. The harnesses validate structural gates but cannot verify real parser behavior.

### Low

5. **Naming inconsistency**  
   Some result files are `*-results.json`, others `*-results.json`; summaries are consistently `summary.md`. No functional impact.

## Decision

- **T07–T18b:** Approve synthetic closure. All expected-negative cases are correctly classified; live integration remains BLOCKED.
- These harnesses meet their spec acceptance criteria for the synthetic scope and do not introduce regressions.

## Verification Commands

```bash
for runner in _bmad-output/test-artifacts/t{07,08,09,10a,10b,11,12a,12b,13a,13b,14,15,16,17,18,18a,18b}/run_*.py; do
  uv run python "$runner"
done
```
