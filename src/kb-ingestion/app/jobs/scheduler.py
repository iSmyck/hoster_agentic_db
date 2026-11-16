"""Source-sync scheduler / poller (KBI.3.5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from ..schemas.source_sync import SchedulerTickReport, SyncJob
from ..services.source_sync import SourceRegistry, SourceSyncService


class Scheduler:
    def __init__(self, registry: SourceRegistry, sync: SourceSyncService) -> None:
        self._registry = registry
        self._sync = sync

    def tick(self, now: datetime | None = None) -> SchedulerTickReport:
        moment = now or datetime.now(UTC)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        jobs: list[SyncJob] = []
        skipped: list[str] = []
        for source in self._registry.list_all():
            in_flight = self._sync.in_flight_job(source.source_id)
            if in_flight is not None or self._sync.is_running(source.source_id):
                skipped.append(source.source_id)
                jobs.append(
                    SyncJob(
                        job_id=uuid.uuid4().hex,
                        source_id=source.source_id,
                        status="skipped",
                        scheduled_at=moment.isoformat(),
                    )
                )
                continue
            last = self._sync.last_queued_at(source.source_id)
            due = last is None or moment >= last + timedelta(seconds=source.poll_interval)
            if not due:
                continue
            job = self._sync.enqueue_job(source.source_id, moment)
            jobs.append(job)
        return SchedulerTickReport(jobs=jobs, skipped_source_ids=skipped)
