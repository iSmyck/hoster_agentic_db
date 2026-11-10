"""FastAPI routes for the Backup adapter."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backup.app.adapters.gitlab import BackupGitLabAdapterError
from backup.app.schemas.backup import (
    BackupCreateResponse,
    BackupLatestResponse,
    ErrorResponse,
    HealthResponse,
)
from backup.app.services.backup import BackupService, BackupServiceError

router = APIRouter()


def get_backup_service(request: Request) -> BackupService:
    """Return the BackupService stored on the application instance."""
    return request.app.state.backup_service


def _handle_backup_error(exc: BackupServiceError) -> HTTPException:
    code_map = {
        "GITLAB_ERROR": status.HTTP_502_BAD_GATEWAY,
        "KB_OPS_ERROR": status.HTTP_502_BAD_GATEWAY,
        "BACKUP_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "HASH_MISMATCH": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    status_code = code_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    if exc.code == "GITLAB_ERROR":
        # Surface 403/404 from the underlying GitLab API call.
        cause = exc.__cause__
        if isinstance(cause, BackupGitLabAdapterError) and cause.status_code is not None:
            if cause.status_code == 403:
                status_code = status.HTTP_403_FORBIDDEN
            elif cause.status_code == 404:
                status_code = status.HTTP_404_NOT_FOUND
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/api/kb/v1/backups/{space_id}/mirror",
    status_code=status.HTTP_201_CREATED,
    response_model=BackupCreateResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_mirror_backup(
    space_id: str,
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> dict[str, Any]:
    try:
        package = service.create_mirror_backup(space_id)
    except BackupServiceError as exc:
        raise _handle_backup_error(exc) from exc
    return {
        "space_id": package.space_id,
        "backup_id": package.backup_id,
        "status": package.status.value,
        "package_path": package.package_path,
    }


@router.get(
    "/api/kb/v1/backups/{space_id}/latest",
    response_model=BackupLatestResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_latest_backup(
    space_id: str,
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> dict[str, Any]:
    package = service.get_latest(space_id)
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "no backup found for space"},
        )
    return {
        "space_id": package.space_id,
        "backup_id": package.backup_id,
        "status": package.status.value,
        "package_path": package.package_path,
        "manifest": package.manifest.model_dump(mode="json") if package.manifest else None,
    }
