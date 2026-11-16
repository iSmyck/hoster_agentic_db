"""Shared object-store primitives for kb-ingestion and backup staging."""

from .store import InMemoryObjectStore, ObjectStore, ObjectStoreError, StagedObject

__all__ = [
    "InMemoryObjectStore",
    "ObjectStore",
    "ObjectStoreError",
    "StagedObject",
]