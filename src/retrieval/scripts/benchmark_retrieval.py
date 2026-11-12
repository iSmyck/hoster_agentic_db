#!/usr/bin/env python3
"""Synthetic ACL-aware Russian corpus benchmark for the Retrieval adapter.

The harness runs without owner credentials or a real corpus. It uses:

* SQLite in-memory database (no PostgreSQL/pgvector required).
* The ``stub-deterministic`` embedding adapter by default.
* A generated Russian-language corpus with public and restricted documents.
* A configurable ACL matrix enforced by the stub identity client.

Metrics reported: recall@k, mean reciprocal rank (MRR), and p95 search latency.
The harness also exercises the empty-corpus, unauthorized-filtering, and stale-
cursor edge cases.

Run from the project root:
    uv run python src/retrieval/scripts/benchmark_retrieval.py

Environment variables (see ``src/retrieval/app/core/config.py``):
    BENCHMARK_K                 cut-off rank (default 5)
    BENCHMARK_CORPUS_SIZE       number of topics (default 10; max 10)
    BENCHMARK_QUERY_COUNT       number of golden queries to run; -1 runs all (default -1)
    BENCHMARK_MODE              exact | semantic | hybrid (default exact)
    BENCHMARK_EMBEDDING_MODEL   stub-deterministic | kimi (default stub-deterministic)
    BENCHMARK_RECALL_THRESHOLD
    BENCHMARK_MRR_THRESHOLD
    BENCHMARK_P95_MS_THRESHOLD
    BENCHMARK_OUTPUT_PATH
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Make the ``src`` package root importable when the script is run directly.
SRC_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SRC_ROOT))

# Force SQLite in-memory mode with schema qualification disabled, and default
# the benchmark to the stub embedding adapter before the settings singleton is
# imported. Kimi embeddings can be opted into via BENCHMARK_EMBEDDING_MODEL.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("KB_INDEX_SCHEMA", "")

# The benchmark must set the embedding model before the settings singleton is
# imported. It also accepts the service-prefixed alias for consistency.
os.environ["EMBEDDING_MODEL"] = os.environ.get(
    "BENCHMARK_EMBEDDING_MODEL",
    os.environ.get("RETRIEVAL_BENCHMARK_EMBEDDING_MODEL", "stub-deterministic"),
)
os.environ["RETRIEVAL_EMBEDDING_MODEL"] = os.environ["EMBEDDING_MODEL"]

from sqlalchemy import create_engine  # noqa: I001
from sqlalchemy.orm import sessionmaker

from retrieval.app.adapters.embeddings import build_embedding_adapter
from retrieval.app.adapters.go_client import StubGOClient
from retrieval.app.adapters.identity_client import StubIdentityClient
from retrieval.app.core.config import settings
from retrieval.app.models.index import Base
from retrieval.app.services.indexing import activate_pointer, build_index
from retrieval.app.services.retrieval_error import RetrievalServiceError
from retrieval.app.services.search import search


DEFAULT_TOPICS = [
    "анализ данных",
    "информационная безопасность",
    "облачные технологии",
    "управление проектами",
    "машинное обучение",
    "корпоративная архитектура",
    "разработка программного обеспечения",
    "сетевые протоколы",
    "базы данных",
    "цифровая трансформация",
]

SMOKE_SNAPSHOT_SHA = "a" * 40
STALE_SNAPSHOT_SHA = "b" * 40


def _topic_slug(topic: str) -> str:
    return topic.replace(" ", "_").replace("/", "_")


def _document_path(topic: str, sensitivity: str) -> str:
    prefix = "docs/ru" if sensitivity == "public" else "secret/ru"
    return f"{prefix}/{_topic_slug(topic)}.md"


def _document_content(topic: str, sensitivity: str) -> str:
    if sensitivity == "public":
        return (
            f"Этот документ посвящен {topic}. "
            f"Здесь описаны основные понятия, методы и примеры использования {topic} "
            f"в корпоративной среде."
        )
    return (
        f"Секретный документ по {topic}. "
        f"Содержит конфиденциальные данные, внутренние метрики и ограниченные "
        f"сведения о {topic}."
    )


def _topic_sha(topic: str, sensitivity: str) -> str:
    import hashlib

    digest = hashlib.sha1(f"{topic}:{sensitivity}".encode()).hexdigest()
    return digest[:40]


def build_synthetic_corpus(size: int) -> dict[str, str]:
    """Return a path -> content mapping for ``size`` Russian topics."""
    documents: dict[str, str] = {}
    for topic in DEFAULT_TOPICS[:size]:
        for sensitivity in ("public", "secret"):
            path = _document_path(topic, sensitivity)
            documents[path] = _document_content(topic, sensitivity)
    return documents


def build_go_state(
    space_id: str,
    snapshot_sha: str,
    documents: dict[str, str],
) -> dict[tuple[str, ...], Any]:
    """Populate a StubGOClient state dict for the synthetic corpus."""
    state: dict[tuple[str, ...], Any] = {
        ("tree", space_id, snapshot_sha): [
            {"path": path, "type": "blob", "sha": _topic_sha(topic_from_path(path), path)}
            for path in documents
        ],
        ("branch", space_id, "main"): {"commit": {"id": snapshot_sha}},
    }
    for path, content in documents.items():
        state[("doc", space_id, path, snapshot_sha)] = content
    return state


def topic_from_path(path: str) -> str:
    """Infer the original topic from a synthetic document path."""
    filename = path.split("/")[-1]
    slug = filename.replace(".md", "")
    return slug.replace("_", " ")


def build_acl_matrix() -> dict[str, dict[str, Any]]:
    """Return actor configurations for the benchmark ACL matrix."""
    return {
        "reader": {
            "actor_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
            "allowed_prefixes": ["/docs"],
        },
        "approver": {
            "actor_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
            "allowed_prefixes": ["/docs", "/secret"],
        },
        "outsider": {
            "actor_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
            "allowed_prefixes": ["/none"],
        },
    }


def build_identity_client(
    documents: dict[str, str],
    acl_matrix: dict[str, dict[str, Any]],
) -> StubIdentityClient:
    """Build a stub identity client with per-actor path-level approvals."""
    state: dict[tuple[str, ...], Any] = {}
    for config in acl_matrix.values():
        actor_id = config["actor_id"]
        allowed = config["allowed_prefixes"]
        for path in documents:
            # The production search code authorizes against "/" + document_path.
            check_path = "/" + path
            approved = any(path.startswith(p.lstrip("/")) for p in allowed)
            state[("check", "benchmark-space", str(actor_id), check_path)] = {
                "approved": approved,
                "space_id": "benchmark-space",
                "actor_id": str(actor_id),
                "path": check_path,
                "matched_prefix": allowed[0] if approved else None,
                "reason": "stub-benchmark-path",
            }
    return StubIdentityClient(state=state, allowed_prefixes=[])


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = int((percentile / 100.0) * (len(sorted_values) - 1))
    return sorted_values[idx]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_benchmark() -> dict[str, Any]:
    """Execute the synthetic benchmark and return the report dictionary."""
    k = settings.BENCHMARK_K
    corpus_size = settings.BENCHMARK_CORPUS_SIZE
    mode = settings.BENCHMARK_MODE
    output_path = Path(settings.BENCHMARK_OUTPUT_PATH)

    if corpus_size > len(DEFAULT_TOPICS):
        raise ValueError(
            f"BENCHMARK_CORPUS_SIZE ({corpus_size}) exceeds available topics "
            f"({len(DEFAULT_TOPICS)})."
        )
    if not settings.BENCHMARK_OUTPUT_PATH:
        raise ValueError("BENCHMARK_OUTPUT_PATH must not be empty.")

    documents = build_synthetic_corpus(corpus_size)
    acl_matrix = build_acl_matrix()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=None,  # type: ignore[arg-type]
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        embedding_adapter = build_embedding_adapter(settings)
        go_client = StubGOClient(
            state=build_go_state("benchmark-space", SMOKE_SNAPSHOT_SHA, documents)
        )
        identity_client = build_identity_client(documents, acl_matrix)

        generation = build_index(
            db, go_client, embedding_adapter, "benchmark-space", SMOKE_SNAPSHOT_SHA
        )
        activate_pointer(db, "benchmark-space", "default", generation.id, 0)
        db.commit()

        reader_id = acl_matrix["reader"]["actor_id"]
        approver_id = acl_matrix["approver"]["actor_id"]
        outsider_id = acl_matrix["outsider"]["actor_id"]

        golden_queries: list[dict[str, Any]] = []
        for topic in DEFAULT_TOPICS[:corpus_size]:
            query = f"документ посвящен {topic}"
            public_path = _document_path(topic, "public")
            secret_path = _document_path(topic, "secret")
            golden_queries.append(
                {
                    "query": query,
                    "actor_role": "reader",
                    "actor_id": reader_id,
                    "relevant": [public_path],
                }
            )
            golden_queries.append(
                {
                    "query": query,
                    "actor_role": "approver",
                    "actor_id": approver_id,
                    "relevant": [public_path, secret_path],
                }
            )

        query_count = settings.BENCHMARK_QUERY_COUNT
        if query_count == 0:
            raise ValueError("BENCHMARK_QUERY_COUNT must be -1 or positive.")
        if query_count >= 0:
            golden_queries = golden_queries[:query_count]

        per_query_results: list[dict[str, Any]] = []
        latencies_ms: list[float] = []
        unauthorized_filter_pass = True

        for item in golden_queries:
            start = time.perf_counter()
            response = search(
                db,
                identity_client,
                embedding_adapter,
                "benchmark-space",
                item["query"],
                item["actor_id"],
                profile="default",
                mode=mode,
                top_k=k,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies_ms.append(elapsed_ms)

            retrieved = [r["document_path"] for r in response["results"]]
            relevant = item["relevant"]

            retrieved_relevant = set(retrieved[:k]) & set(relevant)
            recall = len(retrieved_relevant) / len(relevant) if relevant else 0.0

            mrr = 0.0
            for rank, path in enumerate(retrieved[:k], start=1):
                if path in relevant:
                    mrr = 1.0 / rank
                    break

            per_query_results.append(
                {
                    "query": item["query"],
                    "actor_role": item["actor_role"],
                    "retrieved": retrieved,
                    "relevant": relevant,
                    "recall@k": recall,
                    "mrr": mrr,
                    "latency_ms": round(elapsed_ms, 3),
                }
            )

            if item["actor_role"] == "reader":
                for path in retrieved:
                    if path.startswith("secret/"):
                        unauthorized_filter_pass = False

        sorted_latencies = sorted(latencies_ms)
        avg_recall = _mean([r["recall@k"] for r in per_query_results])
        avg_mrr = _mean([r["mrr"] for r in per_query_results])
        p95_latency_ms = _percentile(sorted_latencies, 95.0)
        mean_latency_ms = _mean(latencies_ms)

        # Empty-corpus edge case.
        empty_space = "benchmark-empty-space"
        empty_state = {
            ("tree", empty_space, SMOKE_SNAPSHOT_SHA): [],
            ("branch", empty_space, "main"): {"commit": {"id": SMOKE_SNAPSHOT_SHA}},
        }
        empty_go = StubGOClient(state=empty_state)
        empty_generation = build_index(
            db, empty_go, embedding_adapter, empty_space, SMOKE_SNAPSHOT_SHA
        )
        activate_pointer(db, empty_space, "default", empty_generation.id, 0)
        db.commit()
        empty_response = search(
            db,
            identity_client,
            embedding_adapter,
            empty_space,
            "документ посвящен анализ данных",
            reader_id,
            profile="default",
            mode=mode,
            top_k=k,
        )
        empty_corpus_pass = empty_response["results"] == []

        # Stale-cursor edge case.
        stale_error: dict[str, Any] | None = None
        try:
            search(
                db,
                identity_client,
                embedding_adapter,
                "benchmark-space",
                "документ посвящен анализ данных",
                reader_id,
                profile="default",
                mode=mode,
                top_k=k,
                cursor=STALE_SNAPSHOT_SHA,
            )
        except RetrievalServiceError as exc:
            stale_error = {"code": exc.code, "message": exc.message}
        stale_cursor_pass = bool(stale_error and stale_error.get("code") == "STALE_SNAPSHOT")

        # Outsider edge case.
        outsider_response = search(
            db,
            identity_client,
            embedding_adapter,
            "benchmark-space",
            "документ посвящен анализ данных",
            outsider_id,
            profile="default",
            mode=mode,
            top_k=k,
        )
        outsider_filter_pass = outsider_response["results"] == []

        metrics = {
            "recall@k": round(avg_recall, 4),
            "mrr": round(avg_mrr, 4),
        "p95_latency_ms": round(p95_latency_ms, 3),
        "mean_latency_ms": round(mean_latency_ms, 3),
        "p95_method": "nearest-rank (conservative for small samples)",
            "queries_run": len(per_query_results),
            "k": k,
            "mode": mode,
            "corpus_size": corpus_size,
        }

        thresholds = {
            "recall@k": settings.BENCHMARK_RECALL_THRESHOLD,
            "mrr": settings.BENCHMARK_MRR_THRESHOLD,
            "p95_latency_ms": settings.BENCHMARK_P95_MS_THRESHOLD,
        }

        metrics_pass = (
            avg_recall >= thresholds["recall@k"]
            and avg_mrr >= thresholds["mrr"]
            and p95_latency_ms <= thresholds["p95_latency_ms"]
        )
        overall_pass = (
            metrics_pass
            and unauthorized_filter_pass
            and empty_corpus_pass
            and stale_cursor_pass
            and outsider_filter_pass
        )

        report: dict[str, Any] = {
            "title": "Phase B synthetic retrieval benchmark",
            "synthetic": True,
            "live_blocked": True,
            "generated_at": datetime.now(UTC).isoformat(),
            "config": {
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dimensions": settings.EMBEDDING_DIMENSIONS,
                "database": "sqlite:///:memory:",
                "k": k,
                "mode": mode,
                "corpus_size": corpus_size,
                "query_count": len(per_query_results),
                "thresholds": thresholds,
            },
            "metrics": metrics,
            "edge_cases": {
                "empty_corpus": {"passed": empty_corpus_pass},
                "stale_cursor": {"passed": stale_cursor_pass, "error": stale_error},
                "unauthorized_filter": {"passed": unauthorized_filter_pass},
                "outsider_filter": {"passed": outsider_filter_pass},
            },
            "per_query": per_query_results,
            "pass": overall_pass,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

        return report

    finally:
        db.close()
        Base.metadata.drop_all(engine)


def main() -> int:
    print("Running synthetic ACL-aware Russian retrieval benchmark...")
    report = run_benchmark()

    print(f"  embedding model: {report['config']['embedding_model']}")
    print(f"  mode: {report['config']['mode']}")
    print(f"  queries: {report['metrics']['queries_run']}")
    print(f"  recall@{report['metrics']['k']}: {report['metrics']['recall@k']}")
    print(f"  MRR: {report['metrics']['mrr']}")
    print(f"  p95 latency: {report['metrics']['p95_latency_ms']} ms")
    print(f"  output: {settings.BENCHMARK_OUTPUT_PATH}")
    print(f"  PASS: {report['pass']}")

    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
