"""FastAPI application factory for the Backup adapter."""

from __future__ import annotations

from fastapi import FastAPI

from backup.app.adapters.gitlab import BackupGitLabAdapter, HttpBackupGitLabAdapter
from backup.app.adapters.object_store import MinioObjectStoreAdapter
from backup.app.api.router import router as backup_router
from backup.app.core.config import settings
from backup.app.services.backup import BackupService
from backup.app.services.object_store import ObjectStoreService
from backup.app.services.postgres_backup import PostgresBackupService
from backup.app.services.restore import RestoreService


def create_app(
    adapter: BackupGitLabAdapter | None = None,
    service: BackupService | None = None,
    restore_service: RestoreService | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="corp-ai-db Backup",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(backup_router)

    if service is not None:
        app.state.backup_service = service
        app.state.object_store_service = (
            service.object_store_service
            if getattr(service, "object_store_service", None) is not None
            else None
        )
        if app.state.object_store_service is None:
            default_adapter = _default_object_store_adapter()
            app.state.object_store_service = (
                ObjectStoreService(default_adapter) if default_adapter else None
            )
        app.state.restore_service = restore_service or _default_restore_service(
            app.state.backup_service
        )
    else:
        default_object_store_adapter = _default_object_store_adapter()
        adapter = adapter or _default_adapter()
        app.state.backup_service = BackupService(
            adapter=adapter,
            object_store_adapter=default_object_store_adapter,
            postgres_backup_service=_default_postgres_backup_service(),
        )
        app.state.object_store_service = (
            ObjectStoreService(default_object_store_adapter)
            if default_object_store_adapter is not None
            else None
        )
        app.state.restore_service = restore_service or _default_restore_service(
            app.state.backup_service
        )
    return app


def _default_restore_service(backup_service: BackupService) -> RestoreService:
    return RestoreService(
        adapter=_default_restore_adapter(),
        storage_path=str(backup_service.storage_path),
        gitlab_url=settings.BACKUP_RESTORE_GITLAB_URL,
        gitlab_token=settings.BACKUP_RESTORE_GITLAB_TOKEN,
        project_path_prefix=settings.BACKUP_RESTORE_GITLAB_PROJECT_PATH_PREFIX,
        object_store_adapter=_default_restore_object_store_adapter(),
        postgres_backup_service=backup_service.postgres_backup_service,
    )


def _default_restore_adapter() -> HttpBackupGitLabAdapter:
    return HttpBackupGitLabAdapter(
        settings.BACKUP_RESTORE_GITLAB_URL,
        settings.BACKUP_RESTORE_GITLAB_TOKEN,
        settings.BACKUP_RESTORE_GITLAB_PROJECT_PATH_PREFIX,
    )


def _default_restore_object_store_adapter() -> MinioObjectStoreAdapter | None:
    if not settings.BACKUP_RESTORE_MINIO_ACCESS_KEY or not settings.BACKUP_RESTORE_MINIO_SECRET_KEY:
        return None
    return MinioObjectStoreAdapter(
        endpoint=settings.BACKUP_RESTORE_MINIO_ENDPOINT,
        access_key=settings.BACKUP_RESTORE_MINIO_ACCESS_KEY,
        secret_key=settings.BACKUP_RESTORE_MINIO_SECRET_KEY,
        bucket=settings.BACKUP_RESTORE_MINIO_BUCKET,
        use_ssl=settings.BACKUP_RESTORE_MINIO_USE_SSL,
    )


def _default_adapter() -> HttpBackupGitLabAdapter:
    return HttpBackupGitLabAdapter(
        settings.BACKUP_GITLAB_URL,
        settings.BACKUP_GITLAB_TOKEN,
        settings.BACKUP_GITLAB_PROJECT_PATH_PREFIX,
    )


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


app = create_app()
