"""Indexing business logic for building and activating index generations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from retrieval.app.adapters.embeddings import EmbeddingAdapter, EmbeddingAdapterError
from retrieval.app.adapters.go_client import GOClient, GOClientError
from retrieval.app.models.index import Chunk, IndexGeneration, IndexPointer
from retrieval.app.services.retrieval_error import RetrievalServiceError


def _next_generation_order(db: Session, space_id: str) -> int:
    """Return the next monotonic ordering value for a Space."""
    max_order = (
        db.query(func.max(IndexGeneration.ordering))
        .filter(IndexGeneration.space_id == space_id)
        .scalar()
    )
    return (max_order or 0) + 1


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by words."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
        if start <= 0:
            break
    return chunks


def build_index(
    db: Session,
    go_client: GOClient,
    embedding_adapter: EmbeddingAdapter,
    space_id: str,
    snapshot_sha: str,
) -> IndexGeneration:
    """Build a new index generation from an exact Git snapshot.

    Fetches the tree from the Git Orchestrator, reads every blob document,
    chunks and embeds the content, then stores the generation and its chunks.
    """
    try:
        entries = go_client.get_tree(space_id, snapshot_sha)
    except GOClientError as exc:
        raise RetrievalServiceError("UPSTREAM_UNAVAILABLE", f"tree read failed: {exc}") from exc

    blobs = [e for e in entries if e.get("type") == "blob"]

    ordering = _next_generation_order(db, space_id)
    generation = IndexGeneration(
        space_id=space_id,
        snapshot_sha=snapshot_sha,
        status="building",
        ordering=ordering,
        equivalence_evidence={"input_documents": len(blobs)},
    )
    db.add(generation)
    db.flush()

    chunk_documents: list[tuple[str, str, int]] = []
    for entry in blobs:
        path = entry["path"]
        try:
            content = go_client.read_document(space_id, path, snapshot_sha)
        except GOClientError as exc:
            raise RetrievalServiceError(
                "UPSTREAM_UNAVAILABLE",
                f"document read failed for {path}: {exc}",
            ) from exc
        chunks = _chunk_text(content)
        for idx, chunk_text in enumerate(chunks):
            chunk_documents.append((path, chunk_text, idx))

    if chunk_documents:
        texts = [text for _, text, _ in chunk_documents]
        try:
            embeddings = embedding_adapter.encode(texts)
        except EmbeddingAdapterError as exc:
            raise RetrievalServiceError(
                "UPSTREAM_UNAVAILABLE",
                f"embedding generation failed: {exc}",
            ) from exc
        try:
            for (path, text, idx), vector in zip(chunk_documents, embeddings, strict=True):
                db.add(
                    Chunk(
                        generation_id=generation.id,
                        document_path=path,
                        content=text,
                        embedding=vector,
                        chunk_metadata={"chunk_index": idx, "snapshot_sha": snapshot_sha},
                    )
                )
        except ValueError as exc:
            raise RetrievalServiceError(
                "UPSTREAM_UNAVAILABLE",
                f"embedding count mismatch: expected {len(chunk_documents)}, got {len(embeddings)}",
            ) from exc

    generation.status = "ready"
    generation.equivalence_evidence = {
        "input_documents": len(blobs),
        "chunks": len(chunk_documents),
    }
    db.flush()
    return generation


def activate_pointer(
    db: Session,
    space_id: str,
    profile: str,
    generation_id: uuid.UUID,
    fence_token: int,
) -> IndexPointer:
    """CAS-activate ``generation_id`` as the serving generation for a profile.

    The supplied ``fence_token`` must match the currently active pointer's
    fence token. On success the old pointer is deactivated and a new pointer
    with an incremented fence token is inserted.
    """
    generation = db.get(IndexGeneration, generation_id)
    if generation is None:
        raise RetrievalServiceError("NOT_FOUND", "generation not found")
    if str(generation.space_id) != space_id:
        raise RetrievalServiceError("INVALID_STATE", "generation belongs to a different space")

    active_pointer = (
        db.query(IndexPointer)
        .filter(
            IndexPointer.space_id == space_id,
            IndexPointer.profile == profile,
            IndexPointer.active.is_(True),
        )
        .with_for_update()
        .first()
    )

    if active_pointer is not None:
        if active_pointer.fence_token != fence_token:
            raise RetrievalServiceError(
                "INDEX_GENERATION_CONFLICT",
                "fence token mismatch; pointer was updated concurrently",
            )
        if active_pointer.generation_id == generation_id:
            return active_pointer
    elif fence_token != 0:
        raise RetrievalServiceError(
            "INDEX_GENERATION_CONFLICT",
            "fence token mismatch; no active pointer for space/profile",
        )

    if generation.status != "ready":
        raise RetrievalServiceError("INVALID_STATE", f"generation status is {generation.status}")

    if active_pointer is not None:
        active_pointer.active = False

    new_pointer = IndexPointer(
        space_id=space_id,
        profile=profile,
        generation_id=generation_id,
        active=True,
        fence_token=fence_token + 1,
    )
    db.add(new_pointer)
    generation.status = "active"
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise RetrievalServiceError(
            "INDEX_GENERATION_CONFLICT",
            "pointer was updated concurrently",
        ) from exc
    return new_pointer


def get_active_pointer(
    db: Session,
    space_id: str,
    profile: str,
) -> IndexPointer | None:
    """Return the active pointer for a Space/profile, or None."""
    return (
        db.query(IndexPointer)
        .filter(
            IndexPointer.space_id == space_id,
            IndexPointer.profile == profile,
            IndexPointer.active.is_(True),
        )
        .first()
    )


def get_active_generation(
    db: Session,
    space_id: str,
    profile: str,
) -> IndexGeneration | None:
    """Return the active generation for a Space/profile, or None."""
    pointer = get_active_pointer(db, space_id, profile)
    if pointer is None:
        return None
    return db.get(IndexGeneration, pointer.generation_id)


def reconcile_index_with_head(
    db: Session,
    go_client: GOClient,
    space_id: str,
    profile: str = "default",
    branch: str = "main",
) -> dict[str, Any]:
    """Compare the active index snapshot with the current branch HEAD.

    Returns a reconciliation report indicating whether the index is stale,
    up-to-date, or no index is active.  Used by CI and operational runbooks
    to detect drift between published content and retrieval state.
    """
    pointer = get_active_pointer(db, space_id, profile)
    if pointer is None:
        return {
            "space_id": space_id,
            "profile": profile,
            "branch": branch,
            "status": "no_active_index",
            "index_snapshot_sha": None,
            "head_sha": None,
            "stale": False,
        }

    generation = db.get(IndexGeneration, pointer.generation_id)
    if generation is None:
        return {
            "space_id": space_id,
            "profile": profile,
            "branch": branch,
            "status": "generation_missing",
            "index_snapshot_sha": None,
            "head_sha": None,
            "stale": True,
        }

    head_sha = go_client.get_branch_head(space_id, branch)
    stale = generation.snapshot_sha != head_sha
    return {
        "space_id": space_id,
        "profile": profile,
        "branch": branch,
        "status": "stale" if stale else "up_to_date",
        "index_snapshot_sha": generation.snapshot_sha,
        "head_sha": head_sha,
        "stale": stale,
    }
