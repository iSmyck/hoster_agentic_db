---
title: 'ACT-006 — Live pgvector benchmark with synthetic Russian corpus'
type: 'chore'
created: '2026-11-12'
status: 'done'
baseline_revision: '2e65cb769db5c6131312698fadc205f1a225c2e3'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Owner approved a synthetic Russian corpus and team-defined ACL/thresholds for ACT-006. We need to execute the first live retrieval benchmark against PostgreSQL/pgvector with a real embedding model (KIMI) so Phase B can move from synthetic `verified` to live-accepted.

**Approach:** Extend the existing benchmark harness to run against PostgreSQL/pgvector using KIMI embeddings, generate a representative Russian corpus and golden queries, define an ACL matrix, run the benchmark, and record evidence. Keep the run isolated to a dedicated benchmark schema.

## Boundaries & Constraints

**Always:**
- Use a dedicated `kb_index_benchmark` schema; never run destructive migrations against production `kb_index`.
- Use synthetic fixtures only; no real client documents.
- Keep corpus small enough to control KIMI API cost (target ≤ 50 documents, ≤ 30 queries).
- Record evidence under `_bmad-output/test-artifacts/b3/` and sanitized report under `specs/corporate-kb/evidence/phase-b/`.
- Update `sprint-status.yaml` after verification.

**Never:**
- Run migrations against the production `kb_index` schema.
- Commit the KIMI API key or any secret.
- Mark the benchmark passed if thresholds are not met.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | pgvector schema ready, KIMI healthy | JSON report with recall@k, MRR, p95 latency; PASS vs thresholds | Report FAIL, non-zero exit |
| Empty query result | Query returns no chunks | recall@k = 0 for that query; included in averages | No crash |
| AuthZ filter drops all | User has no ACL path prefixes | Empty result set; recall = 0 | No crash |
| KIMI API error | 5xx/timeout from KIMI | Benchmark aborts with error message | Non-zero exit |
| pgvector not available | Extension missing or wrong dimension | Clear error, no partial writes | Non-zero exit |

</intent-contract>

## Code Map

- `src/retrieval/scripts/benchmark_retrieval.py` -- existing synthetic SQLite harness; extend for PostgreSQL/pgvector.
- `src/retrieval/app/core/config.py` -- settings for DB URL, schema, embedding model/dimensions.
- `src/retrieval/app/adapters/kimi_embeddings.py` -- KIMI embeddings adapter.
- `src/retrieval/migrations/versions/2026_11_09_0001_initial_kb_index_tables.py` -- initial schema.
- `src/retrieval/migrations/versions/2026_11_09_0002_update_chunk_embedding_dimension.py` -- destructive dimension migration.
- `src/retrieval/app/services/indexing.py` -- build/activate index.
- `src/retrieval/app/services/search.py` -- search/ranking.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- status updates.
- `specs/corporate-kb/evidence/phase-b/phase-b-retrieval-benchmark.md` -- evidence report.

## Tasks & Acceptance

**Execution:**
- `src/retrieval/scripts/benchmark_retrieval.py` -- add PostgreSQL/pgvector support: accept `DATABASE_URL` and `KB_INDEX_SCHEMA` from env; run Alembic migrations against the target schema before building the index; default to SQLite only when `DATABASE_URL` is unset. RATIONALE: enable live benchmark.
- `src/retrieval/scripts/benchmark_retrieval.py` -- generate a larger synthetic Russian corpus (≥ 20 documents across 10 topics) with public/restricted documents and a golden query set for reader/approver roles. RATIONALE: representative benchmark inputs.
- `src/retrieval/scripts/benchmark_retrieval.py` -- configure benchmark thresholds (recall@k ≥ 0.6, MRR ≥ 0.5, p95 ≤ 5000 ms) and expose them via env vars. RATIONALE: team-defined acceptance gates.
- `_bmad-output/test-artifacts/b3/run_act006_live_benchmark.sh` -- wrapper script that sets `DATABASE_URL`, `KB_INDEX_SCHEMA=kb_index_benchmark`, `EMBEDDING_MODEL=kimi`, and runs the harness. RATIONALE: reproducible command.
- `specs/corporate-kb/evidence/phase-b/phase-b-retrieval-benchmark.md` -- update with live benchmark metrics and PASS/FAIL verdict. RATIONALE: reviewable evidence.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- set Phase B status to `done`, ACT-006 to `done`, update overall_percent to 75. RATIONALE: reflect live acceptance.

