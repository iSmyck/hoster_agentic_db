"""Object-store adapter port and MinIO implementation for backup staging."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Any


class ObjectStoreAdapterError(Exception):
    """Raised when an object-store adapter operation fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        s3_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.s3_code = s3_code


class ObjectStoreEntry:
    """Immutable object metadata returned by the adapter."""

    def __init__(
        self,
        object_id: str,
        version: str,
        sha256: str,
        size: int,
        media_type: str | None = None,
        source_ref: str | None = None,
    ) -> None:
        self.object_id = object_id
        self.version = version
        self.sha256 = sha256
        self.size = size
        self.media_type = media_type
        self.source_ref = source_ref

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "version": self.version,
            "sha256": self.sha256,
            "size": self.size,
            "media_type": self.media_type,
            "source_ref": self.source_ref,
        }


class ObjectStoreAdapter(ABC):
    """Outbound port for read-only/object-store interactions used by backup."""

    @abstractmethod
    def upload(
        self,
        space_id: str,
        object_id: str,
        data: bytes,
        media_type: str | None = None,
        source_ref: str | None = None,
    ) -> ObjectStoreEntry:
        """Store an object and return its immutable metadata."""

    @abstractmethod
    def list_objects(self, space_id: str) -> list[ObjectStoreEntry]:
        """List current objects for a Space."""

    @abstractmethod
    def get_object(self, space_id: str, object_id: str, version: str | None = None) -> bytes:
        """Return the content of an object version."""

    @abstractmethod
    def list_object_versions(self, space_id: str, object_id: str) -> list[ObjectStoreEntry]:
        """List all versions of an object."""


