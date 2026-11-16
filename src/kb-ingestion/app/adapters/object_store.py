"""kb-ingestion re-export of shared object-store adapter."""

from shared.object_store import InMemoryObjectStore, ObjectStore, ObjectStoreError, StagedObject

__all__ = ["InMemoryObjectStore", "ObjectStore", "ObjectStoreError", "StagedObject"]