"""Search business logic for semantic/exact/hybrid retrieval."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from retrieval.app.adapters.embeddings import (
    EmbeddingAdapter,
    EmbeddingAdapterError,
    cosine_similarity,
)
from retrieval.app.adapters.identity_client import IdentityClient, IdentityClientError
from retrieval.app.models.index import Chunk, SearchLog
from retrieval.app.services import indexing
from retrieval.app.services.retrieval_error import RetrievalServiceError

QUERY_CHUNK_LIMIT = 1000


def _to_floats(value: Any) -> list[float]:
    """Normalize an embedding value from pgvector or JSON to a float list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [float(v) for v in value]
    # pgvector returns a string representation in some drivers.
    if isinstance(value, str):
        return [float(v) for v in value.strip("{}[]").split(",") if v]
    return list(value)


def _exact_score(query: str, content: str) -> float:
    """Simple keyword overlap score for exact fallback."""
    query_terms = query.lower().split()
    content_lower = content.lower()
    if not query_terms:
        return 0.0
    matches = sum(1 for term in query_terms if term in content_lower)
    return matches / len(query_terms)


def _rank_chunks(
    chunks: list[Chunk],
    query: str,
    query_embedding: list[float],
    mode: str,
) -> list[tuple[Chunk, float, str]]:
    """Return chunks annotated with score and contributing mode."""
    scored: list[tuple[Chunk, float, str]] = []
    for chunk in chunks:
        semantic_score = 0.0
        exact_score = 0.0

        if mode in ("semantic", "hybrid"):
            vector = _to_floats(chunk.embedding)
            semantic_score = cosine_similarity(query_embedding, vector)

        if mode in ("exact", "hybrid"):
            exact_score = _exact_score(query, chunk.content)

        if mode == "semantic":
            score = semantic_score
        elif mode == "exact":
            score = exact_score
        else:
            # Weighted hybrid: 70 % semantic, 30 % exact overlap.
            score = 0.7 * semantic_score + 0.3 * exact_score

        if score > 0:
            scored.append((chunk, score, mode))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def search(
    db: Session,
    identity_client: IdentityClient,
    embedding_adapter: EmbeddingAdapter,
    space_id: str,
    query: str,
    actor_id: uuid.UUID,
    profile: str = "default",
    mode: str = "hybrid",
    top_k: int = 10,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Execute an authorized search against the active published index.

    Per-payload re-authorization is performed for every candidate chunk via
    the Identity/AuthZ service before it is returned.

    A ``cursor`` bound to a stale generation or snapshot causes
    ``STALE_SNAPSHOT`` so callers cannot silently read from a superseded index.
    """
    generation = indexing.get_active_generation(db, space_id, profile)
    if generation is None:
        raise RetrievalServiceError("INDEX_NOT_READY", "no active index for space/profile")

    if cursor is not None and cursor != "" and cursor not in (str(generation.id), generation.snapshot_sha):
        raise RetrievalServiceError(
            "STALE_SNAPSHOT",
            "cursor is bound to a generation that is no longer active",
        )

    query_embedding: list[float] = []
    if mode in ("semantic", "hybrid"):
        try:
            query_embedding = embedding_adapter.encode([query])[0]
        except EmbeddingAdapterError as exc:
            raise RetrievalServiceError(
                "UPSTREAM_UNAVAILABLE",
                f"embedding generation failed: {exc}",
            ) from exc

    if mode == "semantic" and db.bind is not None and db.bind.dialect.name != "sqlite":
        chunks = (
            db.query(Chunk)
            .filter(Chunk.generation_id == generation.id)
            .order_by(Chunk.embedding.op("<=>")(query_embedding))
            .limit(QUERY_CHUNK_LIMIT)
            .all()
        )
    else:
        chunks = (
            db.query(Chunk)
            .filter(Chunk.generation_id == generation.id)
            .limit(QUERY_CHUNK_LIMIT)
            .all()
        )

    scored = _rank_chunks(chunks, query, query_embedding, mode)

    results: list[dict[str, Any]] = []
    authorization_filtered_count = 0
    for chunk, score, result_mode in scored:
        path = chunk.document_path
        try:
            authz_response = identity_client.check_path(
                space_id=space_id,
                actor_id=actor_id,
                path="/" + path,
            )
        except IdentityClientError as exc:
            raise RetrievalServiceError(
                "UPSTREAM_UNAVAILABLE",
                f"identity check failed: {exc}",
            ) from exc
        if not authz_response.get("approved"):
            authorization_filtered_count += 1
            continue

        results.append({
            "chunk_id": chunk.id,
            "document_path": path,
            "content": chunk.content,
            "score": round(score, 6),
            "mode": result_mode,
            "metadata": chunk.chunk_metadata,
        })
        if len(results) >= top_k:
            break

    log = SearchLog(
        space_id=space_id,
        query=query,
        profile=profile,
        results_count=len(results),
        actor_id=str(actor_id),
    )
    db.add(log)
    db.flush()

    return {
        "space_id": space_id,
        "query": query,
        "profile": profile,
        "generation_id": generation.id,
        "snapshot_sha": generation.snapshot_sha,
        "results": results,
        "authorization_filtered_count": authorization_filtered_count,
    }
