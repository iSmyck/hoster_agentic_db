"""Pytest fixtures for the Backup adapter."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Configure SQLite test mode before any app module is imported.
os.environ.setdefault("BACKUP_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BACKUP_KB_OPS_SCHEMA", "")
os.environ.setdefault("KB_OPS_SCHEMA", "")
os.environ.setdefault("GO_KB_OPS_SCHEMA", "")

import importlib

# The package directory is named with a hyphen, which is not a valid Python
# identifier.  Load the package under its real name, then mirror every loaded
# module under the ``git_orchestrator`` alias so test code can use normal
# import statements.
_SRC = Path(__file__).resolve().parents[2]  # src/backup/tests -> src
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

importlib.import_module("git-orchestrator.app.main")
for _original in list(sys.modules):
    if _original.startswith("git-orchestrator"):
        _aliased = _original.replace("git-orchestrator", "git_orchestrator")
        sys.modules[_aliased] = sys.modules[_original]

from git_orchestrator.app.models.ops import Base as OpsBase

from backup.app.adapters.gitlab import StubBackupGitLabAdapter
from backup.app.adapters.object_store import StubObjectStoreAdapter
from backup.app.main import create_app
from backup.app.services.backup import BackupService
from backup.app.services.object_store import ObjectStoreService
from backup.app.services.postgres_backup import PostgresBackupService


@pytest.fixture
def engine() -> Any:
    url = os.environ["BACKUP_DATABASE_URL"]
    return create_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def ops_tables(engine: Any) -> Any:
    OpsBase.metadata.create_all(engine)
    yield
    OpsBase.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine: Any, ops_tables: Any) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def tmp_storage_path() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def stub_adapter() -> StubBackupGitLabAdapter:
    return StubBackupGitLabAdapter(
        state={
            ("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "a" * 40}},
            ("mrs", "demo-space"): [
                {
                    "iid": 1,
                    "title": "Add pricing",
                    "state": "merged",
                    "source_branch": "proposal/abc123",
                    "target_branch": "main",
                    "sha": "b" * 40,
                }
            ],
            ("notes", "demo-space", 1): [
                {
                    "id": 101,
                    "body": "DecisionRecord accepted",
                    "author_id": 7,
                    "created_at": "2026-11-10T10:00:00Z",
                }
            ],
            ("tags", "demo-space"): [
                {"name": "kb-decisions/d-1", "target": "c" * 40, "message": "accepted"}
            ],
        }
    )


@pytest.fixture
def synthetic_git_repo(tmp_storage_path: Path) -> Path:
    """Create a tiny bare repo at ``{tmp}/demo-space.git`` for local mirror tests."""
    origin = tmp_storage_path / "demo-space.git"
    origin.mkdir(parents=True)
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)

    worktree = tmp_storage_path / "worktree"
    worktree.mkdir()
    subprocess.run(
        ["git", "clone", str(origin), str(worktree)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(worktree), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(worktree), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
    )
    (worktree / "README.md").write_text("# Demo Space\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(worktree), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(worktree), "branch", "-M", "main"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(worktree), "push", "origin", "main"],
        check=True,
        capture_output=True,
    )
    return origin


@pytest.fixture
def object_store_adapter() -> StubObjectStoreAdapter:
    return StubObjectStoreAdapter()


@pytest.fixture
def object_store_service(object_store_adapter: StubObjectStoreAdapter) -> ObjectStoreService:
    return ObjectStoreService(object_store_adapter)


@pytest.fixture
def postgres_backup_service() -> PostgresBackupService:
    def fake_run(*args: Any, **kwargs: Any) -> Any:
        class Result:
            returncode = 0
            stderr = b""

        stdout = kwargs.get("stdout")
        if stdout is not None:
            stdout.write(b"-- synthetic pg_dump\n")
        return Result()

    return PostgresBackupService(
        host="localhost",
        port=5432,
        user="u",
        password="p",
        db="db",
        schemas=["kb_authz", "kb_ops", "kb_index"],
        run_command=fake_run,
    )


@pytest.fixture
def backup_service(
    engine: Any,
    stub_adapter: StubBackupGitLabAdapter,
    tmp_storage_path: Path,
) -> BackupService:
    return BackupService(
        adapter=stub_adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url=str(tmp_storage_path),
        gitlab_token="",
        project_path_prefix="origin.git/",  # synthetic mirror clone path
        kb_ops_schema=None,
    )


@pytest.fixture
def client(
    engine: Any,
    ops_tables: Any,
    stub_adapter: StubBackupGitLabAdapter,
    tmp_storage_path: Path,
    synthetic_git_repo: Path,
    object_store_adapter: StubObjectStoreAdapter,
    postgres_backup_service: PostgresBackupService,
) -> Generator[TestClient, None, None]:
    service = BackupService(
        adapter=stub_adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url=str(synthetic_git_repo.parent),
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
        object_store_adapter=object_store_adapter,
        postgres_backup_service=postgres_backup_service,
    )
    app = create_app(service=service)

    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
