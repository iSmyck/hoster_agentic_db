---
title: 'T04a Durable drafts, guarded navigation and cursor-based Git history'
type: 'feature'
created: '2026-11-08'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'd2c0d072a757808ea891fbf6414f00147679f7a7'
context:
  - specs/corporate-kb/contracts/proposal-record.schema.json
  - specs/corporate-kb/contracts/decision-record.schema.json
  - specs/corporate-kb/contracts/front-matter.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-3-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для durable branch-based drafts, guarded navigation, stale-base conflicts и cursor-based Git history с revert-MR restore.

**Approach:** Создать T04a harness, который на synthetic fixtures валидирует draft/branch contracts, idempotency, stale-base conflict detection, history cursor/truncation и restore-through-revert-MR semantics.

## Boundaries & Constraints

**Always:**
- Draft branch attributed to author; `main` unchanged.
- Idempotent save/replay returns existing draft, no duplicate commit.
- `STALE_BASE` conflict when target advances before save.
- History pages expose explicit truncation reason and next cursor.
- Restore создаёт revert-MR с новым commit, не перезаписывая историю.
- Evidence в `_bmad-output/test-artifacts/t04a/` и `specs/corporate-kb/evidence/t04a/`.

**Never:**
- Не использовать real GitLab/GO credentials.
- Не реализовывать concurrent accepts (E04.2) или full AuthZ enforcement (E02.3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Save draft | Author + base_sha + content | Draft branch/commit created/updated PASS | Missing base_sha → FAIL |
| Idempotent replay | Same idempotency key + same payload | Existing draft returned PASS, no new commit | Different payload → IDEMPOTENCY_KEY_REUSED |
| Stale base | Target advanced before save | STALE_BASE conflict PASS | Silent overwrite → FAIL |
| History cursor | Paginated history request | Ordered commits, explicit truncation/cursor | Out-of-order → FAIL |
| Restore revision | Exact historical revision | Revert-MR created with new commit PASS | Direct main write → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t03b/run_policy_tests.py` — reference harness pattern.
- `specs/corporate-kb/contracts/proposal-record.schema.json` — proposal/version metadata.
- `specs/corporate-kb/contracts/decision-record.schema.json` — decision lifecycle.
- `specs/corporate-kb/contracts/front-matter.schema.json` — document state/archive.
- `_bmad-output/implementation-artifacts/epic-3-context.md` — draft/history decisions.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t04a/run_draft_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t04a/fixtures/` — synthetic draft/history/restore YAML fixtures.
- [x] `_bmad-output/test-artifacts/t04a/validators/` — draft save, idempotency, stale base, history cursor, restore validators.
- [x] `_bmad-output/test-artifacts/t04a/draft-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t04a/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `3-1-t04a-...` → `done`.

**Acceptance Criteria:**
- [x] Given authorized author and current base_sha, when save requested, then draft branch/commit created/updated and main unchanged.
- [x] Given same idempotency key and same payload, when replayed, then existing draft returned with no duplicate commit.
- [x] Given target advanced before save, when second save requested, then STALE_BASE conflict with diff view.
- [x] Given history request, when paginated, then ordered commits with explicit truncation reason and next cursor.
- [x] Given exact historical revision, when restore requested, then revert-MR created with new commit, no main rewrite.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

T04a harness reuse T01-T03 reporters/sanitize. Validators operate on synthetic YAML fixtures and JSON schemas; live GitLab/GO checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t04a/run_draft_tests.py` -- expected: write reports.
- `python -m json.tool _bmad-output/test-artifacts/t04a/draft-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t04a/` -- expected: no matches.
