"""Pydantic Settings for the Backup adapter."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables.

    Environment variables are read using service-prefixed ``BACKUP_*`` aliases
    with the unprefixed name as a fallback.  GitLab credentials fall back to
    ``GO_GITLAB_URL``/``GO_GITLAB_TOKEN`` so local development does not need
    duplicate credentials.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BACKUP_STORAGE_PATH: str = Field(
        default="_bmad-output/test-artifacts/d1/backups",
        description="Root directory for per-Space backup packages.",
    )
    BACKUP_GITLAB_URL: str = Field(
        default="http://localhost:8081",
        description="GitLab instance base URL.",
        validation_alias=AliasChoices("BACKUP_GITLAB_URL", "GO_GITLAB_URL", "GITLAB_URL"),
    )
    BACKUP_GITLAB_TOKEN: str = Field(
        default="",
        description="GitLab API token for the backup identity.",
        validation_alias=AliasChoices("BACKUP_GITLAB_TOKEN", "GO_GITLAB_TOKEN", "GITLAB_TOKEN"),
    )
    BACKUP_GITLAB_PROJECT_PATH_PREFIX: str = Field(
        default="",
        description="Optional prefix when mapping space_id to a GitLab project path.",
        validation_alias=AliasChoices(
            "BACKUP_GITLAB_PROJECT_PATH_PREFIX", "GO_GITLAB_PROJECT_PATH_PREFIX"
        ),
    )
    BACKUP_DATABASE_URL: str = Field(
        default="postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb",
        description="SQLAlchemy database URL for kb_ops read-only export.",
        validation_alias=AliasChoices("BACKUP_DATABASE_URL", "DATABASE_URL"),
    )
    BACKUP_KB_OPS_SCHEMA: str | None = Field(
        default="kb_ops",
        description="PostgreSQL schema for kb_ops tables. "
        "Empty/unset disables schema qualification (useful for SQLite tests).",
        validation_alias=AliasChoices("BACKUP_KB_OPS_SCHEMA", "GO_KB_OPS_SCHEMA", "KB_OPS_SCHEMA"),
    )

    # Object store (MinIO/S3) staging settings.
    BACKUP_MINIO_ENDPOINT: str = Field(
        default="localhost:9000",
        description="MinIO/S3 endpoint (host:port).",
        validation_alias=AliasChoices("BACKUP_MINIO_ENDPOINT", "MINIO_ENDPOINT"),
    )
    BACKUP_MINIO_ACCESS_KEY: str = Field(
        default="",
        description="MinIO/S3 access key.",
        validation_alias=AliasChoices("BACKUP_MINIO_ACCESS_KEY", "MINIO_ACCESS_KEY"),
    )
    BACKUP_MINIO_SECRET_KEY: str = Field(
        default="",
        description="MinIO/S3 secret key.",
        validation_alias=AliasChoices("BACKUP_MINIO_SECRET_KEY", "MINIO_SECRET_KEY"),
    )
    BACKUP_MINIO_USE_SSL: bool = Field(
        default=False,
        description="Use HTTPS for MinIO/S3 requests.",
        validation_alias=AliasChoices("BACKUP_MINIO_USE_SSL", "MINIO_USE_SSL"),
    )
    BACKUP_MINIO_BUCKET: str = Field(
        default="kb-backups",
        description="Single MinIO/S3 bucket used with space_id prefixes.",
        validation_alias=AliasChoices("BACKUP_MINIO_BUCKET", "MINIO_BUCKET"),
    )
    BACKUP_MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=100 * 1024 * 1024,
        description="Maximum allowed object upload size in bytes.",
        validation_alias=AliasChoices("BACKUP_MAX_UPLOAD_SIZE_BYTES", "MAX_UPLOAD_SIZE_BYTES"),
    )

    # PostgreSQL backup settings (read-only pg_dump source).
    BACKUP_POSTGRES_HOST: str = Field(
        default="localhost",
        validation_alias=AliasChoices("BACKUP_POSTGRES_HOST", "POSTGRES_HOST"),
    )
    BACKUP_POSTGRES_PORT: int = Field(
        default=5432,
        validation_alias=AliasChoices("BACKUP_POSTGRES_PORT", "POSTGRES_PORT"),
    )
    BACKUP_POSTGRES_USER: str = Field(
        default="corp_kb",
        validation_alias=AliasChoices("BACKUP_POSTGRES_USER", "POSTGRES_USER"),
    )
    BACKUP_POSTGRES_PASSWORD: str = Field(
        default="corp_kb_dev",
        validation_alias=AliasChoices("BACKUP_POSTGRES_PASSWORD", "POSTGRES_PASSWORD"),
    )
    BACKUP_POSTGRES_DB: str = Field(
        default="corp_kb",
        validation_alias=AliasChoices("BACKUP_POSTGRES_DB", "POSTGRES_DB"),
    )
    BACKUP_POSTGRES_SCHEMAS: str = Field(
        default="kb_authz,kb_ops,kb_index",
        description="Comma-separated operational schemas to back up.",
        validation_alias=AliasChoices("BACKUP_POSTGRES_SCHEMAS", "BACKUP_SCHEMAS"),
    )

    # Restore target environment credentials (separate from source backup settings).
    BACKUP_RESTORE_GITLAB_URL: str = Field(
        default="http://localhost:8081",
        description="GitLab instance base URL for restore target.",
        validation_alias=AliasChoices("BACKUP_RESTORE_GITLAB_URL"),
    )
    BACKUP_RESTORE_GITLAB_TOKEN: str = Field(
        default="",
        description="GitLab API token for the restore target identity.",
        validation_alias=AliasChoices("BACKUP_RESTORE_GITLAB_TOKEN"),
    )
    BACKUP_RESTORE_GITLAB_PROJECT_PATH_PREFIX: str = Field(
        default="",
        description="Optional prefix when mapping target space_id to a GitLab project path.",
        validation_alias=AliasChoices("BACKUP_RESTORE_GITLAB_PROJECT_PATH_PREFIX"),
    )
    BACKUP_RESTORE_POSTGRES_HOST: str = Field(
        default="localhost",
        validation_alias=AliasChoices("BACKUP_RESTORE_POSTGRES_HOST"),
    )
    BACKUP_RESTORE_POSTGRES_PORT: int = Field(
        default=5432,
        validation_alias=AliasChoices("BACKUP_RESTORE_POSTGRES_PORT"),
    )
    BACKUP_RESTORE_POSTGRES_USER: str = Field(
        default="corp_kb_restore",
        validation_alias=AliasChoices("BACKUP_RESTORE_POSTGRES_USER"),
    )
    BACKUP_RESTORE_POSTGRES_PASSWORD: str = Field(
        default="",
        validation_alias=AliasChoices("BACKUP_RESTORE_POSTGRES_PASSWORD"),
    )
    BACKUP_RESTORE_POSTGRES_DB: str = Field(
        default="corp_kb_restore",
        validation_alias=AliasChoices("BACKUP_RESTORE_POSTGRES_DB"),
    )
    BACKUP_RESTORE_MINIO_ENDPOINT: str = Field(
        default="localhost:9000",
        validation_alias=AliasChoices("BACKUP_RESTORE_MINIO_ENDPOINT"),
    )
    BACKUP_RESTORE_MINIO_ACCESS_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("BACKUP_RESTORE_MINIO_ACCESS_KEY"),
    )
    BACKUP_RESTORE_MINIO_SECRET_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("BACKUP_RESTORE_MINIO_SECRET_KEY"),
    )
    BACKUP_RESTORE_MINIO_USE_SSL: bool = Field(
        default=False,
        validation_alias=AliasChoices("BACKUP_RESTORE_MINIO_USE_SSL"),
    )
    BACKUP_RESTORE_MINIO_BUCKET: str = Field(
        default="kb-restores",
        validation_alias=AliasChoices("BACKUP_RESTORE_MINIO_BUCKET"),
    )
    RUN_LIVE_RESTORE_TESTS: bool = Field(
        default=False,
        validation_alias=AliasChoices("RUN_LIVE_RESTORE_TESTS"),
    )

    LOG_LEVEL: str = Field(
        default="INFO",
        validation_alias=AliasChoices("BACKUP_LOG_LEVEL", "LOG_LEVEL"),
    )

    @field_validator("BACKUP_KB_OPS_SCHEMA", mode="before")
    @classmethod
    def _empty_schema_means_none(cls, value: object) -> str | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if not isinstance(value, str):
            return str(value)
        return value


settings = Settings()
