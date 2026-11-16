"""MinIO adapter for the shared ingestion ObjectStore protocol."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from .hashing import object_key, sha256_hex
from .store import ObjectStore, ObjectStoreError, StagedObject


class MinioObjectStore(ObjectStore):
    """ObjectStore backed by a MinIO/S3-compatible client.

    Version ids are tracked in-process (``vN``) so the ingestion protocol stays
    independent of backup's bucket-versioning API. ``client`` is injected so
    unit tests never need a live endpoint.
    """

    def __init__(self, bucket: str, client: Any) -> None:
        self._bucket = bucket
        self._client = client
        self._versions: dict[str, int] = {}
        self._meta: dict[str, StagedObject] = {}
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            exists = self._client.bucket_exists(self._bucket)
        except Exception as exc:
            raise ObjectStoreError("OBJECT_STORE_UNAVAILABLE", str(exc)) from exc
        if exists:
            return
        try:
            self._client.make_bucket(self._bucket)
        except Exception as exc:
            raise ObjectStoreError("OBJECT_STORE_UNAVAILABLE", str(exc)) from exc

    def put(
        self,
        space_id: str,
        client_id: str,
        object_id: str,
        data: bytes,
        media_type: str,
    ) -> StagedObject:
        key = object_key(space_id, client_id, object_id)
        digest = sha256_hex(data)
        try:
            self._client.put_object(
                self._bucket,
                key,
                BytesIO(data),
                length=len(data),
                content_type=media_type,
            )
        except Exception as exc:
            raise ObjectStoreError("OBJECT_STORE_PUT_FAILED", str(exc)) from exc
        version_num = self._versions.get(key, 0) + 1
        self._versions[key] = version_num
        staged = StagedObject(
            object_id=object_id,
            sha256=digest,
            version_id=f"v{version_num}",
            size=len(data),
            media_type=media_type,
        )
        self._meta[key] = staged
        return staged

    def get(self, space_id: str, client_id: str, object_id: str) -> bytes | None:
        key = object_key(space_id, client_id, object_id)
        response = None
        try:
            response = self._client.get_object(self._bucket, key)
            return response.read()
        except Exception:  # noqa: BLE001 — MinIO/S3 miss and stub KeyError both map to None
            return None
        finally:
            if response is not None:
                closer = getattr(response, "close", None)
                if closer is not None:
                    closer()
                release = getattr(response, "release_conn", None)
                if release is not None:
                    release()

    def get_staged(self, space_id: str, client_id: str, object_id: str) -> StagedObject | None:
        return self._meta.get(object_key(space_id, client_id, object_id))

    def count(self) -> int:
        return len(self._meta)
