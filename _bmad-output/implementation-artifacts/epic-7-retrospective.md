# Epic 7 Retrospective: Internal pilot acceptance

Date: 2026-11-08
Epic status: done
Stories: 7-1 T11, 7-2 T14, 7-3 T18

## What went well

- T11 inference lifecycle harness covers streaming, tool calls, errors, cancellation.
- T14 eval harness covers Russian golden set, refusal, groundedness, human-in-the-loop.
- T18 pilot hardening harness covers protected deployment and pre-G2 readiness.
- Live integrations recorded as BLOCKED; no fabricated evidence.
- Existing unit tests pass (69 passed).

## What needs improvement

- 42 expected-negative FAILs across epic.
- Real hoster.ai endpoint, golden-set evaluation, and pilot deployment evidence unavailable.

## Action items

- Re-run T11/T14/T18 with real hoster.ai sandbox and owner-authorized pilot corpus.
- Add integration tests for actual inference/eval pipelines once APIs are available.
