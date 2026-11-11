"""Unit tests for object-store adapter and staging service."""

from __future__ import annotations

import hashlib

import pytest

from backup.app.adapters.object_store import (
    ObjectStoreAdapterError,
    StubObjectStoreAdapter,
)
from backup.app.services.object_store import ObjectStoreService, ObjectStoreServiceError


@pytest.fixture
def adapter() -> StubObjectStoreAdapter:
    return StubObjectStoreAdapter()


@pytest.fixture
def service(adapter: StubObjectStoreAdapter) -> ObjectStoreService:
    return ObjectStoreService(adapter)


def test_stage_file_returns_entry(service: ObjectStoreService) -> None:
    content = b"hello object store"
    entry = service.stage_file("demo-space", "hello.txt", content, media_type="text/plain")

    assert entry.object_id.endswith("-hello.txt")
    assert entry.version.startswith("v")
    assert entry.sha256 == hashlib.sha256(content).hexdigest()
    assert entry.size == len(content)
    assert entry.media_type == "text/plain"


def test_build_assets_manifest(service: ObjectStoreService) -> None:
    service.stage_file("demo-space", "a.txt", b"aaa", media_type="text/plain")
    service.stage_file("demo-space", "b.txt", b"bbb", media_type="text/plain")

    manifest = service.build_assets_manifest("demo-space")

    assert manifest.space_id == "demo-space"
    assert len(manifest.objects) == 2
    assert {obj.size for obj in manifest.objects} == {3}


def test_build_assets_manifest_empty_space(service: ObjectStoreService) -> None:
    manifest = service.build_assets_manifest("empty-space")
    assert manifest.space_id == "empty-space"
    assert manifest.objects == []


def test_adapter_get_object(adapter: StubObjectStoreAdapter) -> None:
    service = ObjectStoreService(adapter)
    entry = service.stage_file("demo-space", "file.txt", b"content")
    data = adapter.get_object("demo-space", entry.object_id, entry.version)
    assert data == b"content"


def test_adapter_get_missing_object(adapter: StubObjectStoreAdapter) -> None:
    with pytest.raises(ObjectStoreAdapterError):
        adapter.get_object("demo-space", "missing", "v1")


def test_adapter_list_versions(adapter: StubObjectStoreAdapter) -> None:
    adapter.upload("demo-space", "file.txt", b"v1")
    adapter.upload("demo-space", "file.txt", b"v2")

    versions = adapter.list_object_versions("demo-space", "file.txt")

    assert len(versions) == 2


def test_service_error_wrapped(adapter: StubObjectStoreAdapter) -> None:
    def failing_upload(*args: object, **kwargs: object) -> None:
        raise ObjectStoreAdapterError("bucket missing", s3_code="NoSuchBucket")

    adapter.upload = failing_upload  # type: ignore[method-assign]
    service = ObjectStoreService(adapter)

    with pytest.raises(ObjectStoreServiceError) as exc_info:
        service.stage_file("demo-space", "file.txt", b"data")
    assert exc_info.value.code == "OBJECT_STORE_ERROR"


def test_source_ref_roundtrip(service: ObjectStoreService) -> None:
    entry = service.stage_file(
        "demo-space",
        "file.txt",
        b"content",
        media_type="text/plain",
        source_ref="https://example.com/file.txt",
    )

    versions = service.list_object_versions("demo-space", entry.object_id)
    assert len(versions) == 1
    assert versions[0].source_ref == "https://example.com/file.txt"


def test_service_get_object_content(service: ObjectStoreService) -> None:
    entry = service.stage_file("demo-space", "file.txt", b"service content")

    content = service.get_object_content("demo-space", entry.object_id, entry.version)

    assert content == b"service content"
