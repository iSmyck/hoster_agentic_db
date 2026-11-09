"""End-to-end MVP tests for the Ingestion adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ingestion.app.adapters.go_client import GOClientError, HttpGOClient, StubGOClient
from ingestion.app.adapters.source_connector import GitFolderConnector, StubSourceConnector
from ingestion.app.services import dry_run, importer, source_registry


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestSourceRegistry:
    def test_create_source(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        resp = client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
                "ownership_mode": "curated",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["space_id"] == space_id
        assert body["source_id"] == source_id
        assert body["source_type"] == "test_stub"
        assert body["ownership_mode"] == "curated"
        assert "id" in body

    def test_get_source(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        resp = client.get(f"/api/kb/v1/sources/{source_id}?space_id={space_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["source_id"] == source_id

    def test_create_source_duplicate_returns_409(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        payload = {
            "space_id": space_id,
            "source_id": source_id,
            "source_type": "test_stub",
            "config": clean_source_config,
        }
        assert client.post("/api/kb/v1/sources", json=payload).status_code == 201
        resp = client.post("/api/kb/v1/sources", json=payload)
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "ALREADY_EXISTS"

    def test_create_source_unknown_type_returns_422(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
    ) -> None:
        resp = client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "unknown_connector",
                "config": {},
            },
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_SOURCE_TYPE"


class TestCursorManagement:
    def test_update_cursor(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        resp = client.post(
            f"/api/kb/v1/sources/{source_id}/cursor?space_id={space_id}",
            json={"cursor_value": "cursor-v2", "cursor_hash": "deadbeef"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["cursor_value"] == "cursor-v2"
        assert body["cursor_hash"] == "deadbeef"


class TestDryRun:
    def test_dry_run_ready(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        resp = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "ready"
        assert body["blockers"] == []
        assert body["manifest_data"]["scanned_count"] == 2
        assert body["manifest_data"]["entries"][0]["path"] == "README.md"

    def test_dry_run_blocked(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        blocked_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": blocked_source_config,
            },
        )
        resp = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "blocked"
        blocker_types = {b["type"] for b in body["blockers"]}
        assert blocker_types == {"pii", "media", "security", "unsupported_format"}

    def test_dry_run_idempotent(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        r1 = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={"idempotency_key": "same-key"},
        )
        r2 = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={"idempotency_key": "same-key"},
        )
        assert r1.json()["id"] == r2.json()["id"]

    def test_dry_run_default_key_is_deterministic(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        r1 = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        r2 = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        assert r1.status_code == 201, r1.text
        assert r2.status_code == 201, r2.text
        assert r1.json()["id"] == r2.json()["id"]
        assert r1.json()["idempotency_key"] == r2.json()["idempotency_key"]

    def test_dry_run_idempotency_key_reused_on_changed_config(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        r1 = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={"idempotency_key": "reused-key"},
        )
        assert r1.status_code == 201, r1.text

        # Mutate the source config so the manifest changes.
        client.patch(
            f"/api/kb/v1/sources/{source_id}?space_id={space_id}",
            json={"config": {**clean_source_config, "entries": []}},
        )

        r2 = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={"idempotency_key": "reused-key"},
        )
        assert r2.status_code == 409
        assert r2.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"


class TestGitFolderConnector:
    def test_git_folder_connector_scans_files(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide\n")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("[core]\n")

        connector = GitFolderConnector(
            {"path": str(tmp_path), "include_patterns": ["*.md", "docs/*.md"]}
        )
        result = connector.scan()
        paths = {e.path for e in result.entries}
        assert paths == {"README.md", "docs/guide.md"}

    def test_git_folder_connector_exclude_patterns(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / "draft").mkdir()
        (tmp_path / "draft" / "secret.md").write_text("# Secret\n")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide\n")

        connector = GitFolderConnector(
            {
                "path": str(tmp_path),
                "include_patterns": ["*.md", "docs/*.md", "draft/*.md"],
                "exclude_patterns": ["draft/**"],
            }
        )
        result = connector.scan()
        paths = {e.path for e in result.entries}
        assert paths == {"README.md", "docs/guide.md"}

    def test_git_folder_connector_nested_glob_pattern(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Title\n")
        (tmp_path / "deep").mkdir()
        (tmp_path / "deep" / "a").mkdir()
        (tmp_path / "deep" / "a" / "note.md").write_text("# Note\n")
        (tmp_path / "deep" / "a" / "skip.txt").write_text("skip\n")

        connector = GitFolderConnector(
            {"path": str(tmp_path), "include_patterns": ["**/*.md"]}
        )
        result = connector.scan()
        paths = {e.path for e in result.entries}
        assert paths == {"README.md", "deep/a/note.md"}

    def test_git_folder_connector_skips_symlinks(self, tmp_path: Path) -> None:
        real_file = tmp_path / "README.md"
        real_file.write_text("# Title\n")
        symlink = tmp_path / "link.md"
        symlink.symlink_to(real_file)

        connector = GitFolderConnector({"path": str(tmp_path)})
        result = connector.scan()
        paths = {e.path for e in result.entries}
        assert paths == {"README.md"}

    def test_git_folder_connector_handles_os_errors_gracefully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "README.md").write_text("# Title\n")

        def _raising_read_bytes(*args: Any, **kwargs: Any) -> None:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "read_bytes", _raising_read_bytes)

        connector = GitFolderConnector({"path": str(tmp_path)})
        result = connector.scan()
        assert result.entries == []


class TestStubConnector:
    def test_stub_connector(self) -> None:
        connector = StubSourceConnector(
            {"entries": [{"path": "a.md", "content": "hello", "media_type": "text/markdown"}]}
        )
        result = connector.scan()
        assert len(result.entries) == 1
        assert result.entries[0].path == "a.md"


class TestHttpGOClient:
    def test_get_current_head_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return httpx.Response(200, json={"head_sha": "abc" * 20})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport, base_url="http://go.test")
        go = HttpGOClient("http://go.test", client=client)

        head = go.get_current_head("space-1")
        assert head == "abc" * 20

    def test_get_current_head_raises_on_http_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport, base_url="http://go.test")
        go = HttpGOClient("http://go.test", client=client)

        with pytest.raises(GOClientError):
            go.get_current_head("space-1")

    def test_get_current_head_raises_when_field_missing(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"other": "value"})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport, base_url="http://go.test")
        go = HttpGOClient("http://go.test", client=client)

        with pytest.raises(GOClientError) as exc_info:
            go.get_current_head("space-1")
        assert "head_sha" in str(exc_info.value)

    def test_submit_proposal_success(self) -> None:
        received: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            received.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "proposal-1"})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport, base_url="http://go.test")
        go = HttpGOClient("http://go.test", client=client)

        result = go.submit_proposal({"space_id": "space-1"})
        assert result["id"] == "proposal-1"
        assert received[0]["space_id"] == "space-1"

    def test_submit_proposal_raises_when_id_missing(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"status": "ok"})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport, base_url="http://go.test")
        go = HttpGOClient("http://go.test", client=client)

        with pytest.raises(GOClientError) as exc_info:
            go.submit_proposal({"space_id": "space-1"})
        assert "id" in str(exc_info.value)


class TestImportAuthorization:
    def test_authorize_and_submit(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
        go_client: StubGOClient,
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        dry_resp = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        dry_run_id = dry_resp.json()["id"]

        auth_resp = client.post(
            f"/api/kb/v1/dry-runs/{dry_run_id}/authorize",
            json={"authorized_by": "owner-1"},
        )
        assert auth_resp.status_code == 201, auth_resp.text
        package_id = auth_resp.json()["id"]
        assert auth_resp.json()["status"] == "authorized"
        assert auth_resp.json()["authorized_by"] == "owner-1"

        submit_resp = client.post(
            f"/api/kb/v1/import-packages/{package_id}/submit?space_id={space_id}",
            json={},
        )
        assert submit_resp.status_code == 200, submit_resp.text
        body = submit_resp.json()
        assert body["status"] == "submitted"
        assert body["submitted_proposal_id"] == "11111111-1111-1111-1111-111111111111"

        assert len(go_client.calls) == 1
        proposal = go_client.calls[0]["submit_proposal"]
        assert proposal["space_id"] == space_id
        assert proposal["base_sha"] == "1" * 40
        assert proposal["proposal_data"]["origin"] == "ingestion"

    def test_cannot_authorize_blocked_dry_run(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        blocked_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": blocked_source_config,
            },
        )
        dry_resp = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        dry_run_id = dry_resp.json()["id"]
        auth_resp = client.post(
            f"/api/kb/v1/dry-runs/{dry_run_id}/authorize",
            json={"authorized_by": "owner-1"},
        )
        assert auth_resp.status_code == 403
        assert auth_resp.json()["detail"]["code"] == "NOT_AUTHORIZED"

    def test_cannot_submit_unauthorized_package(
        self,
        client: TestClient,
        db_session: Session,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        dry_resp = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        dry_run_id = dry_resp.json()["id"]

        # Sneakily create a package directly without authorization via DB.
        import uuid as uuid_module

        from ingestion.app.models.ingestion import ImportPackage as ImportPackageModel

        package = ImportPackageModel(
            dry_run_id=uuid_module.UUID(dry_run_id),
            status="pending",
        )
        db_session.add(package)
        db_session.flush()
        package_id = package.id

        resp = client.post(
            f"/api/kb/v1/import-packages/{package_id}/submit?space_id={space_id}",
            json={},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "INVALID_STATE"

    def test_import_package_rejects_different_authorized_by(
        self,
        client: TestClient,
        db_session: Session,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        dry_resp = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        dry_run_id = dry_resp.json()["id"]

        # Create a pending package with an owner via DB to simulate a race.
        import uuid as uuid_module

        from ingestion.app.models.ingestion import ImportPackage as ImportPackageModel

        package = ImportPackageModel(
            dry_run_id=uuid_module.UUID(dry_run_id),
            status="pending",
            authorized_by="owner-a",
        )
        db_session.add(package)
        db_session.flush()

        resp = client.post(
            f"/api/kb/v1/dry-runs/{dry_run_id}/authorize",
            json={"authorized_by": "owner-b"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "AUTHORIZATION_CONFLICT"

    def test_target_branch_from_config(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
        go_client: StubGOClient,
    ) -> None:
        config = {**clean_source_config, "target_branch": "develop"}
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": config,
            },
        )
        dry_resp = client.post(
            f"/api/kb/v1/sources/{source_id}/dry-run?space_id={space_id}",
            json={},
        )
        dry_run_id = dry_resp.json()["id"]

        auth_resp = client.post(
            f"/api/kb/v1/dry-runs/{dry_run_id}/authorize",
            json={"authorized_by": "owner-1"},
        )
        package_id = auth_resp.json()["id"]

        client.post(
            f"/api/kb/v1/import-packages/{package_id}/submit?space_id={space_id}",
            json={},
        )

        proposal = go_client.calls[0]["submit_proposal"]
        assert proposal["target_branch"] == "develop"


class TestThreeWayConflict:
    def test_no_conflict_when_states_match(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        client.post(
            f"/api/kb/v1/sources/{source_id}/cursor?space_id={space_id}",
            json={"cursor_value": "cursor-v1", "cursor_hash": "abc"},
        )
        resp = client.post(
            f"/api/kb/v1/sources/{source_id}/conflict-check?space_id={space_id}",
            json={
                "source_cursor": "cursor-v1",
                "last_merged_cursor": None,
                "go_head": "1" * 40,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["conflict"] is False
        assert body["mismatches"] == []

    def test_conflict_when_cursor_mismatches(
        self,
        client: TestClient,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        client.post(
            "/api/kb/v1/sources",
            json={
                "space_id": space_id,
                "source_id": source_id,
                "source_type": "test_stub",
                "config": clean_source_config,
            },
        )
        client.post(
            f"/api/kb/v1/sources/{source_id}/cursor?space_id={space_id}",
            json={"cursor_value": "cursor-v2", "cursor_hash": "abc"},
        )
        resp = client.post(
            f"/api/kb/v1/sources/{source_id}/conflict-check?space_id={space_id}",
            json={
                "source_cursor": "cursor-v1",
                "last_merged_cursor": None,
                "go_head": "1" * 40,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["conflict"] is True
        assert "source_cursor" in body["mismatches"]


class TestServiceLayer:
    def test_dry_run_service_no_canonical_writes(
        self,
        db_session: Session,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        source_registry.create_source(
            db_session,
            space_id,
            source_id,
            "test_stub",
            clean_source_config,
        )
        from ingestion.app.adapters.source_connector import StubSourceConnector

        connector = StubSourceConnector(clean_source_config)
        manifest = dry_run.run_dry_run(
            db_session,
            connector,
            space_id,
            source_id,
            "key-1",
        )
        assert manifest.status == "ready"
        assert len(manifest.manifest_data["entries"]) == 2
        # No GO proposal was created, no queue events emitted.
        assert manifest.blockers == []

    def test_importer_updates_last_merged_cursor(
        self,
        db_session: Session,
        space_id: str,
        source_id: str,
        clean_source_config: dict[str, Any],
    ) -> None:
        source = source_registry.create_source(
            db_session,
            space_id,
            source_id,
            "test_stub",
            clean_source_config,
        )
        cursor = source_registry.update_cursor(
            db_session,
            source,
            "cursor-v1",
            "hash-v1",
        )

        from ingestion.app.adapters.source_connector import StubSourceConnector

        connector = StubSourceConnector(clean_source_config)
        manifest = dry_run.run_dry_run(
            db_session,
            connector,
            space_id,
            source_id,
            "key-2",
        )
        package = importer.create_import_package(
            db_session,
            manifest.id,
            "owner-1",
        )
        go_client = StubGOClient(state={"head_sha": "2" * 40})
        importer.submit_source_proposal(
            db_session,
            go_client,
            space_id,
            package.id,
        )
        assert cursor.last_merged_cursor == "cursor-v1"
