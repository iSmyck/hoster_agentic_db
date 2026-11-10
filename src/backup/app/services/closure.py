"""Closure verifier: compare pre-restore manifest state with post-restore state."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from backup.app.adapters.gitlab import BackupGitLabAdapter, BackupGitLabAdapterError
from backup.app.adapters.object_store import ObjectStoreAdapter, ObjectStoreAdapterError
from backup.app.models.restore import ClosureMismatch, ClosureReport
from backup.app.services.postgres_backup import PostgresBackupService, PostgresBackupServiceError

logger = logging.getLogger(__name__)


class ClosureVerifierError(Exception):
    """Raised when closure verification cannot be performed."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ClosureVerifier:
    """Compare pre-restore manifests/hashes against the restored Space."""

    def __init__(
        self,
        gitlab_adapter: BackupGitLabAdapter,
        object_store_adapter: ObjectStoreAdapter | None = None,
        postgres_backup_service: PostgresBackupService | None = None,
    ) -> None:
        self.gitlab_adapter = gitlab_adapter
        self.object_store_adapter = object_store_adapter
        self.postgres_backup_service = postgres_backup_service

    def verify(
        self,
        package_path: Path | str,
        target_space_id: str,
    ) -> ClosureReport:
        """Verify that the restored target Space matches the backup package.

        Comparison is high-level: assets manifest object count/hashes, metadata
        tags count, and kb_ops decisions count. It does not compare full content
        byte-by-byte.
        """
        package_path = Path(package_path)
        if not package_path.is_dir():
            raise ClosureVerifierError(
                "PACKAGE_NOT_FOUND", f"package not found: {package_path}"
            )

        pre_state = _load_pre_state(package_path)
        mismatches: list[ClosureMismatch] = []

        # Git metadata: compare tag counts.
        try:
            post_tags = self.gitlab_adapter.list_tags(target_space_id)
            expected_tags = len(pre_state.get("metadata", {}).get("tags", []))
            actual_tags = len(post_tags)
            if expected_tags != actual_tags:
                mismatches.append(
                    ClosureMismatch(
                        scope="metadata",
                        key="tag_count",
                        expected=expected_tags,
                        actual=actual_tags,
                    )
                )
        except BackupGitLabAdapterError as exc:
            raise ClosureVerifierError(
                "GITLAB_ERROR", f"failed to list tags for {target_space_id}: {exc}"
            ) from exc

        # kb_ops: compare decision count when a PostgreSQL service is available.
        kb_ops = pre_state.get("kb_ops_export", {})
        expected_decisions = len(kb_ops.get("decisions", []))
        if expected_decisions and self.postgres_backup_service is not None:
            try:
                actual_decisions = self.postgres_backup_service.count_decisions(target_space_id)
                if expected_decisions != actual_decisions:
                    mismatches.append(
                        ClosureMismatch(
                            scope="kb_ops",
                            key="decision_count",
                            expected=expected_decisions,
                            actual=actual_decisions,
                        )
                    )
            except PostgresBackupServiceError as exc:
                mismatches.append(
                    ClosureMismatch(
                        scope="kb_ops",
                        key="decision_count_query",
                        expected="queryable",
                        actual=f"error: {exc}",
                    )
                )
        elif expected_decisions and self.postgres_backup_service is None:
            mismatches.append(
                ClosureMismatch(
                    scope="kb_ops",
                    key="postgres_service",
                    expected="configured",
                    actual="missing",
                )
            )

        # Object store: compare object count and hashes.
        expected_assets = pre_state.get("assets_manifest", {}).get("objects", [])
        if expected_assets and self.object_store_adapter is not None:
            try:
                post_objects = self.object_store_adapter.list_objects(target_space_id)
                actual_by_id = {obj.object_id: obj for obj in post_objects}
                for expected in expected_assets:
                    obj_id = expected.get("object_id")
                    actual = actual_by_id.get(obj_id)
                    if actual is None:
                        mismatches.append(
                            ClosureMismatch(
                                scope="object_store",
                                key=f"object:{obj_id}",
                                expected="present",
                                actual="missing",
                            )
                        )
                        continue
                    if actual.sha256 != expected.get("sha256"):
                        mismatches.append(
                            ClosureMismatch(
                                scope="object_store",
                                key=f"object:{obj_id}:sha256",
                                expected=expected.get("sha256"),
                                actual=actual.sha256,
                            )
                        )
                if len(post_objects) != len(expected_assets):
                    mismatches.append(
                        ClosureMismatch(
                            scope="object_store",
                            key="object_count",
                            expected=len(expected_assets),
                            actual=len(post_objects),
                        )
                    )
            except ObjectStoreAdapterError as exc:
                raise ClosureVerifierError(
                    "OBJECT_STORE_ERROR",
                    f"failed to list objects for {target_space_id}: {exc}",
                ) from exc
        elif expected_assets and self.object_store_adapter is None:
            mismatches.append(
                ClosureMismatch(
                    scope="object_store",
                    key="adapter",
                    expected="configured",
                    actual="missing",
                )
            )

        backup_id = pre_state.get("manifest", {}).get("backup_id", "")
        space_id = pre_state.get("manifest", {}).get("space_id", "")

        return ClosureReport(
            space_id=space_id,
            target_space_id=target_space_id,
            backup_id=backup_id,
            consistent=len(mismatches) == 0,
            mismatches=mismatches,
        )


def _load_pre_state(package_path: Path) -> dict[str, Any]:
    """Load manifest, metadata, kb_ops_export and assets_manifest from package."""
    state: dict[str, Any] = {}

    manifest_path = package_path / "manifest.json"
    if manifest_path.exists():
        state["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))

    metadata_path = package_path / "metadata.json"
    if metadata_path.exists():
        state["metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))

    kb_ops_path = package_path / "kb_ops_export.json"
    if kb_ops_path.exists():
        state["kb_ops_export"] = json.loads(kb_ops_path.read_text(encoding="utf-8"))

    assets_path = package_path / "assets_manifest.json"
    if assets_path.exists():
        state["assets_manifest"] = json.loads(assets_path.read_text(encoding="utf-8"))

    return state


def _hash_blob(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
