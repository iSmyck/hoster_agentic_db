"""Pytest fixtures for the Retrieval + Indexing adapter.

These fixtures force SQLite in-memory mode with schema qualification disabled
so the same SQLAlchemy models work without PostgreSQL JSONB and pgvector.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Configure SQLite test mode before any app module is imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("KB_INDEX_SCHEMA", "")
os.environ.setdefault("EMBEDDING_MODEL", "stub-deterministic")

from retrieval.app.adapters.embeddings import StubEmbeddingAdapter
from retrieval.app.adapters.go_client import StubGOClient
from retrieval.app.adapters.identity_client import StubIdentityClient
from retrieval.app.main import create_app
from retrieval.app.models.index import Base
from retrieval.app.repositories.db import get_db


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
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def identity_client() -> StubIdentityClient:
    return StubIdentityClient()


@pytest.fixture
def go_client() -> StubGOClient:
    return StubGOClient()


@pytest.fixture
def embedding_adapter() -> StubEmbeddingAdapter:
    return StubEmbeddingAdapter(dimensions=384)


@pytest.fixture
def client(
    engine: Any,
    tables: Any,
    identity_client: StubIdentityClient,
    go_client: StubGOClient,
    embedding_adapter: StubEmbeddingAdapter,
) -> Generator[TestClient, None, None]:
    app = create_app(
        identity_client=identity_client,
        go_client=go_client,
        embedding_adapter=embedding_adapter,
    )

    async def _override_get_db() -> AsyncGenerator[Session, None]:
        session_factory = sessionmaker(bind=engine)
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def actor_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def space_id() -> str:
    return "demo-space"


@pytest.fixture
def snapshot_sha() -> str:
    return "a" * 40
