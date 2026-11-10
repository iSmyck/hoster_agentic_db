"""FastAPI routes for the Backup adapter."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from backup.app.adapters.gitlab import BackupGitLabAdapterError
from backup.app.adapters.object_store import ObjectStoreAdapterError
from backup.app.core.config import settings
from backup.app.schemas.backup import (
    BackupCreateResponse,
    BackupLatestResponse,
    ErrorResponse,
    HealthResponse,
    ObjectUploadResponse,
)
from backup.app.services.backup import BackupService, BackupServiceError
from backup.app.services.object_store import ObjectStoreService, ObjectStoreServiceError

router = APIRouter()

_SPACE_ID_RE = __import__("re").compile(r"^[a-zA-Z0-9_-]+$")


def get_backup_service(request: Request) -> BackupService:
    """Return the BackupService stored on the application instance."""
    return request.app.state.backup_service


def get_object_store_service(request: Request) -> ObjectStoreService:
    """Return the ObjectStoreService stored on the application instance."""
    return request.app.state.object_store_service


def _handle_backup_error(exc: BackupServiceError) -> HTTPException:
    code_map = {
        "INVALID_SPACE_ID": status.HTTP_400_BAD_REQUEST,
        "GITLAB_ERROR": status.HTTP_502_BAD_GATEWAY,
        "KB_OPS_ERROR": status.HTTP_502_BAD_GATEWAY,
        "OBJECT_STORE_ERROR": status.HTTP_502_BAD_GATEWAY,
        "POSTGRES_NOT_CONFIGURED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "OBJECT_STORE_NOT_CONFIGURED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "PG_DUMP_FAILED": status.HTTP_502_BAD_GATEWAY,
        "PG_DUMP_NOT_FOUND": status.HTTP_502_BAD_GATEWAY,
        "POSTGRES_BACKUP_ERROR": status.HTTP_502_BAD_GATEWAY,
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


def _handle_object_store_error(exc: ObjectStoreServiceError) -> HTTPException:
    code_map = {
        "OBJECT_STORE_ERROR": status.HTTP_502_BAD_GATEWAY,
    }
    status_code = code_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    cause = exc.__cause__
    if (
        isinstance(cause, ObjectStoreAdapterError)
        and cause.s3_code is not None
        and cause.s3_code in ("NoSuchBucket", "NoSuchKey", "BucketNotEmpty")
    ):
        status_code = status.HTTP_502_BAD_GATEWAY
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


@router.post(
    "/api/kb/v1/objects/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=ObjectUploadResponse,
    responses={
        400: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def upload_object(
    space_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    service: Annotated[ObjectStoreService, Depends(get_object_store_service)],
) -> dict[str, Any]:
    if not space_id or not _SPACE_ID_RE.fullmatch(space_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_SPACE_ID", "message": "invalid space_id"},
        )
    max_size = settings.BACKUP_MAX_UPLOAD_SIZE_BYTES
    try:
        content = file.file.read(max_size + 1)
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail={"code": "UPLOAD_TOO_LARGE", "message": f"upload exceeds {max_size} bytes"},
            )
        entry = service.stage_file(
            space_id=space_id,
            filename=file.filename or "upload.bin",
            content=content,
            media_type=file.content_type,
        )
    except ObjectStoreServiceError as exc:
        raise _handle_object_store_error(exc) from exc
    finally:
        file.file.close()

    return {
        "object_id": entry.object_id,
        "version": entry.version,
        "sha256": entry.sha256,
        "size": entry.size,
    }


@router.post(
    "/api/kb/v1/backups/{space_id}/full",
    status_code=status.HTTP_201_CREATED,
    response_model=BackupCreateResponse,
    responses={
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_full_backup(
    space_id: str,
    service: Annotated[BackupService, Depends(get_backup_service)],
) -> dict[str, Any]:
    if not space_id or not _SPACE_ID_RE.fullmatch(space_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_SPACE_ID", "message": "invalid space_id"},
        )
    try:
        package = service.create_full_backup(space_id)
    except BackupServiceError as exc:
        raise _handle_backup_error(exc) from exc
    return {
        "space_id": package.space_id,
        "backup_id": package.backup_id,
        "status": package.status.value,
        "package_path": package.package_path,
    }
