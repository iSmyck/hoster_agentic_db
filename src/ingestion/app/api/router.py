"""FastAPI routes for the Ingestion adapter."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ingestion.app.adapters.go_client import GOClient
from ingestion.app.adapters.source_connector import SourceConnector, build_source_connector
from ingestion.app.repositories.db import get_db
from ingestion.app.schemas.ingestion import (
    AuthorizeRequest,
    ConflictCheckRequest,
    ConflictCheckResponse,
    CursorResponse,
    CursorUpdateRequest,
    DryRunRequest,
    DryRunResponse,
    HealthResponse,
    ImportPackageResponse,
    SourceCreateRequest,
    SourceResponse,
    SourceUpdateRequest,
)
from ingestion.app.services import dry_run, importer, source_registry
from ingestion.app.services.dry_run import DryRunError
from ingestion.app.services.importer import ImporterError
from ingestion.app.services.source_registry import SourceRegistryError

router = APIRouter()


def get_go_client(request: Request) -> GOClient:
    """Return the GO client stored on the application instance."""
    return request.app.state.go_client


def get_connector_factory(request: Request) -> Any:
    """Return the connector factory stored on the application instance."""
    return request.app.state.connector_factory


def _build_connector(source_type: str, config: dict[str, Any]) -> SourceConnector:
    return build_source_connector(source_type, config)


def _handle_registry_error(exc: SourceRegistryError) -> HTTPException:
    code_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "ALREADY_EXISTS": status.HTTP_409_CONFLICT,
        "INVALID_SOURCE_TYPE": status.HTTP_422_UNPROCESSABLE_CONTENT,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


def _handle_dry_run_error(exc: DryRunError) -> HTTPException:
    code_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "IDEMPOTENCY_KEY_REUSED": status.HTTP_409_CONFLICT,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


def _handle_importer_error(exc: ImporterError) -> HTTPException:
    code_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "NOT_AUTHORIZED": status.HTTP_403_FORBIDDEN,
        "INVALID_STATE": status.HTTP_409_CONFLICT,
        "AUTHORIZATION_CONFLICT": status.HTTP_409_CONFLICT,
        "EMPTY_MANIFEST": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "PROPOSAL_SUBMISSION_FAILED": status.HTTP_502_BAD_GATEWAY,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/api/kb/v1/sources",
    status_code=status.HTTP_201_CREATED,
    response_model=SourceResponse,
)
def create_source(
    request: SourceCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        source = source_registry.create_source(
            db,
            request.space_id,
            request.source_id,
            request.source_type,
            request.config,
            request.ownership_mode,
            request.enabled,
        )
    except SourceRegistryError as exc:
        raise _handle_registry_error(exc) from exc
    return source


@router.get("/api/kb/v1/sources/{source_id}", response_model=SourceResponse)
def get_source(
    source_id: str,
    space_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        source = source_registry.get_source(db, space_id, source_id)
    except SourceRegistryError as exc:
        raise _handle_registry_error(exc) from exc
    return source


@router.patch("/api/kb/v1/sources/{source_id}", response_model=SourceResponse)
def update_source(
    source_id: str,
    request: SourceUpdateRequest,
    space_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        source = source_registry.update_source(
            db,
            space_id,
            source_id,
            request.config,
            request.ownership_mode,
            request.enabled,
        )
    except SourceRegistryError as exc:
        raise _handle_registry_error(exc) from exc
    return source


@router.post(
    "/api/kb/v1/sources/{source_id}/cursor",
    response_model=CursorResponse,
)
def update_cursor(
    source_id: str,
    request: CursorUpdateRequest,
    space_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        source = source_registry.get_source(db, space_id, source_id)
        cursor = source_registry.update_cursor(
            db,
            source,
            request.cursor_value,
            request.cursor_hash,
        )
    except SourceRegistryError as exc:
        raise _handle_registry_error(exc) from exc
    return cursor


@router.post(
    "/api/kb/v1/sources/{source_id}/dry-run",
    status_code=status.HTTP_201_CREATED,
    response_model=DryRunResponse,
)
def run_dry_run(
    source_id: str,
    request: DryRunRequest,
    space_id: str,
    db: Annotated[Session, Depends(get_db)],
    connector_factory: Annotated[Any, Depends(get_connector_factory)],
) -> Any:
    try:
        source = source_registry.get_source(db, space_id, source_id)
        cursor_record = source_registry.get_or_create_cursor(db, source)
        connector = connector_factory(source.source_type, source.config)
        idempotency_key = request.idempotency_key or dry_run.build_idempotency_key(
            space_id,
            source_id,
            cursor_value=cursor_record.cursor_value,
            cursor_hash=cursor_record.cursor_hash,
        )
        manifest = dry_run.run_dry_run(
            db,
            connector,
            space_id,
            source_id,
            idempotency_key,
        )
    except SourceRegistryError as exc:
        raise _handle_registry_error(exc) from exc
    except DryRunError as exc:
        raise _handle_dry_run_error(exc) from exc
    return manifest


@router.get("/api/kb/v1/dry-runs/{dry_run_id}", response_model=DryRunResponse)
def get_dry_run(
    dry_run_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    manifest = db.get(dry_run.DryRunManifest, dry_run_id)
    if manifest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "dry-run manifest not found"},
        )
    return manifest


@router.post(
    "/api/kb/v1/dry-runs/{dry_run_id}/authorize",
    status_code=status.HTTP_201_CREATED,
    response_model=ImportPackageResponse,
)
def authorize_import(
    dry_run_id: uuid.UUID,
    request: AuthorizeRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    try:
        package = importer.create_import_package(db, dry_run_id, request.authorized_by)
    except ImporterError as exc:
        raise _handle_importer_error(exc) from exc
    return package


@router.post(
    "/api/kb/v1/import-packages/{import_package_id}/submit",
    response_model=ImportPackageResponse,
)
def submit_import(
    import_package_id: uuid.UUID,
    space_id: str,
    db: Annotated[Session, Depends(get_db)],
    go_client: Annotated[GOClient, Depends(get_go_client)],
) -> Any:
    try:
        package = importer.submit_source_proposal(
            db,
            go_client,
            space_id,
            import_package_id,
        )
    except ImporterError as exc:
        raise _handle_importer_error(exc) from exc
    return package


@router.post(
    "/api/kb/v1/sources/{source_id}/conflict-check",
    response_model=ConflictCheckResponse,
)
def conflict_check(
    source_id: str,
    request: ConflictCheckRequest,
    space_id: str,
    db: Annotated[Session, Depends(get_db)],
    go_client: Annotated[GOClient, Depends(get_go_client)],
) -> Any:
    try:
        result = dry_run.detect_three_way_conflict(
            db,
            go_client,
            space_id,
            source_id,
            request.model_dump(),
        )
    except SourceRegistryError as exc:
        raise _handle_registry_error(exc) from exc
    return result
