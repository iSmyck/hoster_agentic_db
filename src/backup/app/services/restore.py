"""Restore service: restore a Space from a backup package into a clean target."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from backup.app.adapters.gitlab import BackupGitLabAdapter, BackupGitLabAdapterError
from backup.app.adapters.object_store import ObjectStoreAdapter, ObjectStoreAdapterError
from backup.app.core.config import settings
from backup.app.models.backup import AssetsManifest, BackupManifest
from backup.app.models.restore import (
    IntegrityReport,
    RestoreRequest,
    RestoreResult,
    RestoreStatus,
    RestoreStep,
)
from backup.app.services.closure import ClosureVerifier
from backup.app.services.integrity import IntegrityChecker, IntegrityCheckerError
from backup.app.services.object_store import ObjectStoreService
from backup.app.services.postgres_backup import PostgresBackupService, PostgresBackupServiceError

logger = logging.getLogger(__name__)


class RestoreServiceError(Exception):
    """Raised when a restore operation fails."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


_SPACE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _sanitize_space_id(space_id: str) -> str:
    """Return a filesystem-safe space_id or raise RestoreServiceError."""
    if not space_id or not _SPACE_ID_RE.fullmatch(space_id):
        raise RestoreServiceError(
            "INVALID_SPACE_ID",
            "space_id must contain only alphanumeric, hyphen, or underscore characters",
        )
    return space_id


