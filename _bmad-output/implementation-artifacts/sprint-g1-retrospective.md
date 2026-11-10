# Sprint Retrospective: G1 Vertical Slice Implementation

**Date:** 2026-11-10  
**Scope:** Epics 0–13, T00–T18b, I01–I09  
**Conducted by:** Amelia (Senior Software Engineer)

## Outcome

**ACCEPTED** for synthetic closure. All stories in sprint-status.yaml are `done`. All T-series harnesses and the pytest service suite pass with zero unexpected failures.

| Suite | Result | Notes |
|-------|--------|-------|
| T01–T18b harnesses | PASS (synthetic) | Live integration BLOCKED |
| `uv run pytest -q` | 220 passed | Identity, GO, retrieval, ingestion |
| `uv run ruff check src/identity src/git-orchestrator src/retrieval src/ingestion` | clean | (rerun before commit) |

## What went well

1. **Systematic harness cleanup unblocked the whole suite.** A single jsonschema/referencing API mismatch (`Draft202012Validator` vs. `DRAFT202012`) was silently breaking six early harnesses. Fixing it in one pattern and applying it across t01/t02/t03a/t03b/t04a/t04b restored 200+ synthetic checks.
2. **Service tests are green.** 220 pytest tests cover identity, git-orchestrator, retrieval, and ingestion services.
3. **G1 editor seam landed.** `src/git-orchestrator/app/api/router.py` added `/api/g1-editor/prepare-branch` with identity binding, idempotency, and proposal-branch creation.
4. **Merge durability invariants are enforced.** Self-approval denial, approver mismatch, idempotent merge replay, and merge parent verification are all implemented and tested.

## What needs improvement

1. **T02 maintained a separate reporter stack.** Expected-negative failure classification required edits in three files instead of one. Future harnesses should reuse `harness_common.py`.
2. **Synchronous HTTP in FastAPI routes.** `prepare_branch` and `get_current_identity` use blocking `httpx` calls. This will not hold up under real load and must be refactored to async before live acceptance.
3. **No regression guard for dependency upgrades.** The jsonschema breakage was only found because we re-ran the harnesses. A single CI step that runs all harnesses would catch this class of failure automatically.
4. **`require_space_access` is a global allowlist, not identity-bound.** The name implies authorization but it only validates `KB_ALLOWED_SPACE_IDS`.

## Action items

| ID | Action | Owner | Status |
|----|--------|-------|--------|
| G1-A1 | Refactor `prepare_branch` and `get_current_identity` to async I/O | Backend | open |
| G1-A2 | Add `project_url(space_id)` to `GitLabAdapter` protocol and both adapters | Backend | open |
| G1-A3 | Handle update-vs-create in `prepare_branch` for existing KB pages | Backend | open |
| G1-A4 | Add top-level harness regression target in CI/CD | QA/DevOps | open |
| G1-A5 | Rename `require_space_access` or implement identity-to-space lookup | Backend | open |
| G1-A6 | Close live acceptance gates: IdP, GitLab MR lifecycle, hoster.ai inference, source connectors | Owner + Dev + QA | open |
| G1-A7 | Migrate T02 reporter stack to `harness_common.py` | Dev | open |

## Deferred work

- T19/T20 remain deferred per ADR-19 (measured benchmark and business gate).
- Production HA, AD/SLO, monitoring, and second-client deployment remain deferred per owner decisions G1-D6/G1-D7.

## Decision

- Mark **G1 vertical slice implementation DONE**.
- Move to **Phase B readiness**: identity/retrieval services live integration once the sandbox is provisioned and owner selects production IdP profile and embedding model.
