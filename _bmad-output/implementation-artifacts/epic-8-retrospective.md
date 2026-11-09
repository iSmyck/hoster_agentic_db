# Epic 8 Retrospective: Production-ready perimeter & G3 acceptance

Date: 2026-11-08
Epic status: done
Stories: 8-1 T15, 8-2 T16, 8-3 T17, 8-4 T18a, 8-5 T18b

## What went well

- T15 source registry and three-way update harness covered.
- T16 real source connector contract harness covered.
- T17 evidence-gated extraction and OCR/media quality harness covered.
- T18a repeatable config-only deployment harness covered.
- T18b full G3 backup/restore/upgrade operational acceptance harness covered.
- All live integrations recorded as BLOCKED; no fabricated evidence.
- Existing unit tests pass (69 passed).

## What needs improvement

- 73 expected-negative FAIL cases across epic.
- Real source connectors, second-client environment, G3 pilot remain BLOCKED.

## Action items

- Re-run T15-T18b with owner-selected real source connector and second-client sandbox.
- Add integration tests for actual source registry, extraction and deployment once backends exist.
