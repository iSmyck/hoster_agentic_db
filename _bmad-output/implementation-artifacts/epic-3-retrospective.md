# Epic 3 Retrospective: Save & history

Date: 2026-11-08
Epic status: done
Stories: 3-1 T04a, 3-2 T04b

## What went well

- T04a harness covers durable draft save, idempotency, stale-base conflict, history cursor/truncation, revert-MR restore.
- T04b harness covers canonical Markdown/front-matter round-trip, front-matter boundary, Russian IME ordering, accessibility labels, XSS/MDX rejection.
- Evidence sanitized and stored in `specs/corporate-kb/evidence/t04a|t04b/`.
- No real credentials, endpoints, or production corpus used.

## What needs improvement

- T04b uses a lightweight Python state machine, not the actual TipTap runtime; real serializer round-trip remains BLOCKED.
- Real browser automation (IME, screen-reader, XSS rendering) is BLOCKED pending sandbox.
- No unit tests for validators; baseline test runner not configured.
- Combined epic-level review skipped in favor of autonomous throughput.

## Action items

- Configure pytest baseline test runner and add unit tests.
- Re-run T04b with real TipTap serializer and browser gate when sandbox is available.
- Re-run T04a with live GitLab/GO draft branches and MRs.
