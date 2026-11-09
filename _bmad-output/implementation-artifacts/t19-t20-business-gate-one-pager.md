# T19/T20 Business Gate One-Pager

## What is being decided

Whether to fund and schedule:
- **T19 — Retrieval evolution:** compare baseline pgvector+FTS with alternative stacks (OpenSearch, etc.) and migrate if measured benefits justify cost.
- **T20 — Fast/Trust/Scale policies:** add caching, routing, threshold, capacity and client-profile policies.

## Why it cannot be decided now

1. **No measured data.** T14 evaluation must run on a production-like corpus with real inference and produce quality/latency/cost benchmarks per ACL profile.
2. **No thresholds.** Owner/product has not defined acceptable latency/quality/cost bounds.
3. **T20 R/I/A mapping is incomplete.** `spec.md` does not assign Requirements to T20; existing links are design-derived, not normative.
4. **MVP is not yet deployed.** It is premature to optimize retrieval or add scale policies before real usage patterns exist.

## Required inputs for the gate

| Input | Owner | Status |
|---|---|---|
| T14 measured benchmarks (quality, latency, cost per ACL profile) | Engineering + QA | BLOCKED until real corpus/inference |
| Acceptable thresholds for latency @ p95/99, MRR/NDCG, cost per 1k queries | Product/Owner | TODO |
| Candidate stack shortlist (OpenSearch, etc.) and compatibility assessment | Architecture | TODO |
| T20 R/I/A mapping and policy requirements | Product/Owner | TODO |
| Budget and SLO impact estimate | Product/Owner | TODO |

## Options

1. **Proceed with T19 only** — evaluate and optionally migrate retrieval backend.
2. **Proceed with T20 only** — add policies without changing retrieval stack.
3. **Proceed with both** — full retrieval evolution + policy layer.
4. **Defer indefinitely** — keep baseline pgvector+FTS and no policies until data justifies change.

## Recommendation

**Option 4 (defer) until T14 benchmarks exist.** Architecture is designed to support T19/T19 later without rewrite.

## Next step

Schedule business gate review after first real-corpus T14 evaluation.
