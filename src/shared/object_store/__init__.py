"""Shared object-store primitives for kb-ingestion and backup hashing."""

from .factory import build_object_store
from .hashing import object_key, sha256_hex
from .minio_store import MinioObjectStore
from .store import InMemoryObjectStore, ObjectStore, ObjectStoreError, StagedObject

__all__ = [
    "InMemoryObjectStore",
    "MinioObjectStore",
    "ObjectStore",
    "ObjectStoreError",
    "StagedObject",
    "build_object_store",
    "object_key",
    "sha256_hex",
]
