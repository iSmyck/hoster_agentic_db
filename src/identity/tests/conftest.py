"""Pytest fixtures for identity adapter tests.

These fixtures force SQLite in-memory mode with schema qualification disabled
so the same SQLAlchemy models work without PostgreSQL JSONB.
"""

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
os.environ.setdefault("KB_AUTHZ_SCHEMA", "")

from identity.app.main import create_app
from identity.app.models.authz import Base


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
def client(engine: Any, tables: Any) -> Generator[TestClient, None, None]:
    app = create_app()

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
    from identity.app.repositories.db import get_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
