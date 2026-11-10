"""Live smoke test for the Backup adapter.

Usage:
    RUN_LIVE_BACKUP_TESTS=1 PYTHONPATH=src uv run python src/backup/scripts/smoke_backup.py

Skips gracefully if the sandbox is unavailable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow the script to run from the repository root without package install.
_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backup.app.adapters.gitlab import HttpBackupGitLabAdapter
from backup.app.adapters.object_store import MinioObjectStoreAdapter, ObjectStoreAdapterError
from backup.app.core.config import settings
from backup.app.services.backup import BackupService
from backup.app.services.object_store import ObjectStoreService
from backup.app.services.postgres_backup import PostgresBackupService


def _default_object_store_adapter() -> MinioObjectStoreAdapter | None:
    if not settings.BACKUP_MINIO_ACCESS_KEY or not settings.BACKUP_MINIO_SECRET_KEY:
        return None
    return MinioObjectStoreAdapter(
        endpoint=settings.BACKUP_MINIO_ENDPOINT,
        access_key=settings.BACKUP_MINIO_ACCESS_KEY,
        secret_key=settings.BACKUP_MINIO_SECRET_KEY,
        bucket=settings.BACKUP_MINIO_BUCKET,
        use_ssl=settings.BACKUP_MINIO_USE_SSL,
    )


def _default_postgres_backup_service() -> PostgresBackupService:
    schemas = [s.strip() for s in settings.BACKUP_POSTGRES_SCHEMAS.split(",") if s.strip()]
    return PostgresBackupService(
        host=settings.BACKUP_POSTGRES_HOST,
        port=settings.BACKUP_POSTGRES_PORT,
        user=settings.BACKUP_POSTGRES_USER,
        password=settings.BACKUP_POSTGRES_PASSWORD,
        db=settings.BACKUP_POSTGRES_DB,
        schemas=schemas,
    )


def main() -> int:
    if os.environ.get("RUN_LIVE_BACKUP_TESTS") != "1":
        print("SKIP: RUN_LIVE_BACKUP_TESTS is not set to 1")
        return 0

    space_id = os.environ.get("BACKUP_LIVE_SPACE_ID", "corp-kb/sales")
    adapter = HttpBackupGitLabAdapter(
        settings.BACKUP_GITLAB_URL,
        settings.BACKUP_GITLAB_TOKEN,
        settings.BACKUP_GITLAB_PROJECT_PATH_PREFIX,
    )
    object_store_adapter = _default_object_store_adapter()
    object_store_service = (
        ObjectStoreService(object_store_adapter) if object_store_adapter else None
    )
    postgres_backup_service = _default_postgres_backup_service()
    service = BackupService(
        adapter=adapter,
        object_store_adapter=object_store_adapter,
        postgres_backup_service=postgres_backup_service,
    )

    try:
        package = service.create_full_backup(space_id)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: backup failed: {exc}")
        return 1

    if package.status != "complete":
        print(f"FAIL: backup status is {package.status}")
        return 1

    manifest = package.manifest
    if manifest is None:
        print("FAIL: manifest missing")
        return 1

    package_path = Path(package.package_path)
    mirror_dir = package_path / "mirror.git"
    if not (mirror_dir / "HEAD").exists():
        print("FAIL: mirror.git/HEAD missing")
        return 1

    for file_hash in manifest.files:
        file_path = package_path / file_hash.path
        if not file_path.exists():
            print(f"FAIL: missing {file_hash.path}")
            return 1

    if object_store_service is not None:
        try:
            manifest_path = package_path / "assets_manifest.json"
            if not manifest_path.exists():
                print("FAIL: assets_manifest.json missing")
                return 1
            export_dir = package_path / "object_store_export"
            if not export_dir.exists():
                print("FAIL: object_store_export/ missing")
                return 1
            print(f"PASS: object-store backup verified for {space_id}")
        except ObjectStoreAdapterError as exc:
            print(f"BLOCKED: object-store verification failed: {exc}")
            return 0

    postgres_dir = package_path / "postgres_export"
    if not postgres_dir.exists():
        print("FAIL: postgres_export/ missing")
        return 1

    print(f"PASS: full backup {package.backup_id} for {space_id} verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
