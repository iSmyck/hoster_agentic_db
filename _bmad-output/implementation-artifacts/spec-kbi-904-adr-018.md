---
title: 'KBI-904 ADR-018 source-sync auto-merge policy'
type: 'feature'
created: '2026-11-17'
status: 'done'
---

## Intent

**Problem:** Cross-cutting listed ADR-018 as a task.

**Approach:** The ADR is already accepted (2026-11-14). Verify the file and auto-merge invariants; do not rewrite policy.

## Boundaries & Constraints

**Always:**
- Treat `specs/corporate-kb/adr/ADR-018-source-sync-auto-merge-policy.md` as the source of truth.
- KBI.3 policy already implements AUTO_MERGE_REQUIRES_TRUSTED.

**Never:**
- Do not create a second ADR.
- Do not change accepted policy text.

## Code Map

- `specs/corporate-kb/adr/ADR-018-source-sync-auto-merge-policy.md`
- `src/kb-ingestion/tests/test_source_sync.py` — AUTO_MERGE_REQUIRES_TRUSTED
- `src/kb-ingestion/tests/test_cross_cutting.py` — ADR file check

## Tasks & Acceptance

**Acceptance Criteria:**
- Given the ADR path, when read, then status is Accepted and AUTO_MERGE_REQUIRES_TRUSTED is specified.
- Given a source with auto_merge true and trusted false, when registered, then AUTO_MERGE_REQUIRES_TRUSTED (existing KBI.3 test).

## Spec Change Log

- 2026-11-17: verified existing accepted ADR; no policy rewrite.

## Review Triage Log

### 2026-11-17 — Review pass
- `[low]` `[reject]` rewrite ADR-018 — already accepted 2026-11-14

## Auto Run Result

- ADR on disk; KBI.3 registration still refuses untrusted auto_merge.
- Verification: 211 passed; ruff clean.
