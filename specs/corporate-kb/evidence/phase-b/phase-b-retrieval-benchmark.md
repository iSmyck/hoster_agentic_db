# Phase B — Identity/Retrieval live integration

## Evidence summary

| Item | Result |
|------|--------|
| Phase B status | `done` |
| B.3 Retrieval API and search/ranking | `done` |
| B.4 Index management and relevance tuning | `done` |
| ACT-006 live pgvector benchmark | `PASS` |
| Evidence date | 2026-11-12 |

## Live pgvector benchmark (ACT-006)

The benchmark harness `src/retrieval/scripts/benchmark_retrieval.py` was run
against the local PostgreSQL/pgvector instance with the KIMI embedding model.
The corpus is synthetic (20 Russian-language documents across 10 topics), but
the infrastructure, embedding model, and pgvector vector search are live.

### Configuration

| Setting | Value |
|---------|-------|
| Database | `postgresql+psycopg://corp_kb:***@localhost:5432/corp_kb` |
| Schema | `kb_index_benchmark` (dedicated benchmark schema) |
| Embedding model | `kimi` (`text-embedding-v2`) |
| Embedding dimensions | 1024 |
| Search mode | `semantic` |
| Corpus size | 10 topics |
| Document count | 20 (public + restricted per topic) |
| Queries run | 20 (reader + approver per topic) |
| `k` | 5 |

### ACL matrix

| Role | Actor ID | Allowed prefixes |
|------|----------|------------------|
| reader | `11111111-1111-1111-1111-111111111111` | `/docs` |
| approver | `22222222-2222-2222-2222-222222222222` | `/docs`, `/secret` |
| outsider | `33333333-3333-3333-3333-333333333333` | `/none` |

### Thresholds

| Metric | Threshold |
|--------|-----------|
| recall@5 | >= 0.6 |
| MRR | >= 0.5 |
| p95 latency | <= 5000 ms |

### Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| recall@5 | 1.0 | >= 0.6 | PASS |
| MRR | 1.0 | >= 0.5 | PASS |
| p95 latency | ~1240 ms | <= 5000 ms | PASS |
| mean latency | ~1040 ms | — | — |

> Latency varies by run and network conditions; the authoritative numbers are in
> `_bmad-output/test-artifacts/b3/live-retrieval-benchmark.json`.

### Edge-case checks

| Scenario | Expected | Status |
|----------|----------|--------|
| Empty corpus | Search returns empty list | PASS |
| Stale cursor | `STALE_SNAPSHOT` error | PASS |
| Unauthorized filter | Reader never sees `/secret/*` results | PASS |
| Outsider filter | No results for actor with no allowed prefixes | PASS |

### Artifacts

- Full JSON report: `_bmad-output/test-artifacts/b3/live-retrieval-benchmark.json`
- Harness source: `src/retrieval/scripts/benchmark_retrieval.py`
- Wrapper script: `_bmad-output/test-artifacts/b3/run_act006_live_benchmark.sh`

## Synthetic benchmark (historical baseline)

The same harness also supports a fully synthetic SQLite/stub-embedding mode for
fast local regression checks. Historical artifact:
`_bmad-output/test-artifacts/b3/synthetic-retrieval-benchmark.json`.

## Unit test suite

Command: `uv run pytest src/retrieval/tests -q`

Result: `43 passed, 4 skipped, 1 warning` (runtime varies by host).

Skipped tests are the live integration tests in `test_retrieval_live.py`; they
run only when the Identity and Retrieval services are healthy or
`RUN_LIVE_RETRIEVAL_TESTS=1` is set.

## Live smoke test

Command: `uv run python src/retrieval/scripts/smoke_retrieval.py`

Result: **BLOCKED** — Identity service (`localhost:8001`) and Retrieval service
(`localhost:8003`) are not currently listening, so the live smoke script cannot
be executed. The script is unchanged and ready to run once the local stack is
started.

Blocked-run record: `_bmad-output/test-artifacts/b3/live-smoke-blocked.json`

## Risks and caveats

- The live benchmark validates real pgvector storage, KIMI embedding quality,
  semantic ranking, and ACL filtering on a dedicated benchmark schema. It does
  not exercise the production `kb_index` schema or real client documents.
- The synthetic corpus is short (one public and one restricted paragraph per
  topic). Relevance on a larger, noisier production corpus may differ and will
  require a separate acceptance run.
- Latency was measured against a local Dockerized PostgreSQL instance; production
  latencies will depend on network topology, model provider routing, and corpus
  size.
