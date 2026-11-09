# ADR-19: T19/T20 deferred — business gate required

## Status

Proposed / Deferred

## Context

T19 — Retrieval evolution and T20 — Fast/Trust/Scale policies are listed in `spec.md` but explicitly depend on:
- Measured ACL-aware quality/latency/cost benchmarks from T14
- A separate business gate approving the work
- Clarified R/I/A mapping for T20 (currently not normatively assigned)

Current implementation (Epics 9–13) delivers the MVP baseline: pgvector + FTS retrieval, single deployment profile, no caching/routing/threshold policies.

## Decision

T19 and T20 are **deferred** from the MVP implementation phase. They will not be scheduled in sprints until:

1. T14 evaluation produces measured benchmarks on the production-like dataset.
2. Owner/product defines acceptable quality/latency/cost thresholds.
3. A separate ADR compares baseline pgvector with candidate stacks (OpenSearch, etc.) using shadow index / dual-read evaluation.
4. For T20: R/I/A mapping is clarified and a business gate approves Fast/Trust/Scale policies.

## Consequences

- No OpenSearch, stack swap, cache layer, routing, or Fast/Trust/Scale policies in MVP.
- Architecture remains extensible: retrieval and ingestion adapters are behind ports; adding new index backends or policies is possible without rewriting core.
- Sprint tracking marks T19/T20 as deferred pending business gate.

## Evidence

- `spec.md` T19/T20 deferred notes
- `tasks.md` T19/T20 status
- Measured benchmarks required from T14
