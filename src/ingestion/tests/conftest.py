"""Pytest fixtures for ingestion adapter tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Configure SQLite test mode before any app module is imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("KB_OPS_SCHEMA", "")
os.environ.setdefault("GO_SERVICE_URL", "")

from ingestion.app.adapters.go_client import StubGOClient
from ingestion.app.adapters.source_connector import (
    SOURCE_CONNECTOR_REGISTRY,
    SourceConnector,
    SourceEntry,
    SourceScanResult,
)
from ingestion.app.main import create_app
from ingestion.app.models.ingestion import Base


class TestStubConnector(SourceConnector):
    """Connector that returns fixture entries for tests."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @property
    def source_type(self) -> str:
        return "test_stub"

    def scan(self, cursor: str | None = None) -> SourceScanResult:
        entries = []
        for item in self.config.get("entries", []):
            content = item.get("content", "")
            if isinstance(content, str):
                content = content.encode("utf-8")
            entries.append(
                SourceEntry(
                    path=item["path"],
                    content=content,
                    media_type=item.get("media_type", "text/markdown"),
                    size=len(content),
                    metadata=item.get("metadata", {}),
                )
            )
        return SourceScanResult(
            entries=entries,
            cursor_value=self.config.get("cursor_value", "test-cursor-1"),
            cursor_hash="abc123",
        )


SOURCE_CONNECTOR_REGISTRY["test_stub"] = TestStubConnector


@pytest.fixture
def engine() -> Any:
    url = os.environ["DATABASE_URL"]
    return create_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def tables(engine: Any) -> Any:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine: Any, tables: Any) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def go_client() -> StubGOClient:
    return StubGOClient(
        state={
            "head_sha": "1" * 40,
            "proposal_id": "11111111-1111-1111-1111-111111111111",
        }
    )


@pytest.fixture
def client(
    engine: Any,
    tables: Any,
    go_client: StubGOClient,
) -> Generator[TestClient, None, None]:
    app = create_app(
        go_client=go_client,
        connector_factory=lambda source_type, config: SOURCE_CONNECTOR_REGISTRY[source_type](
            config
        ),
    )

    async def _override_get_db() -> AsyncGenerator[Session, None]:
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides.clear()
    from ingestion.app.repositories.db import get_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def space_id() -> str:
    return "ingest-space"


@pytest.fixture
def source_id() -> str:
    return "wiki-backup"


@pytest.fixture
def clean_source_config() -> dict[str, Any]:
    return {
        "entries": [
            {
                "path": "README.md",
                "content": "# Hello\nThis is a clean markdown file.",
                "media_type": "text/markdown",
            },
            {
                "path": "docs/guide.md",
                "content": "# Guide\nNo blockers here.",
                "media_type": "text/markdown",
            },
        ],
        "cursor_value": "cursor-v1",
    }


@pytest.fixture
def blocked_source_config() -> dict[str, Any]:
    return {
        "entries": [
            {
                "path": "README.md",
                "content": "# Hello\nContact: alice@example.com",
                "media_type": "text/markdown",
            },
            {
                "path": "logo.png",
                "content": "binary-placeholder",
                "media_type": "image/png",
            },
            {
                "path": "script.sh",
                "content": "#!/bin/bash\necho hello",
                "media_type": "text/x-shellscript",
            },
        ],
        "cursor_value": "cursor-v1",
    }
