"""Pydantic Settings for the Session service."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables.

    Environment variables are read using service-prefixed aliases
    (e.g. ``SESSION_DATABASE_URL``) with the unprefixed name as a fallback.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://corp_kb:corp_kb_dev@localhost:5432/corp_kb",
        description="SQLAlchemy database URL.",
        validation_alias=AliasChoices("SESSION_DATABASE_URL", "DATABASE_URL"),
    )
    KB_SESSIONS_SCHEMA: str | None = Field(
        default="kb_sessions",
        description="PostgreSQL schema for session tables. Empty/unset disables schema qualification (useful for SQLite tests).",
        validation_alias=AliasChoices("SESSION_KB_SESSIONS_SCHEMA", "KB_SESSIONS_SCHEMA"),
    )
    SECRET_KEY: str = Field(
        default="change-me-in-production-immediately",
        description="HMAC secret for signing session tokens. Must be at least 32 bytes for HS256.",
        validation_alias=AliasChoices("SESSION_SECRET_KEY", "SECRET_KEY"),
    )
    ACCESS_TTL_SECONDS: int = Field(
        default=900,
        description="Access token TTL in seconds.",
        validation_alias=AliasChoices("SESSION_ACCESS_TTL_SECONDS", "ACCESS_TTL_SECONDS"),
    )
    REFRESH_TTL_SECONDS: int = Field(
        default=86400,
        description="Refresh token TTL in seconds.",
        validation_alias=AliasChoices("SESSION_REFRESH_TTL_SECONDS", "REFRESH_TTL_SECONDS"),
    )
    ISSUER: str = Field(
        default="corp-ai-db-session",
        description="JWT issuer claim.",
        validation_alias=AliasChoices("SESSION_ISSUER", "ISSUER"),
    )
    IDENTITY_SERVICE_URL: str = Field(
        default="http://localhost:8001",
        description="Base URL of the Identity + AuthZ adapter for OIDC token resolution.",
        validation_alias=AliasChoices("SESSION_IDENTITY_SERVICE_URL", "IDENTITY_SERVICE_URL"),
    )
    OIDC_ADMIN_GROUP: str = Field(
        default="kb-approvers",
        description="Keycloak group that grants admin/approver role in G1.",
        validation_alias=AliasChoices("SESSION_OIDC_ADMIN_GROUP", "OIDC_ADMIN_GROUP"),
    )
    OIDC_ISSUER: str = Field(
        default="",
        description="Expected OIDC issuer URL substring. When empty, OIDC fallback is disabled.",
        validation_alias=AliasChoices("SESSION_OIDC_ISSUER", "OIDC_ISSUER"),
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        validation_alias=AliasChoices("SESSION_LOG_LEVEL", "LOG_LEVEL"),
    )

    @field_validator("KB_SESSIONS_SCHEMA", mode="before")
    @classmethod
    def _empty_schema_means_none(cls, value: object) -> str | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if not isinstance(value, str):
            return str(value)
        return value


settings = Settings()
