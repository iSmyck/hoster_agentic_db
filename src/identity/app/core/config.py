"""Pydantic Settings for the Identity + AuthZ adapter."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator, model_validator
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

    KEYCLOAK_URL: str = Field(
        default="http://localhost:8082",
        description="Keycloak base URL.",
        validation_alias=AliasChoices("IDENTITY_KEYCLOAK_URL", "KEYCLOAK_URL"),
    )
    KEYCLOAK_REALM: str = Field(
        default="corp-kb",
        description="Keycloak realm name.",
        validation_alias=AliasChoices("IDENTITY_KEYCLOAK_REALM", "KEYCLOAK_REALM"),
    )
    KEYCLOAK_CLIENT_ID: str = Field(
        default="identity-service",
        description="Keycloak client id.",
        validation_alias=AliasChoices("IDENTITY_KEYCLOAK_CLIENT_ID", "KEYCLOAK_CLIENT_ID"),
    )
    KEYCLOAK_CLIENT_SECRET: str = Field(
        default="",
        description="Keycloak client secret.",
        validation_alias=AliasChoices("IDENTITY_KEYCLOAK_CLIENT_SECRET", "KEYCLOAK_CLIENT_SECRET"),
    )
    IDENTITY_ADAPTER: str = Field(
        default="stub",
        description="Identity adapter implementation: 'stub' or 'keycloak'.",
        validation_alias=AliasChoices("IDENTITY_ADAPTER"),
    )

    @field_validator("KB_AUTHZ_SCHEMA", mode="before")
    @classmethod
    def _empty_schema_means_none(cls, value: object) -> str | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if not isinstance(value, str):
            return str(value)
        return value

    @field_validator("IDENTITY_ADAPTER")
    @classmethod
    def _valid_identity_adapter(cls, value: str) -> str:
        allowed = {"stub", "keycloak"}
        if value.lower() not in allowed:
            raise ValueError(f"IDENTITY_ADAPTER must be one of {allowed!r}")
        return value.lower()

    @model_validator(mode="after")
    def _keycloak_secret_required(self) -> Settings:
        if self.IDENTITY_ADAPTER == "keycloak" and not self.KEYCLOAK_CLIENT_SECRET:
            raise ValueError("KEYCLOAK_CLIENT_SECRET is required when IDENTITY_ADAPTER=keycloak")
        return self


settings = Settings()
