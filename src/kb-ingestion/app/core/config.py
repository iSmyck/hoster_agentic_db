"""Runtime configuration for the kb-ingestion service."""

from __future__ import annotations

from pydantic import Field
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


settings = Settings()