**Acceptance Criteria:**
- Given PostgreSQL/pgvector is available, when the live benchmark runs with KIMI embeddings, then it completes and writes a JSON report.
- Given the report, when metrics are compared to thresholds, then recall@k, MRR, and p95 latency all pass.
- Given the evidence report, when reviewed, then it clearly states live benchmark, synthetic corpus, ACL matrix, KIMI model, and pgvector config.
- Given the sprint status file, when updated, then Phase B is `done` and ACT-006 is `done`.

## Spec Change Log

## Review Triage Log

### 2026-11-12 — Review pass (self-review)
- verdicts: 3 findings — high 0, medium 0, low 1, false 0, maybe-false 2
- findings:
  - `[low]` `[patch]` Migrations now resolve schema from `RETRIEVAL_KB_INDEX_SCHEMA` / `KB_INDEX_SCHEMA` at import time; this is required for ACT-006 but means the schema cannot change within a process. Existing default remains `kb_index`, so production paths are unaffected.
  - `[maybe-false]` `[defer]` Live benchmark p95 latency (~1240 ms) is well under threshold but depends on KIMI network routing; production latencies may differ with provider topology and corpus size.
  - `[maybe-false]` `[defer]` Synthetic 20-document corpus is small and clean; relevance on a larger, noisier production corpus is not claimed and remains a future gate.

## Design Notes

The benchmark is still corpus-synthetic by owner decision, but it uses real infrastructure (PostgreSQL + pgvector + KIMI). This is the closest we can get to production retrieval acceptance without real client documents. The dedicated schema ensures migrations are safe.

## Verification

**Commands:**
- `bash _bmad-output/test-artifacts/b3/run_act006_live_benchmark.sh` -- expected: exits 0, writes `_bmad-output/test-artifacts/b3/live-retrieval-benchmark.json`.
- `uv run pytest src/retrieval/tests -q` -- expected: all non-skipped tests still pass.
- `python -c "import yaml; yaml.safe_load(open('_bmad-output/implementation-artifacts/sprint-status.yaml'))"` -- expected: no parse errors.

**Manual checks (if no CLI):**
- Inspect `_bmad-output/test-artifacts/b3/live-retrieval-benchmark.json` for metrics and pass/fail.
- Inspect `specs/corporate-kb/evidence/phase-b/phase-b-retrieval-benchmark.md` for live evidence.
- Inspect `sprint-status.yaml` Phase B block for `done` status.

## Auto Run Result

- Summary: ACT-006 live pgvector benchmark executed successfully. Extended `benchmark_retrieval.py` to support PostgreSQL/pgvector and KIMI embeddings, generated a 20-document synthetic Russian corpus, defined an ACL matrix, and ran semantic search against the local PostgreSQL/pgvector instance. Phase B moved to `done`, ACT-006 to `done`, overall_percent raised to 75.
- Files changed:
  - `src/retrieval/scripts/benchmark_retrieval.py` — PostgreSQL/pgvector support, migration helpers, larger Russian corpus, live report metadata.
  - `src/retrieval/app/core/config.py` — benchmark thresholds updated to recall@k ≥ 0.6, p95 ≤ 5000 ms.
  - `src/retrieval/migrations/versions/2026_11_09_0001_initial_kb_index_tables.py` — configurable schema via env vars.
  - `src/retrieval/migrations/versions/2026_11_09_0002_update_chunk_embedding_dimension.py` — configurable schema via env vars.
  - `_bmad-output/test-artifacts/b3/run_act006_live_benchmark.sh` — wrapper script.
  - `_bmad-output/test-artifacts/b3/live-retrieval-benchmark.json` — generated live report.
  - `_bmad-output/test-artifacts/b3/synthetic-retrieval-benchmark.json` — regenerated synthetic report.
  - `specs/corporate-kb/evidence/phase-b/phase-b-retrieval-benchmark.md` — updated live evidence.
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — status updates.
- Review findings: 1 low patched/accepted, 2 maybe-false deferred (latency variability, corpus size).
- Follow-up review recommended: false.
- Verification performed:
  - `bash _bmad-output/test-artifacts/b3/run_act006_live_benchmark.sh` → PASS=true, recall@5=1.0, MRR=1.0, p95≈1240 ms.
  - `uv run pytest src/retrieval/tests -q` → 43 passed, 4 skipped, 1 warning.
  - `uv run python src/retrieval/scripts/benchmark_retrieval.py` → synthetic fallback PASS.
  - `uv run ruff check ...` → All checks passed.
- Residual risks:
  - Live benchmark used synthetic corpus; real production corpus may show different relevance/latency.
  - `kb_index_benchmark` schema is dropped and recreated on each benchmark run; must never be pointed at production schema.
  - Live smoke test `smoke_retrieval.py` still BLOCKED because services are not listening.
