#!/usr/bin/env bash
# ACT-006 live pgvector benchmark wrapper.
#
# Runs the retrieval benchmark against the local PostgreSQL/pgvector instance
# using the KIMI embedding model and a dedicated benchmark schema. The corpus
# is synthetic; only the infrastructure and embeddings are live.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$PROJECT_ROOT"

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb}"
export KB_INDEX_SCHEMA="kb_index_benchmark"
export EMBEDDING_MODEL="kimi"
export RETRIEVAL_EMBEDDING_MODEL="kimi"
export RETRIEVAL_EMBEDDING_DIMENSIONS="${RETRIEVAL_EMBEDDING_DIMENSIONS:-1024}"

export BENCHMARK_MODE="${BENCHMARK_MODE:-semantic}"
export BENCHMARK_K="${BENCHMARK_K:-5}"
export BENCHMARK_CORPUS_SIZE="${BENCHMARK_CORPUS_SIZE:-10}"
export BENCHMARK_QUERY_COUNT="${BENCHMARK_QUERY_COUNT:--1}"
export BENCHMARK_RECALL_THRESHOLD="${BENCHMARK_RECALL_THRESHOLD:-0.6}"
export BENCHMARK_MRR_THRESHOLD="${BENCHMARK_MRR_THRESHOLD:-0.5}"
export BENCHMARK_P95_MS_THRESHOLD="${BENCHMARK_P95_MS_THRESHOLD:-5000}"
export BENCHMARK_OUTPUT_PATH="${BENCHMARK_OUTPUT_PATH:-_bmad-output/test-artifacts/b3/live-retrieval-benchmark.json}"

echo "ACT-006 live pgvector benchmark"
echo "  DATABASE_URL: ${DATABASE_URL}"
echo "  KB_INDEX_SCHEMA: ${KB_INDEX_SCHEMA}"
echo "  EMBEDDING_MODEL: ${EMBEDDING_MODEL}"
echo "  BENCHMARK_MODE: ${BENCHMARK_MODE}"
echo "  BENCHMARK_OUTPUT_PATH: ${BENCHMARK_OUTPUT_PATH}"
echo ""

uv run python src/retrieval/scripts/benchmark_retrieval.py
