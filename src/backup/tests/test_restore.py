"""Unit tests for RestoreService with stub adapters and synthetic packages."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from backup.app.adapters.gitlab import StubBackupGitLabAdapter
from backup.app.adapters.object_store import ObjectStoreAdapter, ObjectStoreEntry
from backup.app.models.backup import (
    AssetsManifest,
    BackupManifest,
    FileHash,
)
from backup.app.models.backup import (
    ObjectStoreEntry as ObjectStoreEntryModel,
)
from backup.app.models.restore import RestoreRequest, RestoreStatus
from backup.app.services.postgres_backup import PostgresBackupService
from backup.app.services.restore import RestoreService, RestoreServiceError


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _create_package(
    tmp_path: Path,
    space_id: str,
    backup_id: str,
    with_postgres: bool = True,
    with_object_store: bool = True,
) -> Path:
    package = tmp_path / space_id / backup_id
    package.mkdir(parents=True)

    # Git mirror
    mirror_dir = package / "mirror.git"
    mirror_dir.mkdir()
    subprocess.run(["git", "init", "--bare", str(mirror_dir)], check=True, capture_output=True)

    files: list[FileHash] = []

    # Metadata
    metadata = {"space_id": space_id, "merge_requests": [], "notes": {}, "tags": [{"name": "v1"}]}
    _write_json(package / "metadata.json", metadata)
    files.append(FileHash(path="metadata.json", sha256=_sha256((package / "metadata.json").read_bytes())))

    # kb_ops
    kb_ops = {"space_id": space_id, "proposals": [], "decisions": [{"id": 1}]}
    _write_json(package / "kb_ops_export.json", kb_ops)
    files.append(FileHash(path="kb_ops_export.json", sha256=_sha256((package / "kb_ops_export.json").read_bytes())))

    if with_postgres:
        pg_dir = package / "postgres_export"
        pg_dir.mkdir()
        for schema in ["kb_authz", "kb_ops", "kb_index"]:
            schema_sql = pg_dir / f"{schema}_schema.sql"
            data_sql = pg_dir / f"{schema}_data.sql"
            schema_sql.write_bytes(b"CREATE SCHEMA\n")
            data_sql.write_bytes(b"INSERT INTO data\n")
            files.append(FileHash(path=str(schema_sql.relative_to(package)), sha256=_sha256(schema_sql.read_bytes())))
            files.append(FileHash(path=str(data_sql.relative_to(package)), sha256=_sha256(data_sql.read_bytes())))

    if with_object_store:
        os_dir = package / "object_store_export"
        os_dir.mkdir()
        obj_content = b"asset content"
        obj_file = os_dir / "asset.txt_v1.bin"
        obj_file.write_bytes(obj_content)
        assets = AssetsManifest(
            space_id=space_id,
            objects=[
                ObjectStoreEntryModel(
                    object_id="asset.txt",
                    version="v1",
                    sha256=_sha256(obj_content),
                    size=len(obj_content),
                    media_type="text/plain",
                )
            ],
        )
        _write_json(package / "assets_manifest.json", assets.model_dump(mode="json"))
        files.append(FileHash(path="object_store_export/asset.txt_v1.bin", sha256=_sha256(obj_content)))

    manifest = BackupManifest(
        space_id=space_id,
        backup_id=backup_id,
        head_sha="a" * 40,
        hour_bucket="2026010100",
        files=sorted(files, key=lambda f: f.path),
    )
    _write_json(package / "manifest.json", manifest.model_dump(mode="json"))
    return package


class CountingPostgresService(PostgresBackupService):
    """PostgresBackupService stub that reports a matching decision count."""

    def count_decisions(self, space_id: str) -> int:
        return 1


def _postgres_service() -> PostgresBackupService:
    def fake_run(*args: Any, **kwargs: Any) -> Any:
        class Result:
            returncode = 0
            stderr = b""
            stdout = b""

        stdout = kwargs.get("stdout")
        if stdout is not None and hasattr(stdout, "write"):
            stdout.write(b"-- synthetic psql\n")
        return Result()

    return CountingPostgresService(
        host="localhost",
        port=5432,
        user="u",
        password="p",
        db="db",
        schemas=["kb_authz", "kb_ops", "kb_index"],
        run_command=fake_run,
    )


class ObjectStoreSpy(ObjectStoreAdapter):
    """Spy object-store adapter that records restored objects."""

    def __init__(self) -> None:
        self.objects: list[ObjectStoreEntry] = []

    def create_bucket(self, bucket: str) -> None:
        return

    def put_object(
        self,
        space_id: str,
        object_id: str,
        data: bytes,
        version: str | None = None,
        media_type: str | None = None,
        source_ref: str | None = None,
    ) -> ObjectStoreEntry:
        entry = ObjectStoreEntry(
            object_id=object_id,
            version=version or "v1",
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
            media_type=media_type,
            source_ref=source_ref,
        )
        self.objects.append(entry)
        return entry

    def upload(
        self,
        space_id: str,
        object_id: str,
        data: bytes,
        media_type: str | None = None,
        source_ref: str | None = None,
    ) -> ObjectStoreEntry:
        return self.put_object(space_id, object_id, data, None, media_type, source_ref)

    def list_objects(self, space_id: str) -> list[ObjectStoreEntry]:
        return self.objects

    def get_object(self, *args: Any, **kwargs: Any) -> bytes:
        return b""

    def list_object_versions(self, *args: Any, **kwargs: Any) -> list[ObjectStoreEntry]:
        return []


def test_restore_success(tmp_path: Path) -> None:
    _create_package(tmp_path, "src-space", "b1")
    spy = ObjectStoreSpy()
    adapter = StubBackupGitLabAdapter(
        state={("tags", "target-space"): [{"name": "v1"}]}
    )
    service = RestoreService(
        adapter=adapter,
        storage_path=str(tmp_path),
        object_store_adapter=spy,
        postgres_backup_service=_postgres_service(),
    )

    result = service.restore(
        "src-space",
        "b1",
        RestoreRequest(target_space_id="target-space"),
    )

    assert result.status == RestoreStatus.COMPLETE
    assert result.target_space_id == "target-space"
    assert result.integrity_report is not None
    assert result.integrity_report.verified is True
    assert result.closure_report is not None
    assert result.closure_report.consistent is True
    assert len(spy.objects) == 1


def test_restore_rejects_existing_target(tmp_path: Path) -> None:
    _create_package(tmp_path, "src-space", "b1")
    spy = ObjectStoreSpy()
    adapter = StubBackupGitLabAdapter(
        state={("branch", "target-space", "main"): {"name": "main", "commit": {"id": "b" * 40}}}
    )
    service = RestoreService(
        adapter=adapter,
        storage_path=str(tmp_path),
        object_store_adapter=spy,
        postgres_backup_service=_postgres_service(),
    )

    with pytest.raises(RestoreServiceError) as exc_info:
        service.restore(
            "src-space",
            "b1",
            RestoreRequest(target_space_id="target-space"),
        )
    assert exc_info.value.code == "TARGET_EXISTS"


def test_restore_force_overwrites_target(tmp_path: Path) -> None:
    _create_package(tmp_path, "src-space", "b1")
    spy = ObjectStoreSpy()
    adapter = StubBackupGitLabAdapter(
        state={
            ("branch", "target-space", "main"): {"name": "main", "commit": {"id": "b" * 40}},
            ("tags", "target-space"): [{"name": "v1"}],
        }
    )
    service = RestoreService(
        adapter=adapter,
        storage_path=str(tmp_path),
        object_store_adapter=spy,
        postgres_backup_service=_postgres_service(),
    )

    result = service.restore(
        "src-space",
        "b1",
        RestoreRequest(target_space_id="target-space", force=True),
    )

    assert result.status == RestoreStatus.COMPLETE


def test_restore_corrupt_package_aborts(tmp_path: Path) -> None:
    package = _create_package(tmp_path, "src-space", "b1")
    (package / "object_store_export" / "asset.txt_v1.bin").write_bytes(b"tampered")
    spy = ObjectStoreSpy()
    adapter = StubBackupGitLabAdapter()
    service = RestoreService(
        adapter=adapter,
        storage_path=str(tmp_path),
        object_store_adapter=spy,
        postgres_backup_service=_postgres_service(),
    )

    result = service.restore("src-space", "b1")

    assert result.status == RestoreStatus.FAILED
    assert result.integrity_report is not None
    assert result.integrity_report.verified is False
    assert len(spy.objects) == 0


def test_restore_missing_package_raises(tmp_path: Path) -> None:
    service = RestoreService(
        adapter=StubBackupGitLabAdapter(),
        storage_path=str(tmp_path),
    )
    with pytest.raises(RestoreServiceError) as exc_info:
        service.restore("src-space", "missing")
    assert exc_info.value.code == "PACKAGE_NOT_FOUND"


def test_closure_mismatch_reported(tmp_path: Path) -> None:
    _create_package(tmp_path, "src-space", "b1")

    class MissingObjectStore(ObjectStoreSpy):
        def list_objects(self, space_id: str) -> list[ObjectStoreEntry]:
            return []

    spy = MissingObjectStore()
    adapter = StubBackupGitLabAdapter(
        state={
            ("branch", "target-space", "main"): {"name": "main", "commit": {"id": "a" * 40}},
            ("tags", "target-space"): [{"name": "v1"}],
        }
    )
    service = RestoreService(
        adapter=adapter,
        storage_path=str(tmp_path),
        object_store_adapter=spy,
        postgres_backup_service=_postgres_service(),
    )

    result = service.restore(
        "src-space",
        "b1",
        RestoreRequest(target_space_id="target-space", force=True),
    )

    assert result.status == RestoreStatus.FAILED
    assert result.closure_report is not None
    assert result.closure_report.consistent is False
    assert any(m.scope == "object_store" for m in result.closure_report.mismatches)


def test_restore_without_object_store_export(tmp_path: Path) -> None:
    _create_package(tmp_path, "src-space", "b1", with_object_store=False)
    spy = ObjectStoreSpy()
    adapter = StubBackupGitLabAdapter(
        state={("tags", "target-space"): [{"name": "v1"}]}
    )
    service = RestoreService(
        adapter=adapter,
        storage_path=str(tmp_path),
        object_store_adapter=spy,
        postgres_backup_service=_postgres_service(),
    )

    result = service.restore(
        "src-space",
        "b1",
        RestoreRequest(target_space_id="target-space"),
    )

    assert result.status == RestoreStatus.COMPLETE
    assert len(spy.objects) == 0


def test_verify_integrity_endpoint(client: Any, tmp_path: Path) -> None:
    _create_package(tmp_path, "demo-space", "b1")
    client.app.state.restore_service.storage_path = tmp_path

    response = client.post(
        "/api/kb/v1/backups/demo-space/verify-integrity",
        data={"backup_id": "b1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["space_id"] == "demo-space"
    assert data["backup_id"] == "b1"


def test_restore_endpoint(client: Any, tmp_path: Path) -> None:
    _create_package(tmp_path, "demo-space", "b1")
    client.app.state.restore_service.storage_path = tmp_path
    client.app.state.restore_service.adapter.state[("tags", "target-space")] = [{"name": "v1"}]

    response = client.post(
        "/api/kb/v1/backups/demo-space/restore",
        json={"backup_id": "b1", "target_space_id": "target-space"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["target_space_id"] == "target-space"


def test_restore_endpoint_target_exists_returns_409(client: Any, tmp_path: Path) -> None:
    _create_package(tmp_path, "demo-space", "b1")
    client.app.state.restore_service.storage_path = tmp_path
    client.app.state.restore_service.adapter.state[("branch", "target-space", "main")] = {
        "name": "main",
        "commit": {"id": "b" * 40},
    }

    response = client.post(
        "/api/kb/v1/backups/demo-space/restore",
        json={"backup_id": "b1", "target_space_id": "target-space"},
    )
    assert response.status_code == 409


def test_restore_endpoint_corrupt_package_returns_failed_status(client: Any, tmp_path: Path) -> None:
    package = _create_package(tmp_path, "demo-space", "b1")
    (package / "object_store_export" / "asset.txt_v1.bin").write_bytes(b"tampered")
    client.app.state.restore_service.storage_path = tmp_path

    response = client.post(
        "/api/kb/v1/backups/demo-space/restore",
        json={"backup_id": "b1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["integrity_report"]["verified"] is False
