"""Pydantic Settings for the Ingestion adapter."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables.

    Environment variables are read using service-prefixed aliases
    (e.g. ``INGESTION_DATABASE_URL``) with the unprefixed name as a fallback.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb",
        description="SQLAlchemy database URL.",
        validation_alias=AliasChoices("INGESTION_DATABASE_URL", "DATABASE_URL"),
    )
    KB_OPS_SCHEMA: str | None = Field(
        default="kb_ops",
        description="PostgreSQL schema for ingestion operational tables. "
        "Empty/unset disables schema qualification (useful for SQLite tests).",
        validation_alias=AliasChoices("INGESTION_KB_OPS_SCHEMA", "KB_OPS_SCHEMA"),
    )
    GO_SERVICE_URL: str = Field(
        default="http://localhost:8002",
        description="Git Orchestrator service base URL.",
        validation_alias=AliasChoices("INGESTION_GO_SERVICE_URL", "GO_SERVICE_URL"),
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        validation_alias=AliasChoices("INGESTION_LOG_LEVEL", "LOG_LEVEL"),
    )

    @field_validator("KB_OPS_SCHEMA", mode="before")
    @classmethod
    def _empty_schema_means_none(cls, value: object) -> str | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if not isinstance(value, str):
            return str(value)
        return value


settings = Settings()
