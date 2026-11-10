# Code Review: Git Orchestrator G1 merge/recovery/browser-editor changes

**Reviewed by:** Amelia (Senior Software Engineer)  
**Date:** 2026-11-10  
**Scope:** Uncommitted changes in `src/git-orchestrator/`

## Summary

Changes add authorization, self-approval guards, idempotent merge replay, protected tag anchoring, and the `/api/g1-editor/prepare-branch` endpoint. All 220 pytest tests pass, including new tests for self-approval, merge replay, slash-containing space IDs, and direct-push blocking.

## Findings

### Blocking / Must-fix

_None._

### High

1. **`prepare_branch` uses synchronous `httpx.Client` in a FastAPI route**  
   The endpoint performs multiple blocking GitLab REST calls. Under load this will starve the ASGI worker pool.  
   **Action:** Refactor to `httpx.AsyncClient` and make the route + adapter methods async, or move the work to a background task queue.

2. **`_gitlab_project_url` reaches into adapter private attributes**  
   It uses `getattr(adapter, "base_url", "")` and `getattr(adapter, "project_path_prefix", "")`. With `StubGitLabAdapter` in tests this returns empty strings but the route is not exercised in the current test suite, so the mismatch is latent.  
   **Action:** Add `project_url(space_id: str)` to the `GitLabAdapter` protocol and implement it in both `HttpGitLabAdapter` and `StubGitLabAdapter`.

3. **`prepare_branch` action is always `"create"`**  
   Editing an existing KB page will fail because the GitLab commits API action is hard-coded to `create`.  
   **Action:** Detect existence of `file_path` (e.g., via `adapter.get_file`) and use `"update"` with `last_commit_id` or `"create"` accordingly.

### Medium

4. **No cleanup of `kb-prepare/{run_id}` temp branch on failure**  
   A partially created temp branch leaks if a later step fails.  
   **Action:** Wrap the branch creation in a try/finally that deletes the temp branch on non-replay failures.

5. **`proposal_branch = f"proposal/{proposal_sha[:8]}"` collision risk**  
   8-character SHA prefix is not collision-resistant. For the MVP corpus size it may be acceptable, but a UUID5 or full SHA-based branch name is safer.

6. **`require_space_access` is a global allowlist, not identity-bound**  
   The function name implies per-identity authorization, but it only checks `KB_ALLOWED_SPACE_IDS`.  
   **Action:** Rename to `require_known_space` or implement identity-to-space lookup against the identity service.

7. **`get_current_identity` blocks on identity service call**  
   Every authenticated route waits synchronously for the identity service. Add a short-lived cache (e.g., LRU by token with TTL) and/or switch to async.

### Low

8. **CORS default includes `localhost:3100` and `localhost:5050`**  
   Acceptable for sandbox, but production deployment must override `CORS_ALLOW_ORIGINS`.

9. **Policy revision defaults are placeholder SHA-like strings**  
   `ACCESS_POLICY_REVISION` and `APPROVAL_POLICY_REVISION` default to `"a"*40`/`"b"*40`. These must be overridden by deployment config.

## Decision

- **Approve** the functional changes for G1 synthetic closure.
- **Required follow-up** before live acceptance: async I/O in `prepare_branch`, adapter protocol extension for project URL, and update-vs-create handling.
- Tests adequately cover the new invariants.

## Verification

```bash
uv run pytest -q
```

Result: 220 passed.