class RestoreService:
    """Orchestrate restore of a backup package into a clean target environment."""

    def __init__(
        self,
        adapter: BackupGitLabAdapter,
        storage_path: str | None = None,
        gitlab_url: str | None = None,
        gitlab_token: str | None = None,
        project_path_prefix: str | None = None,
        object_store_adapter: ObjectStoreAdapter | None = None,
        postgres_backup_service: PostgresBackupService | None = None,
    ) -> None:
        self.adapter = adapter
        self.storage_path = Path(storage_path or settings.BACKUP_STORAGE_PATH)
        # Restore targets use separate credentials by default; callers may still
        # override them explicitly for tests.
        self.gitlab_url = gitlab_url or settings.BACKUP_RESTORE_GITLAB_URL
        self.gitlab_token = gitlab_token or settings.BACKUP_RESTORE_GITLAB_TOKEN
        self.project_path_prefix = (
            project_path_prefix
            if project_path_prefix is not None
            else settings.BACKUP_RESTORE_GITLAB_PROJECT_PATH_PREFIX
        )
        self.object_store_service = (
            ObjectStoreService(object_store_adapter) if object_store_adapter else None
        )
        self.postgres_backup_service = postgres_backup_service
        self.integrity_checker = IntegrityChecker()
        self.closure_verifier = ClosureVerifier(
            adapter,
            object_store_adapter,
            postgres_backup_service,
        )

    def restore(
        self,
        space_id: str,
        backup_id: str,
        request: RestoreRequest | None = None,
    ) -> RestoreResult:
        """Restore a backup package into the target environment.

        Steps:
        1. Load the package and verify its integrity (read-only sidecar).
        2. Refuse to restore if the target Space exists and ``force`` is False.
        3. Push the Git mirror to the target repository.
        4. Restore PostgreSQL operational schemas from SQL files.
        5. Restore object-store objects from the package export.
        6. Run closure verification against the restored target.
        """
        space_id = _sanitize_space_id(space_id)
        request = request or RestoreRequest()
        target_space_id = _sanitize_space_id(request.target_space_id or space_id)
        force = request.force

        resolved_backup_id = backup_id or request.backup_id or ""
        if not resolved_backup_id:
            resolved_backup_id = self._latest_backup_id(space_id)
            if not resolved_backup_id:
                raise RestoreServiceError(
                    "PACKAGE_NOT_FOUND",
                    f"no backup package found for space: {space_id}",
                )

        package_path = self._package_path(space_id, resolved_backup_id)
        if not package_path.is_dir() or not (package_path / "manifest.json").exists():
            raise RestoreServiceError(
                "PACKAGE_NOT_FOUND",
                f"backup package not found: {space_id}/{resolved_backup_id}",
            )

        self._load_manifest(package_path)
        integrity_report = self._run_integrity_check(package_path)
        if not integrity_report.verified:
            return RestoreResult(
                space_id=space_id,
                target_space_id=target_space_id,
                backup_id=resolved_backup_id,
                status=RestoreStatus.FAILED,
                package_path=str(package_path),
                restored_steps=[RestoreStep.INTEGRITY_CHECK],
                integrity_report=integrity_report,
                error="integrity check failed; restore aborted",
            )

        # Refuse to overwrite an existing target unless forced.
        if not force and self._target_exists(target_space_id):
            raise RestoreServiceError(
                "TARGET_EXISTS",
                f"target Space already exists: {target_space_id}",
            )

        result = RestoreResult(
            space_id=space_id,
            target_space_id=target_space_id,
            backup_id=resolved_backup_id,
            status=RestoreStatus.IN_PROGRESS,
            package_path=str(package_path),
            restored_steps=[RestoreStep.INTEGRITY_CHECK],
            integrity_report=integrity_report,
        )
        self._write_restore_status(package_path, result)

        try:
            self._restore_git_mirror(package_path, target_space_id)
            result.restored_steps.append(RestoreStep.GIT_MIRROR)

            self._restore_postgres(package_path)
            result.restored_steps.append(RestoreStep.POSTGRES)

            self._restore_object_store(package_path, target_space_id)
            result.restored_steps.append(RestoreStep.OBJECT_STORE)

            closure_report = self.closure_verifier.verify(package_path, target_space_id)
            result.closure_report = closure_report
            result.restored_steps.append(RestoreStep.CLOSURE_VERIFY)
            if closure_report.consistent:
                result.status = RestoreStatus.COMPLETE
            else:
                result.status = RestoreStatus.FAILED
                result.error = "closure verification failed"
        except RestoreServiceError:
            result.status = RestoreStatus.FAILED
            self._write_restore_status(package_path, result)
            raise
        except Exception as exc:
            result.status = RestoreStatus.FAILED
            result.error = str(exc)
            self._write_restore_status(package_path, result)
            raise RestoreServiceError("RESTORE_FAILED", str(exc)) from exc

        self._write_restore_status(package_path, result)
        return result

    def verify_integrity(
        self,
        space_id: str,
        backup_id: str,
    ) -> IntegrityReport:
        """Run a read-only integrity check on a backup package."""
        space_id = _sanitize_space_id(space_id)
        package_path = self._package_path(space_id, backup_id)
        return self._run_integrity_check(package_path)

    def _package_path(self, space_id: str, backup_id: str) -> Path:
        return self.storage_path / space_id / backup_id

    def _latest_backup_id(self, space_id: str) -> str | None:
        space_dir = self.storage_path / space_id
        if not space_dir.exists():
            return None
        candidates = [
            d for d in space_dir.iterdir() if d.is_dir() and (d / "manifest.json").exists()
        ]
        if not candidates:
            return None
        latest = max(candidates, key=lambda p: (p / "manifest.json").stat().st_mtime)
        return latest.name

    def _load_manifest(self, package_path: Path) -> BackupManifest:
        manifest_path = package_path / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return BackupManifest.model_validate(data)

    def _run_integrity_check(self, package_path: Path) -> IntegrityReport:
        try:
            return self.integrity_checker.verify(package_path)
        except IntegrityCheckerError as exc:
            raise RestoreServiceError(exc.code, exc.message) from exc

    def _target_exists(self, target_space_id: str) -> bool:
        """Return True if the target Space already exists in GitLab."""
        try:
            branch = self.adapter.get_branch(target_space_id, "main")
            head = str(branch.get("commit", {}).get("id", ""))
            return bool(head and head != "0" * 40)
        except BackupGitLabAdapterError as exc:
            if exc.status_code == 404:
                return False
            logger.warning("target existence check failed for %s: %s", target_space_id, exc)
            return False

    def _restore_git_mirror(self, package_path: Path, target_space_id: str) -> None:
        mirror_dir = package_path / "mirror.git"
        if not mirror_dir.is_dir():
            raise RestoreServiceError("MIRROR_MISSING", "mirror.git missing from package")
        try:
            self.adapter.push_mirror(target_space_id, str(mirror_dir))
        except BackupGitLabAdapterError as exc:
            raise RestoreServiceError("GIT_RESTORE_ERROR", str(exc)) from exc

    def _restore_postgres(self, package_path: Path) -> None:
        export_dir = package_path / "postgres_export"
        if not export_dir.is_dir():
            logger.info("no postgres_export in package; skipping PostgreSQL restore")
            return
        if self.postgres_backup_service is None:
            raise RestoreServiceError(
                "POSTGRES_NOT_CONFIGURED",
                "postgres backup service not configured",
            )
        try:
            self.postgres_backup_service.restore_schemas(export_dir)
        except PostgresBackupServiceError as exc:
            raise RestoreServiceError(exc.code, exc.message) from exc

    def _restore_object_store(self, package_path: Path, target_space_id: str) -> None:
        export_dir = package_path / "object_store_export"
        if not export_dir.is_dir():
            logger.info("no object_store_export in package; skipping object-store restore")
            return
        if self.object_store_service is None:
            raise RestoreServiceError(
                "OBJECT_STORE_NOT_CONFIGURED",
                "object store service not configured",
            )

        assets_path = package_path / "assets_manifest.json"
        if not assets_path.exists():
            raise RestoreServiceError(
                "ASSETS_MANIFEST_MISSING",
                "assets_manifest.json missing; cannot restore object store",
            )
        assets = AssetsManifest.model_validate(
            json.loads(assets_path.read_text(encoding="utf-8"))
        )

        for entry in assets.objects:
            safe_object_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", entry.object_id)
            safe_version = re.sub(r"[^a-zA-Z0-9_.-]", "_", entry.version)
            source = export_dir / f"{safe_object_id}_{safe_version}.bin"
            if not source.exists():
                raise RestoreServiceError(
                    "OBJECT_FILE_MISSING",
                    f"object export missing for {entry.object_id}@{entry.version}",
                )
            data = source.read_bytes()
            actual_sha = _sha256_bytes(data)
            if actual_sha != entry.sha256:
                raise RestoreServiceError(
                    "OBJECT_HASH_MISMATCH",
                    f"object export hash mismatch for {entry.object_id}@{entry.version}",
                )
            try:
                self.object_store_service.adapter.put_object(
                    space_id=target_space_id,
                    object_id=entry.object_id,
                    data=data,
                    version=entry.version,
                    media_type=entry.media_type,
                    source_ref=entry.source_ref,
                )
            except ObjectStoreAdapterError as exc:
                raise RestoreServiceError("OBJECT_STORE_ERROR", str(exc)) from exc

    def _write_restore_status(self, package_path: Path, result: RestoreResult) -> None:
        """Write a restore_status.json sidecar to the package directory.

        This implements the minimal managed-write freeze marker required by the
        MVP boundary: the sidecar records that a restore was required/in
        progress, without implementing a full distributed barrier.
        """
        try:
            sidecar_path = package_path / "restore_status.json"
            sidecar_path.write_text(
                json.dumps(
                    {
                        "space_id": result.space_id,
                        "target_space_id": result.target_space_id,
                        "backup_id": result.backup_id,
                        "status": result.status.value,
                        "restored_steps": [step.value for step in result.restored_steps],
                        "error": result.error,
                        "frozen": result.status
                        in (RestoreStatus.IN_PROGRESS, RestoreStatus.PENDING),
                        "restore_required": result.status == RestoreStatus.FAILED,
                        "restored_at": result.restored_at.isoformat(),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to write restore_status.json for %s: %s", package_path, exc)


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()
