"""Object-store staging service: file upload and assets manifest."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from backup.app.adapters.object_store import ObjectStoreAdapter, ObjectStoreAdapterError
from backup.app.models.backup import AssetsManifest, ObjectStoreEntry

logger = logging.getLogger(__name__)


class ObjectStoreServiceError(Exception):
    """Raised when an object-store service operation fails."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ObjectStoreService:
    """Staging service for object-store assets."""

    def __init__(self, adapter: ObjectStoreAdapter) -> None:
        self.adapter = adapter

    def stage_file(
        self,
        space_id: str,
        filename: str,
        content: bytes,
        media_type: str | None = None,
        source_ref: str | None = None,
    ) -> ObjectStoreEntry:
        """Upload a file to object-store staging.

        Returns an immutable entry with object_id, version, sha256 and size.
        """
        object_id = self._derive_object_id(filename)
        try:
            entry = self.adapter.upload(
                space_id=space_id,
                object_id=object_id,
                data=content,
                media_type=media_type,
                source_ref=source_ref,
            )
        except ObjectStoreAdapterError as exc:
            logger.exception("object store upload failed for space_id=%s", space_id)
            raise ObjectStoreServiceError("OBJECT_STORE_ERROR", str(exc)) from exc

        return ObjectStoreEntry(
            object_id=entry.object_id,
            version=entry.version,
            sha256=entry.sha256,
            size=entry.size,
            media_type=entry.media_type,
            source_ref=entry.source_ref,
        )

    def build_assets_manifest(self, space_id: str) -> AssetsManifest:
        """Build an assets manifest listing all staged objects for a Space."""
        try:
            entries = self.adapter.list_objects(space_id)
        except ObjectStoreAdapterError as exc:
            logger.exception("object store list failed for space_id=%s", space_id)
            raise ObjectStoreServiceError("OBJECT_STORE_ERROR", str(exc)) from exc

        return AssetsManifest(
            space_id=space_id,
            objects=[
                ObjectStoreEntry(
                    object_id=e.object_id,
                    version=e.version,
                    sha256=e.sha256,
                    size=e.size,
                    media_type=e.media_type,
                    source_ref=e.source_ref,
                )
                for e in entries
            ],
        )

    def get_object_content(
        self, space_id: str, object_id: str, version: str | None = None
    ) -> bytes:
        """Return the content of an object version."""
        try:
            return self.adapter.get_object(space_id, object_id, version)
        except ObjectStoreAdapterError as exc:
            logger.exception("object store get failed for %s@%s", object_id, version)
            raise ObjectStoreServiceError("OBJECT_STORE_ERROR", str(exc)) from exc

    def list_object_versions(self, space_id: str, object_id: str) -> list[ObjectStoreEntry]:
        """List all versions of a staged object."""
        try:
            entries = self.adapter.list_object_versions(space_id, object_id)
        except ObjectStoreAdapterError as exc:
            logger.exception("object store list versions failed for %s", object_id)
            raise ObjectStoreServiceError("OBJECT_STORE_ERROR", str(exc)) from exc

        return [
            ObjectStoreEntry(
                object_id=e.object_id,
                version=e.version,
                sha256=e.sha256,
                size=e.size,
                media_type=e.media_type,
                source_ref=e.source_ref,
            )
            for e in entries
        ]

    @staticmethod
    def _derive_object_id(filename: str) -> str:
        """Generate an opaque object id from a filename."""
        base = Path(filename).name or "unnamed"
        suffix = uuid.uuid4().hex[:12]
        return f"{suffix}-{base}"
