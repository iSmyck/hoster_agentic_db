"""Request/response models for source-sync (KBI.3)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceRegisterRequest(BaseModel):
    source_type: Literal["n8n", "callback"]
    source_ref: str = Field(min_length=1, max_length=2048)
    credentials_ref: str = Field(min_length=1, max_length=512)
    poll_interval: int = Field(ge=1)
    space_id: str = Field(min_length=1)
    data_profile: Literal["strict", "pii_permitted"]
    validation_required: bool
    auto_merge: bool
    trusted: bool
    legal_basis: str | None = None
    max_files_per_sync: int = Field(default=50, ge=1)
    max_lines_changed: int = Field(default=2000, ge=0)


class SourceRecord(BaseModel):
    source_id: str
    source_type: Literal["n8n", "callback"]
    source_ref: str
    credentials_ref: str
    poll_interval: int
    space_id: str
    data_profile: Literal["strict", "pii_permitted"]
    validation_required: bool
    auto_merge: bool
    trusted: bool
    legal_basis: str | None = None
    max_files_per_sync: int
    max_lines_changed: int


class SyncDocument(BaseModel):
    source_object_id: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    path: str = Field(min_length=1)
    action: Literal["upsert", "delete"]
    ownership_mode: Literal["migrated", "source_managed", "curated", "live_operational"] = (
        "source_managed"
    )
    lines_changed: int = Field(default=0, ge=0)
    tombstone: bool = False
    markdown: str = ""
    front_matter: dict[str, Any] | None = None
    inference_provider: str = "internal"


class SyncRequest(BaseModel):
    documents: list[SyncDocument]
    base_sha: str = Field(default="b" * 40, pattern=r"^[0-9a-f]{40}$")


class ChangeRecord(BaseModel):
    source_object_id: str
    path: str
    kind: Literal["created", "updated", "noop", "deleted"]
    source_version: str
    sha256: str


class SyncOutcome(BaseModel):
    source_object_id: str
    path: str
    disposition: Literal["merged", "human_review", "refused", "noop"]
    code: str | None = None
    go_proposal_id: str | None = None
    actor_type: str | None = None


class SyncReport(BaseModel):
    sync_run_id: str
    source_id: str
    changes: list[ChangeRecord]
    outcomes: list[SyncOutcome]


class NotificationSubscriptionRequest(BaseModel):
    editor_stable_id: str = Field(min_length=1)
    space_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    channel: Literal["log", "webhook"] = "log"


class NotificationSubscription(NotificationSubscriptionRequest):
    subscription_id: str


class SchedulerTickRequest(BaseModel):
    now: str | None = None


class SyncJob(BaseModel):
    job_id: str
    source_id: str
    status: Literal["queued", "running", "done", "skipped", "failed"]
    scheduled_at: str


class SchedulerTickReport(BaseModel):
    jobs: list[SyncJob]
    skipped_source_ids: list[str] = Field(default_factory=list)


class DeliveryRecord(BaseModel):
    editor_stable_id: str
    space_id: str
    path: str
    channel: str
    attempts: int
    status: Literal["sent", "failed"]
    detail: dict[str, Any] = Field(default_factory=dict)
