# T04a evidence — durable drafts, guarded navigation, cursor-based history

**Status:** IN_PROGRESS — synthetic API checks PASS; live GitLab/Open WebUI checks remain BLOCKED pending sandbox.

## Scope

T04a covers three editor capabilities required by the G1 vertical slice:

1. **Durable drafts** — per-author, per-page auto/explicit save in `kb_ops.drafts`.
2. **Guarded navigation** — browser `beforeunload` + in-app dirty-state warning before leaving unsaved changes.
3. **Cursor-based Git history** — paginated commit history for a page path with cursor pagination.

## Synthetic evidence

### Fixture-based contract checks

- Runner: `_bmad-output/test-artifacts/t04a/run_draft_tests.py`
- Results: [`draft-results.json`](draft-results.json) | [`summary.md`](summary.md)
- Counts: **20 PASS, 0 FAIL, 6 BLOCKED**
- BLOCKED checks are the live-only runtime checks (GitLab branch CAS, idempotency registry, stale-base diff, history cursor, restore revert-MR).

### API-level checks (new)

- Runner: `_bmad-output/test-artifacts/t04a/run_draft_api_tests.py`
- Tests: `src/git-orchestrator/tests/test_t04a_drafts.py`
- Results: [`api-results.json`](api-results.json) | [`api-summary.md`](api-summary.md)
- Counts: **9 PASS, 0 FAIL, 0 BLOCKED**
- Coverage:
  - Save draft creates or updates the same slot (idempotency by `space_id`/`path`/`author_stable_id`).
  - Get draft returns saved content; missing draft returns 404.
  - List drafts returns only the caller's drafts for the Space.
  - Discard draft removes the record.
  - History returns seeded commits and supports cursor pagination.
  - Space isolation and path traversal validation.

## Live acceptance (BLOCKED)

The following checks require a running Open WebUI + GitLab sandbox and are not claimed as PASS:

- Browser `beforeunload` guard with real navigation.
- Draft auto-save/load round-trip in `/kb` UI.
- History panel rendering and "Restore version" flow.
- Independent author/approver sessions with draft isolation.

## Commands

```bash
# Full project test suite
uv run pytest -q

# T04a API tests only
DATABASE_URL=sqlite:///:memory: KB_OPS_SCHEMA= uv run pytest src/git-orchestrator/tests/test_t04a_drafts.py -v

# T04a harness runners
uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py
uv run python _bmad-output/test-artifacts/t04a/run_draft_api_tests.py
```

## Implementation notes

- Added `DraftRecord` model and Alembic migration `183bf70ff169`.
- Added `src/git-orchestrator/app/services/drafts.py` with save/get/list/discard.
- Added GO endpoints under `/api/kb/v1/drafts/*` and `/api/kb/v1/documents/history`.
- Extended `StubGitLabAdapter` with `get_history` for synthetic tests.
- Updated `KbEditor.svelte` and `kb.ts` in the upstream Open WebUI checkout with draft tabs, dirty-state guard, and history panel.
- Added `src/git-orchestrator/app/services/seed.py` and `seeded_client` fixture for default mock data.
