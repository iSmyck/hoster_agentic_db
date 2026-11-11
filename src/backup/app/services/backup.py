"""Backup service: git mirror, metadata export, kb_ops export, package assembly."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, quote_plus

from sqlalchemy import Engine, create_engine, text

from backup.app.adapters.gitlab import BackupGitLabAdapter, BackupGitLabAdapterError
from backup.app.adapters.object_store import ObjectStoreAdapter, ObjectStoreAdapterError
from backup.app.core.config import settings
from backup.app.models.backup import (
    AssetsManifest,
    BackupManifest,
    BackupPackage,
    BackupStatus,
    FileHash,
    KbOpsExport,
    MetadataExport,
    NoteSummary,
    ObjectStoreEntry,
    ObjectStoreExport,
    PostgresExport,
)
from backup.app.services.object_store import ObjectStoreService, ObjectStoreServiceError
from backup.app.services.postgres_backup import PostgresBackupService, PostgresBackupServiceError

logger = logging.getLogger(__name__)


class BackupServiceError(Exception):
    """Raised when a backup operation fails."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


_SPACE_ID_RE = re.compile(r"^[a-zA-Z0-9_/-]+$")


def _sanitize_space_id(space_id: str) -> str:
    """Return a filesystem-safe space_id or raise BackupServiceError.

    Allows GitLab-style nested paths (``corp-kb/sales``) while rejecting
    path-traversal sequences and ambiguous forms.
    """
    if not space_id or not _SPACE_ID_RE.fullmatch(space_id):
        raise BackupServiceError(
            "INVALID_SPACE_ID",
            "space_id must contain only alphanumeric, hyphen, underscore, or slash characters",
        )
    if space_id.startswith("/") or space_id.endswith("/") or "//" in space_id:
        raise BackupServiceError(
            "INVALID_SPACE_ID",
            "space_id must not start/end with slash or contain empty segments",
        )
    for segment in space_id.split("/"):
        if segment in {".", ".."}:
            raise BackupServiceError(
                "INVALID_SPACE_ID",
                "space_id must not contain '.' or '..' segments",
            )
    return space_id


