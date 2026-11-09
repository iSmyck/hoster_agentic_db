# Epic 4 Retrospective: Governed agent workflow

Date: 2026-11-08
Epic status: done
Stories: 4-1 T05a, 4-2 T05b, 4-3 T06, 4-4 T07, 4-5 T08, 4-6 T09, 4-7 T07b

## What went well

- All 7 E04 stories implemented as contract/structural harnesses.
- T05a ProposalRecord/ProposalVersion lifecycle covered.
- T05b DecisionRecord, merge proof, recovery semantics covered.
- T06 merge-only GO enforcement and fencing covered.
- T07 business review UI and independent decisions covered.
- T08 scoped agent context and direct-read tools covered.
- T09 restricted single-page agent proposals covered.
- T07b DocOps projections, correction tasks, UX telemetry covered.
- Existing unit tests still pass (`uv run pytest -q`: 28 passed).

## What needs improvement

- 50 intentional FAIL cases; summary should clearly separate structural negatives from regressions.
- Live GitLab/GO/browser/kb_ops checks remain BLOCKED.
- No real merge commit, MR, or browser automation evidence.
- Per-story review skipped in favor of epic-level review.
- Epic-level review found harness-only verification gaps; live runtime checks remain BLOCKED until GO/GitLab sandbox.

## Action items

- Run epic-level code review and fix findings.
- Re-run live checks after GO backend and GitLab sandbox are available.
- Consider refining FAIL reporting to tag expected negatives explicitly.
