"""Object-store port and in-memory stub for convert staging."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ObjectStoreError(Exception):
    """Raised when staging storage fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class StagedObject:
    """Metadata for a staged raw upload."""

    object_id: str
    sha256: str
    version_id: str
    size: int
    media_type: str


class ObjectStore(ABC):
    """Outbound port for immutable raw-file staging."""

    @abstractmethod
    def put(
        self,
        space_id: str,
        client_id: str,
        object_id: str,
        data: bytes,
        media_type: str,
    ) -> StagedObject:
        """Persist bytes and return staging metadata."""

    @abstractmethod
    def get(self, space_id: str, client_id: str, object_id: str) -> bytes | None:
        """Return staged bytes when present."""

    @abstractmethod
    def get_staged(self, space_id: str, client_id: str, object_id: str) -> StagedObject | None:
        """Return staging metadata when present."""

    @abstractmethod
    def count(self) -> int:
        """Return how many staged objects exist (for tests)."""


class InMemoryObjectStore(ObjectStore):
    """Deterministic in-memory store for unit and local tests."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str, str, str]] = {}
        self._versions: dict[str, int] = {}

    def _key(self, space_id: str, client_id: str, object_id: str) -> str:
        return f"{space_id}/{client_id}/{object_id}"

    def put(
        self,
        space_id: str,
        client_id: str,
        object_id: str,
        data: bytes,
        media_type: str,
    ) -> StagedObject:
        key = self._key(space_id, client_id, object_id)
        version_num = self._versions.get(key, 0) + 1
        self._versions[key] = version_num
        version_id = f"v{version_num}"
        digest = hashlib.sha256(data).hexdigest()
        self._objects[key] = (data, digest, version_id, media_type)
        return StagedObject(
            object_id=object_id,
            sha256=digest,
            version_id=version_id,
            size=len(data),
            media_type=media_type,
        )

    def get(self, space_id: str, client_id: str, object_id: str) -> bytes | None:
        key = self._key(space_id, client_id, object_id)
        entry = self._objects.get(key)
        if entry is None:
            return None
        return entry[0]

    def get_staged(self, space_id: str, client_id: str, object_id: str) -> StagedObject | None:
        key = self._key(space_id, client_id, object_id)
        entry = self._objects.get(key)
        if entry is None:
            return None
        data, digest, version_id, media_type = entry
        return StagedObject(
            object_id=object_id,
            sha256=digest,
            version_id=version_id,
            size=len(data),
            media_type=media_type,
        )

    def count(self) -> int:
        return len(self._objects)