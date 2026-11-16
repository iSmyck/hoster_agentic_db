"""Runtime configuration for the kb-ingestion service."""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ingestion staging settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    INGEST_MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=104_857_600,
        validation_alias="KB_INGEST_MAX_UPLOAD_SIZE_BYTES",
    )
    INGEST_OBJECT_STORE_BUCKET: str = Field(
        default="kb-ingest",
        validation_alias="KB_INGEST_OBJECT_STORE_BUCKET",
    )
    MINIO_ENDPOINT: str = Field(default="", validation_alias="KB_INGEST_MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="", validation_alias="KB_INGEST_MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="", validation_alias="KB_INGEST_MINIO_SECRET_KEY")
    MINIO_USE_SSL: bool = Field(default=False, validation_alias="KB_INGEST_MINIO_USE_SSL")
    INGEST_GO_BASE_URL: str = Field(default="", validation_alias="KB_INGEST_GO_BASE_URL")
    INGEST_IDENTITY_BASE_URL: str = Field(
        default="",
        validation_alias="KB_INGEST_IDENTITY_BASE_URL",
    )
    INGEST_REQUIRE_IDENTITY: bool = Field(
        default=False,
        validation_alias="KB_INGEST_REQUIRE_IDENTITY",
    )
    INGEST_SESSION_URL: str = Field(
        default="",
        validation_alias="KB_INGEST_SESSION_URL",
    )
    INGEST_GO_AUTHOR_ID: str = Field(
        default="author-1",
        validation_alias="KB_INGEST_GO_AUTHOR_ID",
    )
    INGEST_GO_APPROVER_ID: str = Field(
        default="approver-1",
        validation_alias="KB_INGEST_GO_APPROVER_ID",
    )
    INGEST_GITLAB_URL: str = Field(
        default="",
        validation_alias=AliasChoices("KB_INGEST_GITLAB_URL", "GO_GITLAB_URL", "GITLAB_URL"),
    )
    INGEST_GITLAB_TOKEN: str = Field(
        default="",
        validation_alias=AliasChoices("KB_INGEST_GITLAB_TOKEN", "GO_GITLAB_TOKEN", "GITLAB_TOKEN"),
    )
    DOCLING_EVIDENCE_GATE: bool = Field(
        default=False,
        validation_alias="KB_INGEST_DOCLING_EVIDENCE_GATE",
    )


settings = Settings()