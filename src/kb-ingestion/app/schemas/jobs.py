"""Job queue request/response models (KBI.4.3)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class JobEnqueueRequest(BaseModel):
    kind: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=10)
    now: str | None = None


class IngestionJob(BaseModel):
    job_id: str
    kind: str
    payload: dict[str, Any]
    status: Literal["queued", "running", "retry", "done", "dead"]
    attempts: int = 0
    max_attempts: int = 3
    next_run_at: str
    last_error: str = ""
    outcome: str | None = None
    queued_at: str
    updated_at: str


class JobTickRequest(BaseModel):
    now: str | None = None
    inject: Literal["none", "transient", "permanent"] = "none"


class JobTickReport(BaseModel):
    processed: int
    job: IngestionJob | None = None


class JobMetrics(BaseModel):
    queued: int
    retry: int
    running: int
    done: int
    dead: int
    lag_seconds: float
    attempts_total: int
    outcomes: dict[str, int]
