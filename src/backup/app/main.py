"""FastAPI application factory for the Backup adapter."""

from __future__ import annotations

from fastapi import FastAPI

from backup.app.adapters.gitlab import BackupGitLabAdapter, HttpBackupGitLabAdapter
from backup.app.api.router import router as backup_router
from backup.app.core.config import settings
from backup.app.services.backup import BackupService


def create_app(
    adapter: BackupGitLabAdapter | None = None,
    service: BackupService | None = None,
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
    else:
        adapter = adapter or _default_adapter()
        app.state.backup_service = BackupService(adapter=adapter)
    return app


def _default_adapter() -> HttpBackupGitLabAdapter:
    return HttpBackupGitLabAdapter(
        settings.BACKUP_GITLAB_URL,
        settings.BACKUP_GITLAB_TOKEN,
        settings.BACKUP_GITLAB_PROJECT_PATH_PREFIX,
    )


app = create_app()
