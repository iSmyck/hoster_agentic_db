# Epic 5 Retrospective: Published knowledge pipeline

Date: 2026-11-08
Epic status: done
Stories: 5-1 T10a, 5-2 T10b

## What went well

- T10a harness covers exact-SHA CI index build, preflight artifact, full/incremental snapshot contract, eligible content exclusion, idempotent rebuild.
- T10b harness covers preflight→published lifecycle, CAS/fencing, per-Space retrieval, search cursor binding, stale/index-not-ready errors.
- Evidence sanitized and stored in `specs/corporate-kb/evidence/t10a|t10b/`.
- Existing unit tests still pass (`uv run pytest -q`: 28 passed).

## What needs improvement

- Live GitLab/PostgreSQL/CI/retrieval checks remain BLOCKED.
- 32 expected-negative FAIL cases across both stories; need clear separation in reporting.
- No real index build or search retrieval evidence.

## Action items

- Re-run T10a/T10b with real CI/index/retrieval sandbox when available.
- Add integration tests for actual pointer CAS/fencing logic once GO backend exists.

## Review note

Epic-level review found harness-only verification gaps: the existing evidence is produced by synthetic structural fixtures, and live runtime checks remain BLOCKED because sandboxes and credentials are unavailable.
