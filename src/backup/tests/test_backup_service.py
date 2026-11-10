"""Unit tests for the BackupService with a stub adapter and synthetic git repo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from git_orchestrator.app.models.ops import DecisionRecord, ProposalRecord
from sqlalchemy.orm import Session

from backup.app.adapters.gitlab import BackupGitLabAdapterError, StubBackupGitLabAdapter
from backup.app.models.backup import BackupStatus
from backup.app.services.backup import BackupService, BackupServiceError


def _insert_proposal(session: Session, space_id: str, proposal_sha: str) -> Any:
    proposal = ProposalRecord(
        space_id=space_id,
        proposal_sha=proposal_sha,
        base_sha="0" * 40,
        idempotency_key=f"key-{proposal_sha}",
    )
    session.add(proposal)
    session.commit()
    return proposal


def _insert_decision(session: Session, proposal: Any) -> Any:
    decision = DecisionRecord(
        proposal_id=proposal.id,
        outcome="accepted",
        actor_id="approver-1",
        idempotency_key=f"decision-{proposal.id}",
        record_sha256="d" * 64,
        tag_name="kb-decisions/d-1",
    )
    session.add(decision)
    session.commit()
    return decision


def test_mirror_backup_creates_package(
    engine: Any,
    ops_tables: Any,
    synthetic_git_repo: Path,
    tmp_storage_path: Path,
) -> None:
    adapter = StubBackupGitLabAdapter(state={("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "a" * 40}}})
    service = BackupService(
        adapter=adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url=str(synthetic_git_repo.parent),
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    package = service.create_mirror_backup("demo-space")

    assert package.status == BackupStatus.COMPLETE
    assert package.space_id == "demo-space"
    assert package.backup_id
    package_path = Path(package.package_path)
    assert (package_path / "mirror.git" / "HEAD").exists()
    assert (package_path / "metadata.json").exists()
    assert (package_path / "kb_ops_export.json").exists()
    assert (package_path / "manifest.json").exists()


def test_metadata_export_contains_mrs_notes_tags(
    engine: Any,
    stub_adapter: StubBackupGitLabAdapter,
    tmp_storage_path: Path,
) -> None:
    service = BackupService(
        adapter=stub_adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url="http://localhost:8081",
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    metadata = service._export_metadata("demo-space")

    assert metadata.space_id == "demo-space"
    assert len(metadata.merge_requests) == 1
    assert metadata.merge_requests[0]["iid"] == 1
    assert "1" in metadata.notes
    assert metadata.notes["1"][0].body == "DecisionRecord accepted"
    assert metadata.tags[0]["name"] == "kb-decisions/d-1"


def test_kb_ops_export_contains_records(
    engine: Any,
    db_session: Session,
    stub_adapter: StubBackupGitLabAdapter,
    tmp_storage_path: Path,
) -> None:
    proposal = _insert_proposal(db_session, "demo-space", "p" * 40)
    _insert_decision(db_session, proposal)

    service = BackupService(
        adapter=stub_adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url="http://localhost:8081",
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    export = service._export_kb_ops("demo-space")

    assert export.space_id == "demo-space"
    assert len(export.proposals) == 1
    assert export.proposals[0]["space_id"] == "demo-space"
    assert len(export.decisions) == 1
    assert str(export.decisions[0]["proposal_id"]).replace("-", "") == str(proposal.id).replace("-", "")


def test_manifest_hashes_match(
    engine: Any,
    ops_tables: Any,
    synthetic_git_repo: Path,
    tmp_storage_path: Path,
) -> None:
    adapter = StubBackupGitLabAdapter(state={("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "a" * 40}}})
    service = BackupService(
        adapter=adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url=str(synthetic_git_repo.parent),
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    package = service.create_mirror_backup("demo-space")
    manifest = package.manifest
    assert manifest is not None

    package_path = Path(package.package_path)
    for file_hash in manifest.files:
        actual = _sha256_file(package_path / file_hash.path)
        assert actual == file_hash.sha256, file_hash.path


def test_idempotency_returns_existing_package(
    engine: Any,
    ops_tables: Any,
    synthetic_git_repo: Path,
    tmp_storage_path: Path,
) -> None:
    adapter = StubBackupGitLabAdapter(state={("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "a" * 40}}})
    service = BackupService(
        adapter=adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url=str(synthetic_git_repo.parent),
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    first = service.create_mirror_backup("demo-space")
    second = service.create_mirror_backup("demo-space")

    assert first.backup_id == second.backup_id
    assert second.status == BackupStatus.COMPLETE


def test_failure_leaves_failed_status(
    engine: Any,
    tmp_storage_path: Path,
) -> None:
    adapter = StubBackupGitLabAdapter(state={("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "a" * 40}}})
    service = BackupService(
        adapter=adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url="http://nonexistent.invalid",
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    with pytest.raises(BackupServiceError):
        service.create_mirror_backup("demo-space")

    space_dir = Path(service.storage_path) / "demo-space"
    assert space_dir.exists()
    status_files = list(space_dir.rglob("status.json"))
    assert status_files, "expected a status.json under the backup package"
    status = json.loads(status_files[0].read_text(encoding="utf-8"))
    assert status["status"] == BackupStatus.FAILED.value
    assert "error" in status


def test_gitlab_unreachable_raises_service_error(
    engine: Any,
    tmp_storage_path: Path,
) -> None:
    class FailingAdapter(StubBackupGitLabAdapter):
        def list_merge_requests(self, space_id: str) -> list[dict[str, Any]]:
            raise BackupGitLabAdapterError("gitlab down")

    adapter = FailingAdapter(state={("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "a" * 40}}})
    service = BackupService(
        adapter=adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url="http://localhost:8081",
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    with pytest.raises(BackupServiceError) as exc_info:
        service.create_mirror_backup("demo-space")
    assert exc_info.value.code == "GITLAB_ERROR"


def test_health_endpoint(client: Any) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_backup_endpoint(client: Any) -> None:
    response = client.post("/api/kb/v1/backups/demo-space/mirror")
    assert response.status_code == 201
    data = response.json()
    assert data["space_id"] == "demo-space"
    assert data["status"] == BackupStatus.COMPLETE.value


def test_latest_backup_endpoint(client: Any) -> None:
    client.post("/api/kb/v1/backups/demo-space/mirror")
    response = client.get("/api/kb/v1/backups/demo-space/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["space_id"] == "demo-space"
    assert data["status"] == BackupStatus.COMPLETE.value
    assert data["manifest"] is not None


def test_latest_backup_not_found(client: Any) -> None:
    response = client.get("/api/kb/v1/backups/missing-space/latest")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


def test_resolve_head_from_branch(
    engine: Any,
    tmp_storage_path: Path,
) -> None:
    adapter = StubBackupGitLabAdapter(
        state={("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "abc123"}}}
    )
    service = BackupService(
        adapter=adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url="http://localhost:8081",
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    head = service._resolve_head("demo-space")
    assert head == "abc123"


def test_kb_ops_error_preserved(
    engine: Any,
    tmp_storage_path: Path,
) -> None:
    class BrokenEngine:
        def connect(self) -> None:
            raise RuntimeError("db down")

    adapter = StubBackupGitLabAdapter(
        state={("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "a" * 40}}}
    )
    service = BackupService(
        adapter=adapter,
        engine=BrokenEngine(),  # type: ignore[arg-type]
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url="http://localhost:8081",
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    with pytest.raises(BackupServiceError) as exc_info:
        service._export_kb_ops("demo-space")
    assert exc_info.value.code == "KB_OPS_ERROR"


def test_invalid_space_id_rejected(
    engine: Any,
    tmp_storage_path: Path,
) -> None:
    adapter = StubBackupGitLabAdapter()
    service = BackupService(
        adapter=adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url="http://localhost:8081",
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    for bad in ["../etc", "demo/space", "demo space", "", "demo.space"]:
        with pytest.raises(BackupServiceError) as exc_info:
            service.create_mirror_backup(bad)
        assert exc_info.value.code == "INVALID_SPACE_ID"


def test_metadata_export_failure_raises(
    engine: Any,
    tmp_storage_path: Path,
) -> None:
    class FailingNotesAdapter(StubBackupGitLabAdapter):
        def list_notes(self, space_id: str, mr_iid: int) -> list[dict[str, Any]]:
            raise BackupGitLabAdapterError("notes unreachable")

    adapter = FailingNotesAdapter(
        state={
            ("branch", "demo-space", "main"): {"name": "main", "commit": {"id": "a" * 40}},
            ("mrs", "demo-space"): [{"iid": 1, "title": "MR"}],
        }
    )
    service = BackupService(
        adapter=adapter,
        engine=engine,
        storage_path=str(tmp_storage_path / "backups"),
        gitlab_url="http://localhost:8081",
        gitlab_token="",
        project_path_prefix="",
        kb_ops_schema=None,
    )

    with pytest.raises((BackupGitLabAdapterError, BackupServiceError)):
        service._export_metadata("demo-space")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
