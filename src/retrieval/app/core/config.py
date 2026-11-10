"""Pydantic Settings for the Retrieval + Indexing adapter."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables.

    Environment variables are read using service-prefixed aliases
    (e.g. ``RETRIEVAL_DATABASE_URL``) with the unprefixed name as a fallback.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb",
        description="SQLAlchemy database URL.",
        validation_alias=AliasChoices("RETRIEVAL_DATABASE_URL", "DATABASE_URL"),
    )
    KB_INDEX_SCHEMA: str | None = Field(
        default="kb_index",
        description="PostgreSQL schema for index tables. Empty/unset disables schema qualification (useful for SQLite tests).",
        validation_alias=AliasChoices("RETRIEVAL_KB_INDEX_SCHEMA", "KB_INDEX_SCHEMA"),
    )
    IDENTITY_SERVICE_URL: str = Field(
        default="http://localhost:8001",
        description="Base URL of the Identity + AuthZ service.",
        validation_alias=AliasChoices("RETRIEVAL_IDENTITY_SERVICE_URL", "IDENTITY_SERVICE_URL"),
    )
    GO_SERVICE_URL: str = Field(
        default="http://localhost:8002",
        description="Base URL of the Git Orchestrator service.",
        validation_alias=AliasChoices("RETRIEVAL_GO_SERVICE_URL", "GO_SERVICE_URL"),
    )
    GO_CLIENT_MODE: str = Field(
        default="http",
        description="GO client mode: 'http' for HttpGOClient, 'stub' for in-memory synthetic fixture.",
        validation_alias=AliasChoices("RETRIEVAL_GO_CLIENT_MODE", "GO_CLIENT_MODE"),
    )
    EMBEDDING_DIMENSIONS: int = Field(
        default=384,
        description="Dimensionality of embedding vectors.",
        validation_alias=AliasChoices("RETRIVAL_EMBEDDING_DIMENSIONS", "EMBEDDING_DIMENSIONS"),
    )
    EMBEDDING_MODEL: str = Field(
        default="stub-deterministic",
        description="Embedding model identifier; 'stub-deterministic' uses the test stub, 'kimi' uses kimi.ai.",
        validation_alias=AliasChoices("RETRIEVAL_EMBEDDING_MODEL", "EMBEDDING_MODEL"),
    )
    KIMI_API_BASE_URL: str = Field(
        default="https://api.kimi.com/coding/v1",
        description="Base URL for the kimi.ai API.",
        validation_alias="KIMI_API_BASE_URL",
    )
    KIMI_API_KEY: str = Field(
        default="",
        description="API key for kimi.ai. Never log or expose this value.",
        validation_alias="KIMI_API_KEY",
    )
    KIMI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-v2",
        description="Model identifier passed to the kimi.ai embeddings endpoint.",
        validation_alias="KIMI_EMBEDDING_MODEL",
    )
    SEARCH_TOP_K: int = Field(
        default=10,
        description="Default number of ranked results to return.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        validation_alias=AliasChoices("RETRIEVAL_LOG_LEVEL", "LOG_LEVEL"),
    )

    @field_validator("KB_INDEX_SCHEMA", mode="before")
    @classmethod
    def _empty_schema_means_none(cls, value: object) -> str | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if not isinstance(value, str):
            return str(value)
        return value


settings = Settings()
