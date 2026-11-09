"""Pydantic Settings for the Retrieval + Indexing adapter."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables.

    Environment variables are read without a prefix, e.g. ``DATABASE_URL``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb",
        description="SQLAlchemy database URL.",
    )
    KB_INDEX_SCHEMA: str | None = Field(
        default="kb_index",
        description="PostgreSQL schema for index tables. Empty/unset disables schema qualification (useful for SQLite tests).",
    )
    IDENTITY_SERVICE_URL: str = Field(
        default="http://localhost:8001",
        description="Base URL of the Identity + AuthZ service.",
    )
    GO_SERVICE_URL: str = Field(
        default="http://localhost:8002",
        description="Base URL of the Git Orchestrator service.",
    )
    EMBEDDING_DIMENSIONS: int = Field(
        default=384,
        description="Dimensionality of embedding vectors.",
    )
    EMBEDDING_MODEL: str = Field(
        default="stub-deterministic",
        description="Embedding model identifier; 'stub-deterministic' uses the test stub.",
    )
    SEARCH_TOP_K: int = Field(
        default=10,
        description="Default number of ranked results to return.",
    )
    LOG_LEVEL: str = Field(default="INFO")

    @field_validator("KB_INDEX_SCHEMA", mode="before")
    @classmethod
    def _empty_schema_means_none(cls, value: object) -> str | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if not isinstance(value, str):
            return str(value)
        return value


settings = Settings()
