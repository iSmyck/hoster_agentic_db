"""Pydantic Settings for the Retrieval + Indexing adapter."""

from __future__ import annotations

from typing import Literal

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
    GO_CLIENT_MODE: Literal["http", "stub"] = Field(
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

    # Benchmark harness configuration. These only affect the synthetic
    # retrieval benchmark and are ignored by the production service.
    BENCHMARK_QUERY_COUNT: int = Field(
        default=-1,
        ge=-1,
        description="Number of golden queries to run; -1 runs the full synthetic set.",
    )
    BENCHMARK_K: int = Field(
        default=5,
        ge=1,
        description="Cut-off rank for recall@k and MRR computations.",
    )
    BENCHMARK_MODE: Literal["semantic", "exact", "hybrid"] = Field(
        default="exact",
        description="Search mode used by the benchmark harness.",
    )
    BENCHMARK_CORPUS_SIZE: int = Field(
        default=10,
        ge=1,
        description="Number of topics in the synthetic Russian corpus.",
    )
    BENCHMARK_RECALL_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum average recall@k for a passing synthetic run.",
    )
    BENCHMARK_MRR_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum mean reciprocal rank for a passing synthetic run.",
    )
    BENCHMARK_P95_MS_THRESHOLD: float = Field(
        default=1000.0,
        ge=0.0,
        description="Maximum p95 latency (ms) for a passing synthetic run.",
    )
    BENCHMARK_OUTPUT_PATH: str = Field(
        default="_bmad-output/test-artifacts/b3/synthetic-retrieval-benchmark.json",
        description="Path to the JSON benchmark report, relative to the project root.",
    )
    BENCHMARK_EMBEDDING_MODEL: str = Field(
        default="stub-deterministic",
        description="Embedding model used by the benchmark harness; 'stub-deterministic' or 'kimi'.",
        validation_alias=AliasChoices("RETRIEVAL_BENCHMARK_EMBEDDING_MODEL", "BENCHMARK_EMBEDDING_MODEL"),
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
