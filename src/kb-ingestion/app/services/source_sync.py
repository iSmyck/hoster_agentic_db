"""Source registry, delta detection, and auto-merge policy (KBI.3)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..adapters.go_client import GOClient, GOClientError, StubGOClient
from ..schemas.source_sync import (
    ChangeRecord,
    SourceRecord,
    SourceRegisterRequest,
    SyncDocument,
    SyncJob,
    SyncOutcome,
    SyncReport,
    SyncRequest,
)
from ..validators.data_barrier import DataBarrierError, enforce_data_barrier
from ..validators.front_matter import FrontMatterError, enforce_front_matter
from .notifier import Notifier


class SourceSyncError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class _CursorEntry:
    sha256: str
    source_version: str
    path: str


class SourceRegistry:
    def __init__(self) -> None:
        self._items: dict[str, SourceRecord] = {}

    def register(self, request: SourceRegisterRequest) -> SourceRecord:
        if request.auto_merge and not request.trusted:
            raise SourceSyncError(
                "AUTO_MERGE_REQUIRES_TRUSTED",
                "auto_merge requires trusted=true",
            )
        if request.data_profile == "pii_permitted" and not (
            request.legal_basis and request.legal_basis.strip()
        ):
            raise SourceSyncError(
                "LEGAL_BASIS_REQUIRED",
                "legal_basis is required for pii_permitted",
            )
        record = SourceRecord(
            source_id=uuid.uuid4().hex,
            source_type=request.source_type,
            source_ref=request.source_ref,
            credentials_ref=request.credentials_ref,
            poll_interval=request.poll_interval,
            space_id=request.space_id,
            data_profile=request.data_profile,
            validation_required=request.validation_required,
            auto_merge=request.auto_merge,
            trusted=request.trusted,
            legal_basis=request.legal_basis,
            max_files_per_sync=request.max_files_per_sync,
            max_lines_changed=request.max_lines_changed,
        )
        self._items[record.source_id] = record
        return record

    def get(self, source_id: str) -> SourceRecord:
        record = self._items.get(source_id)
        if record is None:
            raise SourceSyncError("SOURCE_NOT_FOUND", "source not found", http_status=404)
        return record

    def list_all(self) -> list[SourceRecord]:
        return list(self._items.values())


class SourceSyncService:
    def __init__(
        self,
        registry: SourceRegistry,
        go_client: GOClient | None = None,
        notifier: Notifier | None = None,
    ) -> None:
        self._registry = registry
        self._go = go_client or StubGOClient()
        self._notifier = notifier or Notifier()
        self._cursors: dict[str, dict[str, _CursorEntry]] = {}
        self._jobs: dict[str, SyncJob] = {}
        self._last_queued: dict[str, datetime] = {}
        self._running: set[str] = set()

    def last_queued_at(self, source_id: str) -> datetime | None:
        return self._last_queued.get(source_id)

    def is_running(self, source_id: str) -> bool:
        return source_id in self._running

    def in_flight_job(self, source_id: str) -> SyncJob | None:
        for job in self._jobs.values():
            if job.source_id == source_id and job.status in {"queued", "running"}:
                return job
        return None

    def enqueue_job(self, source_id: str, when: datetime) -> SyncJob:
        job = SyncJob(
            job_id=uuid.uuid4().hex,
            source_id=source_id,
            status="queued",
            scheduled_at=when.isoformat(),
        )
        self._jobs[job.job_id] = job
        self._last_queued[source_id] = when
        return job

    def run_sync(self, source_id: str, request: SyncRequest) -> SyncReport:
        source = self._registry.get(source_id)
        if source_id in self._running:
            raise SourceSyncError("SYNC_IN_PROGRESS", "sync already running for source", http_status=409)
        job = self.in_flight_job(source_id)
        self._running.add(source_id)
        if job is not None and job.status == "queued":
            job.status = "running"
        failed = False
        try:
            return self._run(source, request)
        except Exception:
            failed = True
            raise
        finally:
            self._running.discard(source_id)
            if job is not None:
                job.status = "failed" if failed else "done"

    def _run(self, source: SourceRecord, request: SyncRequest) -> SyncReport:
        sync_run_id = uuid.uuid4().hex
        changes = [_detect(self._cursor_map(source.source_id), document) for document in request.documents]
        mutating = [item for item in changes if item.kind != "noop"]
        bound_code = _bounds_code(source, mutating, request.documents)
        outcomes: list[SyncOutcome] = []
        for document, change in zip(request.documents, changes, strict=True):
            if change.kind == "noop":
                outcomes.append(
                    SyncOutcome(
                        source_object_id=document.source_object_id,
                        path=document.path,
                        disposition="noop",
                    )
                )
                continue
            outcome = self._apply_change(
                source=source,
                document=document,
                change=change,
                bound_code=bound_code,
                sync_run_id=sync_run_id,
                base_sha=request.base_sha,
            )
            outcomes.append(outcome)
            if outcome.disposition != "refused":
                self._commit_cursor(source.source_id, document, change)
        return SyncReport(
            sync_run_id=sync_run_id,
            source_id=source.source_id,
            changes=changes,
            outcomes=outcomes,
        )

    def _apply_change(
        self,
        *,
        source: SourceRecord,
        document: SyncDocument,
        change: ChangeRecord,
        bound_code: str | None,
        sync_run_id: str,
        base_sha: str,
    ) -> SyncOutcome:
        code, disposition = _policy(source, document, change, bound_code)
        if disposition == "refused":
            return SyncOutcome(
                source_object_id=document.source_object_id,
                path=document.path,
                disposition="refused",
                code=code,
            )
        try:
            _enforce_content(source, document)
        except (FrontMatterError, DataBarrierError) as exc:
            return SyncOutcome(
                source_object_id=document.source_object_id,
                path=document.path,
                disposition="refused",
                code=exc.code,
            )
        try:
            proposal = self._go.submit_proposal(
                _proposal_payload(source, document, change, sync_run_id, base_sha)
            )
        except GOClientError as exc:
            raise SourceSyncError("GO_SUBMIT_FAILED", exc.message, http_status=502) from exc
        go_id = str(proposal.get("id") or "")
        if not go_id:
            raise SourceSyncError("GO_SUBMIT_FAILED", "GO proposal response missing id", http_status=502)
        actor_type = None
        if disposition == "merged":
            actor_type = "source_sync"
            try:
                self._go.auto_merge(
                    go_id,
                    decision_data={
                        "actor_type": "source_sync",
                        "decision": "accepted",
                        "rationale": "auto-merge per source policy",
                        "source_id": source.source_id,
                        "source_version": document.source_version,
                        "sync_run_id": sync_run_id,
                        "trailers": {
                            "Source-Sync-Id": source.source_id,
                            "Source-Version": document.source_version,
                            "Sync-Run-Id": sync_run_id,
                        },
                    },
                )
            except GOClientError as exc:
                raise SourceSyncError("GO_SUBMIT_FAILED", exc.message, http_status=502) from exc
            self._notifier.notify_merge(
                space_id=source.space_id,
                path=document.path,
                payload={
                    "source_id": source.source_id,
                    "sync_run_id": sync_run_id,
                    "go_proposal_id": go_id,
                    "kind": change.kind,
                },
            )
        return SyncOutcome(
            source_object_id=document.source_object_id,
            path=document.path,
            disposition=disposition,
            code=code,
            go_proposal_id=go_id or None,
            actor_type=actor_type,
        )

    def _cursor_map(self, source_id: str) -> dict[str, _CursorEntry]:
        return self._cursors.setdefault(source_id, {})

    def _commit_cursor(self, source_id: str, document: SyncDocument, change: ChangeRecord) -> None:
        store = self._cursor_map(source_id)
        if change.kind == "deleted":
            store.pop(document.source_object_id, None)
            return
        store[document.source_object_id] = _CursorEntry(
            sha256=document.sha256,
            source_version=document.source_version,
            path=document.path,
        )


def _enforce_content(source: SourceRecord, document: SyncDocument) -> None:
    if document.front_matter is not None:
        enforce_front_matter(document.front_matter)
    if document.markdown:
        enforce_data_barrier(
            data_profile=source.data_profile,
            text=document.markdown,
            legal_basis=source.legal_basis,
            inference_provider=document.inference_provider,
            document_path=document.path,
            document_id=document.source_object_id,
        )


def _detect(cursor: dict[str, _CursorEntry], document: SyncDocument) -> ChangeRecord:
    previous = cursor.get(document.source_object_id)
    if document.action == "delete":
        kind: str = "deleted" if previous is not None else "noop"
    elif previous is None:
        kind = "created"
    elif (
        previous.sha256 == document.sha256
        and previous.source_version == document.source_version
        and previous.path == document.path
    ):
        kind = "noop"
    else:
        kind = "updated"
    return ChangeRecord(
        source_object_id=document.source_object_id,
        path=document.path,
        kind=kind,  # type: ignore[arg-type]
        source_version=document.source_version,
        sha256=document.sha256,
    )


def _bounds_code(
    source: SourceRecord,
    mutating: list[ChangeRecord],
    documents: list[SyncDocument],
) -> str | None:
    if len(mutating) > source.max_files_per_sync:
        return "BOUND_EXCEEDED"
    lines = 0
    mutating_ids = {item.source_object_id for item in mutating}
    for document in documents:
        if document.source_object_id in mutating_ids:
            lines += document.lines_changed
    if lines > source.max_lines_changed:
        return "BOUND_EXCEEDED"
    return None


def _policy(
    source: SourceRecord,
    document: SyncDocument,
    change: ChangeRecord,
    bound_code: str | None,
) -> tuple[str | None, str]:
    if document.ownership_mode == "live_operational":
        return "LIVE_OPERATIONAL_FORBIDDEN", "refused"
    if document.ownership_mode == "curated":
        return "CURATED_DOCUMENT_PROTECTED", "refused"
    if change.kind == "deleted" and not document.tombstone:
        return "TOMBSTONE_REQUIRED", "refused"
    if bound_code:
        return bound_code, "human_review"
    auto = (
        source.trusted
        and source.auto_merge
        and not source.validation_required
        and document.ownership_mode in {"source_managed", "migrated"}
    )
    if auto:
        return None, "merged"
    return None, "human_review"


def _proposal_payload(
    source: SourceRecord,
    document: SyncDocument,
    change: ChangeRecord,
    sync_run_id: str,
    base_sha: str,
) -> dict[str, Any]:
    canonical = json.dumps(
        {
            "source_id": source.source_id,
            "source_object_id": document.source_object_id,
            "sha256": document.sha256,
            "kind": change.kind,
            "sync_run_id": sync_run_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    proposal_sha = hashlib.sha1(canonical.encode("utf-8"), usedforsecurity=False).hexdigest()
    return {
        "space_id": source.space_id,
        "proposal_sha": proposal_sha,
        "base_sha": base_sha,
        "target_branch": "main",
        "idempotency_key": f"{sync_run_id}:{document.source_object_id}",
        "proposal_data": {
            "actor_type": "source_sync",
            "author_stable_id": "source-sync-bot",
            "requester_stable_id": "source-sync-bot",
            "source_id": source.source_id,
            "source_version": document.source_version,
            "sync_run_id": sync_run_id,
            "path": document.path,
            "kind": change.kind,
            "tombstone": document.tombstone,
            "origin": {
                "schema": "source-origin-v1",
                "source_id": source.source_id,
                "source_version": document.source_version,
                "source_content_sha256": document.sha256,
            },
        },
    }
