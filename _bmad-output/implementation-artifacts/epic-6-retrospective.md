# Epic 6 Retrospective: Migration & portability

Date: 2026-11-08
Epic status: done
Stories: 6-1 T12a, 6-2 T12b, 6-3 T13a, 6-4 T13b

## What went well

- T12a dry-run import and admission gates covered.
- T12b controlled cutover/activation and pointer order covered.
- T13a complete portable export with manifests and closure covered.
- T13b mirror/metadata backup, rebuild and conservative restore covered.
- Evidence sanitized and stored.
- Existing unit tests pass (69 passed).

## What needs improvement

- 77 expected-negative FAIL cases across epic; reporting clarity needed.
- Live object-store/IdP/GitLab/PostgreSQL checks remain BLOCKED.
- No real export/restore round-trip evidence.

## Action items

- Re-run T12-T13 with real source connectors, object store, and GitLab sandbox.
- Add integration tests for actual export/restore once GO backend exists.
