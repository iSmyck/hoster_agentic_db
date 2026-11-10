"""Pytest fixtures for the Git Orchestrator adapter.

These fixtures force SQLite in-memory mode with schema qualification disabled
so the same SQLAlchemy models work without PostgreSQL JSONB.
"""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Configure SQLite test mode before any app module is imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("KB_OPS_SCHEMA", "")

# The package directory is named with a hyphen, which is not a valid Python
# identifier.  Load the package under its real name, then mirror every loaded
# module under the ``git_orchestrator`` alias so test code can use normal
# import statements.
_SRC = Path(__file__).resolve().parents[2]  # src/git-orchestrator/tests -> src
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

importlib.import_module("git-orchestrator.app.main")
for _original in list(sys.modules):
    if _original.startswith("git-orchestrator"):
        _aliased = _original.replace("git-orchestrator", "git_orchestrator")
        sys.modules[_aliased] = sys.modules[_original]

from fastapi import Request
from git_orchestrator.app.adapters.gitlab import StubGitLabAdapter
from git_orchestrator.app.api.auth import AuthenticatedIdentity, get_current_identity
from git_orchestrator.app.core.config import settings
from git_orchestrator.app.main import create_app
from git_orchestrator.app.models.ops import Base
from git_orchestrator.app.repositories.db import get_db


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
def stub_adapter() -> StubGitLabAdapter:
    return StubGitLabAdapter()


@pytest.fixture
def client(
    engine: Any,
    tables: Any,
    stub_adapter: StubGitLabAdapter,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(settings, "KB_ALLOWED_SPACE_IDS", "corp-kb/sales,demo-space")
    app = create_app(adapter=stub_adapter)

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

    def _override_identity(request: Request) -> AuthenticatedIdentity:
        if request.url.path.endswith("/decisions") or request.url.path.endswith(
            ("/merge", "/reconcile")
        ):
            return AuthenticatedIdentity(stable_id="approver-1", role="admin")
        return AuthenticatedIdentity(stable_id="author-1", role="user")

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_identity] = _override_identity
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