class BackupService:
    """Orchestrate per-Space immutable backup packages."""

    def __init__(
        self,
        adapter: BackupGitLabAdapter,
        engine: Engine | None = None,
        storage_path: str | None = None,
        gitlab_url: str | None = None,
        gitlab_token: str | None = None,
        project_path_prefix: str | None = None,
        kb_ops_schema: str | None = None,
        object_store_adapter: ObjectStoreAdapter | None = None,
        postgres_backup_service: PostgresBackupService | None = None,
    ) -> None:
        self.adapter = adapter
        self.engine = engine or create_engine(settings.BACKUP_DATABASE_URL)
        self.storage_path = Path(storage_path or settings.BACKUP_STORAGE_PATH)
        self.gitlab_url = gitlab_url or settings.BACKUP_GITLAB_URL
        self.gitlab_token = gitlab_token or settings.BACKUP_GITLAB_TOKEN
        self.project_path_prefix = (
            project_path_prefix
            if project_path_prefix is not None
            else settings.BACKUP_GITLAB_PROJECT_PATH_PREFIX
        )
        self.kb_ops_schema = (
            kb_ops_schema if kb_ops_schema is not None else settings.BACKUP_KB_OPS_SCHEMA
        )
        self.object_store_service = (
            ObjectStoreService(object_store_adapter) if object_store_adapter else None
        )
        self.postgres_backup_service = postgres_backup_service

    def _table(self, name: str) -> str:
        if self.kb_ops_schema:
            return f"{self.kb_ops_schema}.{name}"
        return name

    def _backup_id(self, space_id: str, head_sha: str) -> str:
        """Idempotency key: deterministic per space_id + HEAD SHA.

        Spec acceptance criterion: repeated request for the same space_id and
        HEAD returns the existing package_id.
        """
        payload = (space_id + head_sha).encode()
        return hashlib.sha256(payload).hexdigest()

    def _package_path(self, space_id: str, backup_id: str) -> Path:
        return self.storage_path / space_id / backup_id

    def _mirror_url(self, space_id: str) -> str:
        project_path = f"{self.project_path_prefix}{space_id}"
        base = self.gitlab_url.rstrip("/")
        if self.gitlab_token:
            quoted_token = quote(self.gitlab_token, safe="")
            return f"{base.replace('://', f'://oauth2:{quoted_token}@', 1)}/{project_path}.git"
        return f"{base}/{project_path}.git"

    def create_mirror_backup(self, space_id: str) -> BackupPackage:
        """Create a per-Space backup package containing a git mirror + metadata."""
        return self._create_backup(space_id, include_postgres=False, include_object_store=False)

    def create_full_backup(self, space_id: str) -> BackupPackage:
        """Create a per-Space backup package with git, metadata, PostgreSQL and object store."""
        return self._create_backup(space_id, include_postgres=True, include_object_store=True)

    def _create_backup(
        self,
        space_id: str,
        include_postgres: bool,
        include_object_store: bool,
    ) -> BackupPackage:
        space_id = _sanitize_space_id(space_id)
        status_marker = BackupStatus.IN_PROGRESS
        head_sha = ""
        backup_id = ""
        package_path: Path | None = None

        try:
            # Resolve current HEAD via the adapter (or a synthetic value for stubs).
            head_sha = self._resolve_head(space_id)
            backup_id = self._backup_id(space_id, head_sha)
            hour_bucket = datetime.now(UTC).strftime("%Y%m%d%H")
            package_path = self._package_path(space_id, backup_id)

            if package_path.exists() and (package_path / "manifest.json").exists():
                return self._load_existing_package(space_id, backup_id, package_path)

            try:
                package_path.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                if (package_path / "manifest.json").exists():
                    return self._load_existing_package(space_id, backup_id, package_path)
                raise BackupServiceError(
                    "BACKUP_IN_PROGRESS",
                    f"backup {backup_id} for {space_id} is already in progress",
                )

            status_path = package_path.with_suffix(".status.json")
            self._write_status(status_path, status_marker, backup_id, space_id)

            mirror_dir = package_path / "mirror.git"
            self._clone_mirror(space_id, mirror_dir)

            metadata = self._export_metadata(space_id)
            metadata_path = package_path / "metadata.json"
            self._write_json(metadata_path, metadata.model_dump(mode="json"))

            kb_ops = self._export_kb_ops(space_id)
            kb_ops_path = package_path / "kb_ops_export.json"
            self._write_json(kb_ops_path, kb_ops.model_dump(mode="json"))

            if include_postgres:
                self._backup_postgres(space_id, package_path)

            if include_object_store:
                self._backup_object_store(space_id, package_path)

            manifest = self._assemble_package(
                space_id,
                backup_id,
                head_sha,
                hour_bucket,
                package_path,
            )

            status_marker = BackupStatus.COMPLETE
            self._write_status(status_path, status_marker, backup_id, space_id, manifest=manifest)

            return BackupPackage(
                space_id=space_id,
                backup_id=backup_id,
                status=BackupStatus.COMPLETE,
                package_path=str(package_path),
                manifest=manifest,
            )
        except Exception as exc:
            logger.exception("backup failed for space_id=%s", space_id)
            if package_path is not None:
                try:
                    self._write_status(
                        package_path.with_suffix(".status.json"),
                        BackupStatus.FAILED,
                        backup_id or "unknown",
                        space_id,
                        error=str(exc),
                    )
                except Exception as write_exc:  # noqa: BLE001
                    logger.warning("failed to write failed status for %s: %s", space_id, write_exc)
            if isinstance(exc, BackupGitLabAdapterError):
                code = "GITLAB_ERROR"
            elif isinstance(exc, ObjectStoreAdapterError):
                code = "OBJECT_STORE_ERROR"
            elif isinstance(exc, (PostgresBackupServiceError, BackupServiceError)):
                code = exc.code
            else:
                code = "BACKUP_FAILED"
            raise BackupServiceError(code, str(exc)) from exc

    def _resolve_head(self, space_id: str) -> str:
        """Resolve HEAD SHA for the Space repository.

        Uses the adapter's default branch endpoint first, then falls back to an
        existing local mirror (idempotency path).
        """
        try:
            default_branch = self.adapter.get_default_branch(space_id)
            branch = self.adapter.get_branch(space_id, default_branch)
            head = str(branch.get("commit", {}).get("id", ""))
            if head and head != "0" * 40:
                return head
        except Exception as head_exc:  # noqa: BLE001
            logger.warning("failed to resolve HEAD from adapter for %s: %s", space_id, head_exc)

        # Fallback: derive from an existing mirror in the latest backup package.
        space_dir = self.storage_path / space_id
        if space_dir.exists():
            candidates = [
                d for d in space_dir.iterdir()
                if d.is_dir() and (d / "manifest.json").exists()
            ]
            for backup_dir in sorted(
                candidates,
                key=lambda p: _read_manifest_created_at(p),
                reverse=True,
            ):
                mirror_dir = backup_dir / "mirror.git"
                if mirror_dir.is_dir():
                    try:
                        result = subprocess.run(
                            ["git", "rev-parse", "HEAD"],
                            cwd=str(mirror_dir),
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=30,
                        )
                        head = result.stdout.strip()
                        if head:
                            return head
                    except Exception as mirror_exc:  # noqa: BLE001
                        logger.warning(
                            "failed to resolve HEAD from mirror for %s: %s",
                            space_id,
                            mirror_exc,
                        )
        return "0" * 40

    def _load_existing_package(
        self, space_id: str, backup_id: str, package_path: Path
    ) -> BackupPackage:
        manifest_path = package_path / "manifest.json"
        manifest = None
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = BackupManifest.model_validate(data)
        return BackupPackage(
            space_id=space_id,
            backup_id=backup_id,
            status=BackupStatus.COMPLETE,
            package_path=str(package_path),
            manifest=manifest,
        )

    def _clone_mirror(self, space_id: str, mirror_dir: Path) -> None:
        if mirror_dir.exists():
            shutil.rmtree(mirror_dir)
        url = self._mirror_url(space_id)
        try:
            result = subprocess.run(
                ["git", "clone", "--mirror", url, str(mirror_dir)],
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            raise BackupGitLabAdapterError(
                f"git clone --mirror timed out for {space_id}"
            ) from exc
        if result.returncode != 0:
            logger.error("git clone --mirror failed for %s", space_id)
            raise BackupGitLabAdapterError("git clone --mirror failed")

    def _export_metadata(self, space_id: str) -> MetadataExport:
        try:
            mrs = self.adapter.list_merge_requests(space_id)
        except BackupGitLabAdapterError:
            raise
        except Exception as exc:
            raise BackupGitLabAdapterError(str(exc)) from exc

        notes_by_mr: dict[str, list[NoteSummary]] = {}
        for mr in mrs:
            iid = mr.get("iid")
            if iid is None:
                continue
            raw_notes = self.adapter.list_notes(space_id, int(iid))
            notes_by_mr[str(iid)] = [
                NoteSummary(
                    id=note.get("id", 0),
                    body=note.get("body", ""),
                    author_id=note.get("author_id"),
                    created_at=note.get("created_at"),
                )
                for note in raw_notes
            ]

        raw_tags = self.adapter.list_tags(space_id)

        return MetadataExport(
            space_id=space_id,
            merge_requests=mrs,
            notes=notes_by_mr,
            tags=raw_tags,
        )

    def _export_kb_ops(self, space_id: str) -> KbOpsExport:
        proposals: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        source_sync_cursors: list[dict[str, Any]] = []
        cutovers: list[dict[str, Any]] = []
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT * FROM {self._table('proposals')} WHERE space_id = :space_id"),
                    {"space_id": space_id},
                )
                for row in result.mappings():
                    proposals.append(_serialize_row(row))

                result = conn.execute(
                    text(
                        f"SELECT * FROM {self._table('decisions')} WHERE proposal_id IN ("
                        f"SELECT id FROM {self._table('proposals')} WHERE space_id = :space_id)"
                    ),
                    {"space_id": space_id},
                )
                for row in result.mappings():
                    decisions.append(_serialize_row(row))

                result = conn.execute(
                    text(
                        f"SELECT * FROM {self._table('source_sync_cursors')} WHERE space_id = :space_id"
                    ),
                    {"space_id": space_id},
                )
                for row in result.mappings():
                    source_sync_cursors.append(_serialize_row(row))

                result = conn.execute(
                    text(f"SELECT * FROM {self._table('cutovers')} WHERE space_id = :space_id"),
                    {"space_id": space_id},
                )
                for row in result.mappings():
                    cutovers.append(_serialize_row(row))
        except Exception as exc:
            raise BackupServiceError("KB_OPS_ERROR", f"kb_ops export failed: {exc}") from exc

        return KbOpsExport(
            space_id=space_id,
            proposals=proposals,
            decisions=decisions,
            source_sync_cursors=source_sync_cursors,
            cutovers=cutovers,
        )

    def _backup_postgres(self, space_id: str, package_path: Path) -> PostgresExport:
        if self.postgres_backup_service is None:
            raise BackupServiceError(
                "POSTGRES_NOT_CONFIGURED",
                "postgres backup service not configured",
            )
        export_dir = package_path / "postgres_export"
        try:
            export = self.postgres_backup_service.dump_schemas(space_id, export_dir)
        except PostgresBackupServiceError as exc:
            raise BackupServiceError(exc.code, exc.message) from exc
        return export

    def _backup_object_store(self, space_id: str, package_path: Path) -> ObjectStoreExport:
        if self.object_store_service is None:
            raise BackupServiceError(
                "OBJECT_STORE_NOT_CONFIGURED",
                "object store service not configured",
            )
        export_dir = package_path / "object_store_export"
        export_dir.mkdir(parents=True, exist_ok=True)

        try:
            current_objects = self.object_store_service.build_assets_manifest(space_id)
        except (ObjectStoreServiceError, ObjectStoreAdapterError) as exc:
            raise BackupServiceError("OBJECT_STORE_ERROR", str(exc)) from exc

        all_versions: list[ObjectStoreEntry] = []
        for current in current_objects.objects:
            try:
                versions = self.object_store_service.list_object_versions(
                    space_id, current.object_id
                )
            except ObjectStoreServiceError as exc:
                raise BackupServiceError("OBJECT_STORE_ERROR", str(exc)) from exc
            if not versions:
                versions = [current]
            for entry in versions:
                try:
                    content = self.object_store_service.get_object_content(
                        space_id, entry.object_id, entry.version
                    )
                except ObjectStoreServiceError as exc:
                    raise BackupServiceError("OBJECT_STORE_ERROR", str(exc)) from exc
                actual_sha = hashlib.sha256(content).hexdigest()
                if actual_sha != entry.sha256:
                    raise BackupServiceError(
                        "HASH_MISMATCH",
                        f"object store hash mismatch for {entry.object_id}@{entry.version}",
                    )
                safe_name = _safe_object_filename(entry.object_id, entry.version)
                dest = export_dir / safe_name
                if dest.exists():
                    raise BackupServiceError(
                        "DUPLICATE_OBJECT_VERSION",
                        f"duplicate object version destination: {dest.name}",
                    )
                dest.write_bytes(content)
                all_versions.append(
                    ObjectStoreEntry(
                        object_id=entry.object_id,
                        version=entry.version,
                        sha256=entry.sha256,
                        size=entry.size,
                        media_type=entry.media_type,
                        source_ref=entry.source_ref,
                    )
                )

        assets_manifest = AssetsManifest(space_id=space_id, objects=all_versions)
        assets_path = package_path / "assets_manifest.json"
        self._write_json(assets_path, assets_manifest.model_dump(mode="json"))

        return ObjectStoreExport(space_id=space_id, objects=all_versions)

    def _assemble_package(
        self,
        space_id: str,
        backup_id: str,
        head_sha: str,
        hour_bucket: str,
        package_path: Path,
    ) -> BackupManifest:
        manifest = self._compute_manifest(space_id, backup_id, head_sha, hour_bucket, package_path)
        manifest_path = package_path / "manifest.json"
        self._write_json(manifest_path, manifest.model_dump(mode="json"))

        # Verify hashes immediately after writing.
        for file_hash in manifest.files:
            file_path = package_path / file_hash.path
            actual = _sha256_file(file_path)
            if actual != file_hash.sha256:
                raise BackupServiceError(
                    "HASH_MISMATCH",
                    f"hash mismatch for {file_hash.path}: expected {file_hash.sha256}, got {actual}",
                )

        return manifest

    def _compute_manifest(
        self,
        space_id: str,
        backup_id: str,
        head_sha: str,
        hour_bucket: str,
        package_path: Path,
    ) -> BackupManifest:
        files: list[FileHash] = []
        for path in sorted(
            [p.relative_to(package_path) for p in package_path.rglob("*") if p.is_file()]
        ):
            if path.name == "manifest.json" or path.name.startswith("."):
                continue
            files.append(FileHash(path=str(path), sha256=_sha256_file(package_path / path)))
        return BackupManifest(
            space_id=space_id,
            backup_id=backup_id,
            head_sha=head_sha,
            hour_bucket=hour_bucket,
            files=files,
        )

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_status(
        self,
        path: Path,
        status: BackupStatus,
        backup_id: str,
        space_id: str,
        manifest: BackupManifest | None = None,
        error: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "space_id": space_id,
            "backup_id": backup_id,
            "status": status.value,
        }
        if manifest:
            payload["manifest"] = manifest.model_dump(mode="json")
        if error:
            payload["error"] = error
        self._write_json(path, payload)

    def get_latest(self, space_id: str) -> BackupPackage | None:
        space_id = _sanitize_space_id(space_id)
        space_dir = self.storage_path / space_id
        if not space_dir.exists():
            return None
        candidates = [
            d for d in space_dir.iterdir() if d.is_dir() and (d / "manifest.json").exists()
        ]
        if not candidates:
            return None
        latest = max(
            candidates,
            key=_read_manifest_created_at,
        )
        manifest = BackupManifest.model_validate(
            json.loads((latest / "manifest.json").read_text(encoding="utf-8"))
        )
        return BackupPackage(
            space_id=space_id,
            backup_id=latest.name,
            status=BackupStatus.COMPLETE,
            package_path=str(latest),
            manifest=manifest,
        )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_object_filename(object_id: str, version: str) -> str:
    """Return a unique, filesystem-safe filename for an object version.

    Uses percent-encoding so distinct object/version strings cannot collide.
    """
    encoded_object_id = quote_plus(object_id, safe="")
    encoded_version = quote_plus(version, safe="")
    return f"{encoded_object_id}_{encoded_version}.bin"


def _read_manifest_created_at(package_path: Path) -> datetime:
    """Return manifest.created_at for a package directory, or epoch if unreadable."""
    manifest_path = package_path / "manifest.json"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        created_at = data.get("created_at")
        if created_at:
            return datetime.fromisoformat(created_at)
    except Exception as exc:  # noqa: BLE001
        logger.debug("unable to read manifest created_at for %s: %s", package_path, exc)
    return datetime.fromtimestamp(0, tz=UTC)


def _serialize_row(row: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy row mapping into JSON-serializable dict."""
    result: dict[str, Any] = {}
    for key in row:
        value = row[key]
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        else:
            try:
                json.dumps(value)
            except TypeError:
                value = str(value)
        result[key] = value
    return result
