"""Factory for the shared ObjectStore protocol."""

from __future__ import annotations

from typing import Any

from .minio_store import MinioObjectStore
from .store import InMemoryObjectStore, ObjectStore


def build_object_store(
    *,
    endpoint: str = "",
    access_key: str = "",
    secret_key: str = "",
    bucket: str = "kb-ingest",
    secure: bool = False,
    client: Any | None = None,
) -> ObjectStore:
    """Return MinIO when a client or endpoint is provided, else in-memory."""
    if client is not None:
        return MinioObjectStore(bucket, client)
    if not endpoint:
        return InMemoryObjectStore()
    from minio import Minio

    minio_client = Minio(
        endpoint,
        access_key=access_key or None,
        secret_key=secret_key or None,
        secure=secure,
    )
    return MinioObjectStore(bucket, minio_client)
