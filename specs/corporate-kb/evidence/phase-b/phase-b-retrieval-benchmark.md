# Phase B — Identity/Retrieval live integration

## Evidence summary

| Item | Result |
|------|--------|
| Phase B status | `verified` (synthetic closure) |
| B.3 Retrieval API and search/ranking | `verified` |
| B.4 Index management and relevance tuning | `verified` |
| ACT-006 live pgvector benchmark | `BLOCKED` pending owner inputs |
| Evidence date | 2026-11-12 |

## Synthetic benchmark

The benchmark harness `src/retrieval/scripts/benchmark_retrieval.py` closes B.3/B.4
without requiring a real Russian corpus, Kimi credentials, or a running PostgreSQL/pgvector
stack. It exercises the existing Retrieval service code end-to-end on SQLite with the
`stub-deterministic` embedding adapter.

### Configuration

- Database: `sqlite:///:memory:`
- Embedding model: `stub-deterministic`
- Embedding dimensions: 1024 (from project `.env`)
- Search mode: `exact`
- Corpus size: 10 Russian topics
- Queries run: 20 (reader + approver per topic)
- `k`: 5

### Metrics

Values below are taken from the latest generated artifact.

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| recall@5 | 1.0 | >= 0.5 | PASS |
| MRR | 1.0 | >= 0.5 | PASS |
| p95 latency | see JSON artifact | <= 1000 ms | PASS |
| mean latency | see JSON artifact | — | — |

> The exact latency values vary by run and host; the authoritative numbers are in
> `_bmad-output/test-artifacts/b3/synthetic-retrieval-benchmark.json`.

### Edge-case checks

| Scenario | Expected | Status |
|----------|----------|--------|
| Empty corpus | Search returns empty list | PASS |
| Stale cursor | `STALE_SNAPSHOT` error | PASS |
| Unauthorized filter | Reader never sees `/secret/*` results | PASS |
| Outsider filter | No results for actor with no allowed prefixes | PASS |

### Artifacts

- Full JSON report: `_bmad-output/test-artifacts/b3/synthetic-retrieval-benchmark.json`
- Harness source: `src/retrieval/scripts/benchmark_retrieval.py`

## Unit test suite

Command: `uv run pytest src/retrieval/tests -q`

Result: `43 passed, 4 skipped, 1 warning` (runtime varies by host).

Skipped tests are the live integration tests in `test_retrieval_live.py`; they run only
when the Identity and Retrieval services are healthy or `RUN_LIVE_RETRIEVAL_TESTS=1` is set.

## Live smoke test

Command: `uv run python src/retrieval/scripts/smoke_retrieval.py`

Result: **BLOCKED** — Identity service (`localhost:8001`) and Retrieval service
(`localhost:8003`) are not currently listening, so the live smoke script cannot be executed.
The script is unchanged and ready to run once the local stack is started.

Blocked-run record: `_bmad-output/test-artifacts/b3/live-smoke-blocked.json`

## Live gates explicitly blocked

The following owner/sandbox inputs are still required before ACT-006 can move from
`synthetic PASS` to `live PASS`:

1. Russian-language knowledge-base corpus or representative sample documents and expected queries.
2. pgvector index configuration (chunk size, overlap, embedding model baseline) and target
   recall@k / MRR thresholds.
3. ACL matrix defining which users/groups may retrieve which documents.
4. SLO targets (p95 latency, relevance floor) and hardware baseline for the benchmark.

## Risks and caveats

- The synthetic benchmark validates adapter wiring, ACL filtering, cursor handling, and
  deterministic ranking. It does **not** validate production embedding quality or pgvector
  performance.
- Live acceptance for Phase B remains blocked on ACT-006 owner inputs; the `verified`
  status reflects synthetic closure only.
