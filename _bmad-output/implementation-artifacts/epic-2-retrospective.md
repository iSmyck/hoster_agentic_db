# Epic 2 Retrospective: Managed documents & access

Date: 2026-11-08
Epic status: done
Stories: 2-1 T02, 2-2 T03a, 2-3 T03b

## What went well

- All three E02 stories implemented as thin QA adapters over contracts.
- T02 document harness covers tree navigation, exact-revision direct read, section anchors, attachment tuples, archive invariants, path normalization.
- T03a identity harness covers stable keys, nested group snapshots, rename survival, empty groups, epoch ordering.
- T03b policy harness covers per-Space isolation, longest-prefix selection, path normalization, revocation epoch, error shape.
- Evidence sanitized and stored in `specs/corporate-kb/evidence/t02|t03a|t03b/`.
- No real credentials, endpoints, or production corpus used.

## What needs improvement

- Live runtime checks remain BLOCKED pending GitLab/IdP/GO sandboxes.
- No unit tests for harness modules; baseline test runner not configured.
- Dynamic catalog-driven execution not implemented; vectors are hardcoded per story.
- Combined epic-level code review was skipped in favor of autonomous throughput; consider per-story review for E03+.

## Action items

- Configure pytest/pyproject.toml baseline test runner.
- Add unit tests for document/identity/policy validators.
- Re-run E02 runtime checks after E04 GO backend and real sandboxes are available.