class MinioObjectStoreAdapter(ObjectStoreAdapter):
    """MinIO/S3-backed object-store adapter.

    Uses a single bucket with ``space_id/`` prefixes to simplify sandbox usage.
    Versioning is used when enabled on the bucket; otherwise ``etag`` is used as
    the version identifier.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        use_ssl: bool = False,
    ) -> None:
        from minio import Minio

        self.bucket = bucket
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=use_ssl,
        )
        self._ensure_bucket()

    def _object_key(self, space_id: str, object_id: str) -> str:
        return f"{space_id}/{object_id}"

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload(
        self,
        space_id: str,
        object_id: str,
        data: bytes,
        media_type: str | None = None,
        source_ref: str | None = None,
    ) -> ObjectStoreEntry:
        from minio.error import S3Error

        key = self._object_key(space_id, object_id)
        sha256 = hashlib.sha256(data).hexdigest()
        metadata: dict[str, str] = {"sha256": sha256}
        if source_ref is not None:
            metadata["source_ref"] = source_ref
        try:
            from io import BytesIO

            self.client.put_object(
                self.bucket,
                key,
                BytesIO(data),
                length=len(data),
                content_type=media_type or "application/octet-stream",
                metadata=metadata,
            )
            stat = self.client.stat_object(self.bucket, key)
            version = stat.version_id or stat.etag or "null"
            return ObjectStoreEntry(
                object_id=object_id,
                version=version,
                sha256=sha256,
                size=len(data),
                media_type=media_type,
                source_ref=source_ref,
            )
        except S3Error as exc:
            raise ObjectStoreAdapterError(
                str(exc), status_code=getattr(exc, "http_status", None), s3_code=exc.code
            ) from exc
        except Exception as exc:
            raise ObjectStoreAdapterError(str(exc)) from exc

    def list_objects(self, space_id: str) -> list[ObjectStoreEntry]:
        from minio.error import S3Error

        prefix = f"{space_id}/"
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            return [self._entry_from_object(obj) for obj in objects]
        except S3Error as exc:
            raise ObjectStoreAdapterError(
                str(exc), status_code=getattr(exc, "http_status", None), s3_code=exc.code
            ) from exc
        except Exception as exc:
            raise ObjectStoreAdapterError(str(exc)) from exc

    def get_object(self, space_id: str, object_id: str, version: str | None = None) -> bytes:
        from minio.error import S3Error

        key = self._object_key(space_id, object_id)
        try:
            response = self.client.get_object(
                self.bucket,
                key,
                version_id=version if version and version != "null" else None,
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as exc:
            raise ObjectStoreAdapterError(
                str(exc), status_code=getattr(exc, "http_status", None), s3_code=exc.code
            ) from exc
        except Exception as exc:
            raise ObjectStoreAdapterError(str(exc)) from exc

    def list_object_versions(self, space_id: str, object_id: str) -> list[ObjectStoreEntry]:
        from minio.error import S3Error

        key = self._object_key(space_id, object_id)
        try:
            versions = self.client.list_objects(
                self.bucket, prefix=key, recursive=False, include_version=True
            )
            return [self._entry_from_object(v) for v in versions if v.object_name == key]
        except S3Error as exc:
            raise ObjectStoreAdapterError(
                str(exc), status_code=getattr(exc, "http_status", None), s3_code=exc.code
            ) from exc
        except Exception as exc:
            raise ObjectStoreAdapterError(str(exc)) from exc

    def _entry_from_object(self, obj: Any) -> ObjectStoreEntry:
        object_id = obj.object_name.removeprefix(f"{obj.object_name.split('/')[0]}/")
        meta = obj.metadata or {}
        sha256 = (
            meta.get("sha256")
            or meta.get("Sha256")
            or meta.get("X-Amz-Meta-Sha256")
            or meta.get("x-amz-meta-sha256")
            or ""
        )
        if not sha256:
            raise ObjectStoreAdapterError(
                "MISSING_SHA256_METADATA",
                status_code=500,
            )
        source_ref = (
            meta.get("source_ref")
            or meta.get("Source_ref")
            or meta.get("X-Amz-Meta-Source_ref")
            or meta.get("x-amz-meta-source_ref")
            or None
        )
        return ObjectStoreEntry(
            object_id=object_id,
            version=obj.version_id or obj.etag or "null",
            sha256=sha256,
            size=obj.size,
            media_type=obj.content_type,
            source_ref=source_ref,
        )


class StubObjectStoreAdapter(ObjectStoreAdapter):
    """In-memory stub adapter for unit tests."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, ObjectStoreEntry]] = {}
        self._content: dict[tuple[str, str, str], bytes] = {}

    def upload(
        self,
        space_id: str,
        object_id: str,
        data: bytes,
        media_type: str | None = None,
        source_ref: str | None = None,
    ) -> ObjectStoreEntry:
        sha256 = hashlib.sha256(data).hexdigest()
        version = f"v{len(self._content) + 1}"
        entry = ObjectStoreEntry(
            object_id=object_id,
            version=version,
            sha256=sha256,
            size=len(data),
            media_type=media_type,
            source_ref=source_ref,
        )
        self._store.setdefault(space_id, {})[object_id] = entry
        self._content[(space_id, object_id, version)] = data
        return entry

    def list_objects(self, space_id: str) -> list[ObjectStoreEntry]:
        return list(self._store.get(space_id, {}).values())

    def get_object(self, space_id: str, object_id: str, version: str | None = None) -> bytes:
        candidates = [
            (v, data)
            for (s, o, v), data in self._content.items()
            if s == space_id and o == object_id and (version is None or v == version)
        ]
        if not candidates:
            raise ObjectStoreAdapterError(f"object not found: {space_id}/{object_id}@{version}")
        if version is None:
            return max(candidates, key=lambda item: item[0])[1]
        return candidates[0][1]

    def list_object_versions(self, space_id: str, object_id: str) -> list[ObjectStoreEntry]:
        entries: list[ObjectStoreEntry] = []
        for (s, o, v), data in self._content.items():
            if s == space_id and o == object_id:
                entries.append(
                    ObjectStoreEntry(
                        object_id=object_id,
                        version=v,
                        sha256=hashlib.sha256(data).hexdigest(),
                        size=len(data),
                    )
                )
        return entries
