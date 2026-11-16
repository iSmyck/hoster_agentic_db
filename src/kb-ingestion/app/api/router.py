"""HTTP routes for kb-ingestion convert staging."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from ..core.config import settings
from ..schemas.convert import ConvertRunRequest, DryRunReport
from ..services.converter import ConversionError, ConversionService
from ..services.staging import StagingError, StagingService

router = APIRouter()


def get_staging_service(request: Request) -> StagingService:
    return request.app.state.staging_service


def get_conversion_service(request: Request) -> ConversionService:
    return request.app.state.conversion_service


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/api/kb/v1/ingest/convert",
    status_code=status.HTTP_201_CREATED,
)
def convert_upload(
    data_profile: Annotated[str, Form()],
    service: Annotated[StagingService, Depends(get_staging_service)],
    space_id: Annotated[str, Form()] = "",
    client_id: Annotated[str, Form()] = "",
    legal_basis: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> dict[str, object]:
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "MISSING_FILE", "message": "file is required"},
        )
    max_size = settings.INGEST_MAX_UPLOAD_SIZE_BYTES
    try:
        service.validate_metadata(
            space_id=space_id,
            client_id=client_id,
            data_profile=data_profile,
            legal_basis=legal_basis,
        )
        content = file.file.read(max_size + 1)
        result = service.stage_convert_upload(
            space_id=space_id,
            client_id=client_id,
            data_profile=data_profile,
            legal_basis=legal_basis,
            content=content,
            media_type=file.content_type,
        )
    except StagingError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    finally:
        file.file.close()
    return {
        "object_id": result.object_id,
        "sha256": result.sha256,
        "version_id": result.version_id,
        "size": result.size,
        "media_type": result.media_type,
    }


@router.post(
    "/api/kb/v1/ingest/convert/run",
    response_model=DryRunReport,
    status_code=status.HTTP_200_OK,
)
def convert_run(
    body: ConvertRunRequest,
    service: Annotated[ConversionService, Depends(get_conversion_service)],
) -> DryRunReport:
    try:
        return service.run_dry_convert(body)
    except ConversionError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc