"""HTTP routes for kb-ingestion convert staging."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from ..core.config import settings
from ..schemas.convert import ConvertRunRequest, DryRunReport
from ..schemas.structure import (
    BatchReadReport,
    BatchReadRequest,
    StructureProposalEdit,
    StructureProposalReport,
    StructureProposalView,
    StructureSubmitReport,
    StructureSubmitRequest,
)
from ..services.agent_structurer import AgentStructurer, StructureError
from ..services.converter import ConversionError, ConversionService
from ..services.staging import StagingError, StagingService
from ..services.structure_proposals import StructureReviewService

router = APIRouter()


def get_staging_service(request: Request) -> StagingService:
    return request.app.state.staging_service


def get_conversion_service(request: Request) -> ConversionService:
    return request.app.state.conversion_service


def get_agent_structurer(request: Request) -> AgentStructurer:
    structurer = getattr(request.app.state, "agent_structurer", None)
    if structurer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "agent_structurer is not configured"},
        )
    return structurer


def get_structure_review(request: Request) -> StructureReviewService:
    service = getattr(request.app.state, "structure_review", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "structure_review is not configured"},
        )
    return service


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


@router.post(
    "/api/kb/v1/ingest/structure/batch-read",
    response_model=BatchReadReport,
    status_code=status.HTTP_200_OK,
)
def structure_batch_read(
    body: BatchReadRequest,
    service: Annotated[AgentStructurer, Depends(get_agent_structurer)],
) -> BatchReadReport:
    try:
        return service.batch_read(body)
    except StructureError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post(
    "/api/kb/v1/ingest/structure/propose",
    response_model=StructureProposalReport,
    status_code=status.HTTP_200_OK,
)
def structure_propose(
    body: BatchReadRequest,
    service: Annotated[AgentStructurer, Depends(get_agent_structurer)],
) -> StructureProposalReport:
    try:
        return service.propose_tree(body)
    except StructureError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post(
    "/api/kb/v1/ingest/structure/proposals",
    response_model=StructureProposalView,
    status_code=status.HTTP_201_CREATED,
)
def structure_proposal_create(
    body: BatchReadRequest,
    service: Annotated[StructureReviewService, Depends(get_structure_review)],
) -> StructureProposalView:
    try:
        return service.create(body)
    except StructureError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get(
    "/api/kb/v1/ingest/structure/proposals/{proposal_id}",
    response_model=StructureProposalView,
)
def structure_proposal_get(
    proposal_id: str,
    service: Annotated[StructureReviewService, Depends(get_structure_review)],
) -> StructureProposalView:
    try:
        return service.get(proposal_id)
    except StructureError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.patch(
    "/api/kb/v1/ingest/structure/proposals/{proposal_id}",
    response_model=StructureProposalView,
)
def structure_proposal_patch(
    proposal_id: str,
    body: StructureProposalEdit,
    service: Annotated[StructureReviewService, Depends(get_structure_review)],
) -> StructureProposalView:
    try:
        return service.patch(proposal_id, body)
    except StructureError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post(
    "/api/kb/v1/ingest/structure/proposals/{proposal_id}/approve",
    response_model=StructureProposalView,
)
def structure_proposal_approve(
    proposal_id: str,
    service: Annotated[StructureReviewService, Depends(get_structure_review)],
) -> StructureProposalView:
    try:
        return service.approve(proposal_id)
    except StructureError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post(
    "/api/kb/v1/ingest/structure/proposals/{proposal_id}/submit",
    response_model=StructureSubmitReport,
)
def structure_proposal_submit(
    proposal_id: str,
    body: StructureSubmitRequest,
    service: Annotated[StructureReviewService, Depends(get_structure_review)],
) -> StructureSubmitReport:
    try:
        return service.submit(proposal_id, body)
    except StructureError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc