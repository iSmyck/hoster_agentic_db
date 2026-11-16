"""HTTP routes for kb-ingestion convert staging."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from ..core.config import settings
from ..jobs.queue import InMemoryJobQueue
from ..jobs.scheduler import Scheduler
from ..schemas.convert import ConvertRunRequest, DryRunReport
from ..schemas.enforce import (
    DataBarrierReport,
    DataBarrierRequest,
    FrontMatterValidateReport,
    FrontMatterValidateRequest,
)
from ..schemas.jobs import (
    IngestionJob,
    JobEnqueueRequest,
    JobMetrics,
    JobTickReport,
    JobTickRequest,
)
from ..schemas.mermaid import MermaidActivateRequest, MermaidRouteReport
from ..schemas.source_sync import (
    NotificationSubscription,
    NotificationSubscriptionRequest,
    SchedulerTickReport,
    SchedulerTickRequest,
    SourceRecord,
    SourceRegisterRequest,
    SyncReport,
    SyncRequest,
)
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
from ..services.mermaid_route import MermaidRoute
from ..services.notifier import Notifier
from ..services.source_sync import SourceRegistry, SourceSyncError, SourceSyncService
from ..services.staging import StagingError, StagingService
from ..services.structure_proposals import StructureReviewService
from ..validators.data_barrier import DataBarrierError, enforce_data_barrier
from ..validators.front_matter import FrontMatterError, enforce_front_matter

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


def get_source_registry(request: Request) -> SourceRegistry:
    registry = getattr(request.app.state, "source_registry", None)
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "source_registry is not configured"},
        )
    return registry


def get_source_sync(request: Request) -> SourceSyncService:
    service = getattr(request.app.state, "source_sync", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "source_sync is not configured"},
        )
    return service


def get_notifier(request: Request) -> Notifier:
    notifier = getattr(request.app.state, "notifier", None)
    if notifier is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "notifier is not configured"},
        )
    return notifier


def get_mermaid_route(request: Request) -> MermaidRoute:
    route = getattr(request.app.state, "mermaid_route", None)
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "mermaid_route is not configured"},
        )
    return route


def get_job_queue(request: Request) -> InMemoryJobQueue:
    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "job_queue is not configured"},
        )
    return queue


def get_scheduler(request: Request) -> Scheduler:
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "scheduler is not configured"},
        )
    return scheduler


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


def _sync_http(exc: SourceSyncError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": exc.message},
    )


@router.post(
    "/api/kb/v1/ingest/sources",
    response_model=SourceRecord,
    status_code=status.HTTP_201_CREATED,
)
def register_source(
    body: SourceRegisterRequest,
    registry: Annotated[SourceRegistry, Depends(get_source_registry)],
) -> SourceRecord:
    try:
        return registry.register(body)
    except SourceSyncError as exc:
        raise _sync_http(exc) from exc


@router.get("/api/kb/v1/ingest/sources/{source_id}", response_model=SourceRecord)
def get_source(
    source_id: str,
    registry: Annotated[SourceRegistry, Depends(get_source_registry)],
) -> SourceRecord:
    try:
        return registry.get(source_id)
    except SourceSyncError as exc:
        raise _sync_http(exc) from exc


@router.post(
    "/api/kb/v1/ingest/sources/{source_id}/sync",
    response_model=SyncReport,
)
def sync_source(
    source_id: str,
    body: SyncRequest,
    service: Annotated[SourceSyncService, Depends(get_source_sync)],
) -> SyncReport:
    try:
        return service.run_sync(source_id, body)
    except SourceSyncError as exc:
        raise _sync_http(exc) from exc


@router.post(
    "/api/kb/v1/ingest/notifications/subscriptions",
    response_model=NotificationSubscription,
    status_code=status.HTTP_201_CREATED,
)
def subscribe_notifications(
    body: NotificationSubscriptionRequest,
    notifier: Annotated[Notifier, Depends(get_notifier)],
) -> NotificationSubscription:
    return notifier.subscribe(body)


@router.post(
    "/api/kb/v1/ingest/scheduler/tick",
    response_model=SchedulerTickReport,
)
def scheduler_tick(
    body: SchedulerTickRequest,
    scheduler: Annotated[Scheduler, Depends(get_scheduler)],
) -> SchedulerTickReport:
    if not body.now:
        return scheduler.tick(datetime.now(UTC))
    try:
        now = datetime.fromisoformat(body.now)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": "invalid now timestamp"},
        ) from exc
    return scheduler.tick(now)


def _parse_now(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": "invalid now timestamp"},
        ) from exc


@router.post(
    "/api/kb/v1/ingest/validate/front-matter",
    response_model=FrontMatterValidateReport,
)
def validate_front_matter_endpoint(body: FrontMatterValidateRequest) -> FrontMatterValidateReport:
    try:
        enforce_front_matter(body.front_matter)
    except FrontMatterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return FrontMatterValidateReport(valid=True)


@router.post(
    "/api/kb/v1/ingest/validate/data-barrier",
    response_model=DataBarrierReport,
)
def validate_data_barrier_endpoint(body: DataBarrierRequest) -> DataBarrierReport:
    try:
        hits = enforce_data_barrier(
            data_profile=body.data_profile,
            text=body.text,
            legal_basis=body.legal_basis,
            inference_provider=body.inference_provider,
            document_path=body.document_path,
            document_id=body.document_id,
        )
    except DataBarrierError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={
                "code": exc.code,
                "message": exc.message,
                "hits": exc.hits,
                "correction_task": (
                    exc.correction_task.model_dump() if exc.correction_task is not None else None
                ),
            },
        ) from exc
    return DataBarrierReport(valid=True, hits=hits)


@router.post(
    "/api/kb/v1/ingest/jobs",
    response_model=IngestionJob,
    status_code=status.HTTP_201_CREATED,
)
def enqueue_job(
    body: JobEnqueueRequest,
    queue: Annotated[InMemoryJobQueue, Depends(get_job_queue)],
) -> IngestionJob:
    return queue.enqueue(
        body.kind,
        body.payload,
        max_attempts=body.max_attempts,
        now=_parse_now(body.now),
    )


@router.post(
    "/api/kb/v1/ingest/jobs/tick",
    response_model=JobTickReport,
)
def tick_jobs(
    body: JobTickRequest,
    queue: Annotated[InMemoryJobQueue, Depends(get_job_queue)],
) -> JobTickReport:
    job = queue.process_one(now=_parse_now(body.now), inject=body.inject)
    return JobTickReport(processed=0 if job is None else 1, job=job)


@router.get("/api/kb/v1/ingest/jobs/metrics", response_model=JobMetrics)
def job_metrics(
    queue: Annotated[InMemoryJobQueue, Depends(get_job_queue)],
    now: str | None = None,
) -> JobMetrics:
    return queue.metrics(_parse_now(now))


@router.get("/api/kb/v1/ingest/mermaid/status", response_model=MermaidRouteReport)
def mermaid_status(
    route: Annotated[MermaidRoute, Depends(get_mermaid_route)],
) -> MermaidRouteReport:
    return route.status()


@router.post("/api/kb/v1/ingest/mermaid/activate", response_model=MermaidRouteReport)
def mermaid_activate(
    body: MermaidActivateRequest,
    route: Annotated[MermaidRoute, Depends(get_mermaid_route)],
) -> MermaidRouteReport:
    return route.activate(human_spot_check=body.human_spot_check, license_ok=body.license_ok)