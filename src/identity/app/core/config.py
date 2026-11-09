"""Pydantic Settings for the Identity + AuthZ adapter."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables.

    Environment variables are read using service-prefixed aliases
    (e.g. ``IDENTITY_DATABASE_URL``) with the unprefixed name as a fallback.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb",
        description="SQLAlchemy database URL.",
        validation_alias=AliasChoices("IDENTITY_DATABASE_URL", "DATABASE_URL"),
    )
    KB_AUTHZ_SCHEMA: str | None = Field(
        default="kb_authz",
        description="PostgreSQL schema for authz tables. Empty/unset disables schema qualification (useful for SQLite tests).",
        validation_alias=AliasChoices("IDENTITY_KB_AUTHZ_SCHEMA", "KB_AUTHZ_SCHEMA"),
    )
    ISSUER: str = Field(
        default="corp-ai-db-identity",
        description="AuthzContext issuer identifier.",
    )
    CONTEXT_TTL_SECONDS: int = Field(
        default=900,
        description="Default AuthzContext TTL in seconds.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        validation_alias=AliasChoices("IDENTITY_LOG_LEVEL", "LOG_LEVEL"),
    )

    @field_validator("KB_AUTHZ_SCHEMA", mode="before")
    @classmethod
    def _empty_schema_means_none(cls, value: object) -> str | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if not isinstance(value, str):
            return str(value)
        return value


settings = Settings()
