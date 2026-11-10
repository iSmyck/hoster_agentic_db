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
