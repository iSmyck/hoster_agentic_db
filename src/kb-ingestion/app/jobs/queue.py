"""In-memory ingestion job queue with retry and DLQ (KBI.4.3)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta

from ..schemas.jobs import IngestionJob, JobMetrics

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+")
_MAX_BACKOFF = 60


def sanitize_error(message: str) -> str:
    redacted = _BEARER.sub("[redacted-token]", message)
    return _EMAIL.sub("[redacted-email]", redacted)


class JobQueueError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class InMemoryJobQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}

    def enqueue(
        self,
        kind: str,
        payload: dict,
        *,
        max_attempts: int = 3,
        now: datetime | None = None,
    ) -> IngestionJob:
        moment = _aware(now)
        job = IngestionJob(
            job_id=uuid.uuid4().hex,
            kind=kind,
            payload=dict(payload),
            status="queued",
            attempts=0,
            max_attempts=max_attempts,
            next_run_at=moment.isoformat(),
            queued_at=moment.isoformat(),
            updated_at=moment.isoformat(),
        )
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> IngestionJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobQueueError("JOB_NOT_FOUND", "job not found", http_status=404)
        return job

    def claim_due(self, now: datetime | None = None) -> IngestionJob | None:
        moment = _aware(now)
        due: list[IngestionJob] = []
        for job in self._jobs.values():
            if job.status not in {"queued", "retry"}:
                continue
            if datetime.fromisoformat(job.next_run_at) > moment:
                continue
            due.append(job)
        if not due:
            return None
        due.sort(key=lambda item: (item.next_run_at, item.queued_at))
        job = due[0]
        job.status = "running"
        job.updated_at = moment.isoformat()
        return job

    def succeed(self, job_id: str, *, now: datetime | None = None) -> IngestionJob:
        job = self.get(job_id)
        moment = _aware(now)
        job.status = "done"
        job.outcome = "done"
        job.last_error = ""
        job.updated_at = moment.isoformat()
        return job

    def fail(
        self,
        job_id: str,
        error: str,
        *,
        retryable: bool,
        now: datetime | None = None,
    ) -> IngestionJob:
        job = self.get(job_id)
        moment = _aware(now)
        job.attempts += 1
        job.last_error = sanitize_error(error)
        job.updated_at = moment.isoformat()
        exhausted = (not retryable) or job.attempts >= job.max_attempts
        if exhausted:
            job.status = "dead"
            job.outcome = "dead"
            return job
        delay = min(_MAX_BACKOFF, 2 ** (job.attempts - 1))
        job.status = "retry"
        job.outcome = "retry"
        job.next_run_at = (moment + timedelta(seconds=delay)).isoformat()
        return job

    def process_one(
        self,
        *,
        now: datetime | None = None,
        inject: str = "none",
    ) -> IngestionJob | None:
        job = self.claim_due(now)
        if job is None:
            return None
        if inject == "transient":
            return self.fail(job.job_id, "injected transient failure", retryable=True, now=now)
        if inject == "permanent":
            return self.fail(
                job.job_id,
                "injected permanent failure Bearer secret-token user@example.com",
                retryable=False,
                now=now,
            )
        return self.succeed(job.job_id, now=now)

    def metrics(self, now: datetime | None = None) -> JobMetrics:
        moment = _aware(now)
        counts = {"queued": 0, "retry": 0, "running": 0, "done": 0, "dead": 0}
        attempts_total = 0
        lag = 0.0
        for job in self._jobs.values():
            counts[job.status] = counts.get(job.status, 0) + 1
            attempts_total += job.attempts
            if job.status in {"queued", "retry"}:
                queued = datetime.fromisoformat(job.queued_at)
                lag = max(lag, (moment - queued).total_seconds())
        return JobMetrics(
            queued=counts["queued"],
            retry=counts["retry"],
            running=counts["running"],
            done=counts["done"],
            dead=counts["dead"],
            lag_seconds=lag,
            attempts_total=attempts_total,
            outcomes={"done": counts["done"], "dead": counts["dead"], "retry": counts["retry"]},
        )


def _aware(value: datetime | None) -> datetime:
    moment = value or datetime.now(UTC)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment
