# Epic 1 Retrospective: Contract sandbox & defect prevention

Date: 2026-11-08
Epic status: done
Story: 1-1 T01 Reproducible two-Space sandbox and executable defect evidence

## What went well

- T01 harness created and produces reproducible validation reports.
- PASS 50 / FAIL 0 / BLOCKED 65 / NOT_EXECUTED 2.
- Structural/parse contract checks execute without live backends.
- Real integration checks correctly marked BLOCKED/NOT_EXECUTED, never mocked as PASS.
- Sanitized evidence contains no secrets or absolute filesystem paths.

## What needs improvement

- Implementation subagent corrupted `sprint-status.yaml` once; restored from git and tightened oversight.
- Several runtime checks deferred due to unavailable live GitLab/IdP/CI/hoster.ai sandboxes.
- Harness hardcodes CF vector execution rather than dynamically interpreting `t01-contract-tests.yaml`.
- No unit tests yet; baseline test runner not configured.

## Action items

- Add unit tests for validators/reporters/sandbox once pytest infrastructure exists.
- Implement dynamic catalog-driven execution when GO backend is available.
- Re-run full T01 suite after live sandboxes are provisioned in later epics.
