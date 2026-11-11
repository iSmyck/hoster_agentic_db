"""Backup package integrity checker: recompute SHA-256 and compare to manifest."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from backup.app.models.backup import BackupManifest
from backup.app.models.restore import IntegrityReport

logger = logging.getLogger(__name__)


class IntegrityCheckerError(Exception):
    """Raised when an integrity check cannot be performed."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class IntegrityChecker:
    """Verify that every file in a backup package matches manifest.json.

    The checker is read-only with respect to the original backup package: it
    may append an ``integrity_report.json`` sidecar, but never modifies the
    files listed in the manifest.
    """

    def verify(self, package_path: Path | str) -> IntegrityReport:
        """Return an IntegrityReport for the package at ``package_path``.

        Raises ``IntegrityCheckerError`` if the package or manifest is missing.
        """
        package_path = Path(package_path)
        if not package_path.is_dir():
            raise IntegrityCheckerError("PACKAGE_NOT_FOUND", f"package not found: {package_path}")

        manifest_path = package_path / "manifest.json"
        if not manifest_path.exists():
            raise IntegrityCheckerError(
                "MANIFEST_MISSING", f"manifest.json missing in {package_path}"
            )

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = BackupManifest.model_validate(manifest_data)
        except Exception as exc:
            raise IntegrityCheckerError(
                "MANIFEST_INVALID", f"manifest.json invalid: {exc}"
            ) from exc

        mismatches: list[dict[str, Any]] = []
        missing_files: list[str] = []
        checked_files = 0

        for file_hash in manifest.files:
            file_path = package_path / file_hash.path
            if not file_path.exists():
                missing_files.append(file_hash.path)
                continue
            checked_files += 1
            actual = _sha256_file(file_path)
            if actual != file_hash.sha256:
                mismatches.append(
                    {
                        "path": file_hash.path,
                        "expected": file_hash.sha256,
                        "actual": actual,
                    }
                )

        report = IntegrityReport(
            space_id=manifest.space_id,
            backup_id=manifest.backup_id,
            package_path=str(package_path),
            verified=len(mismatches) == 0 and len(missing_files) == 0,
            checked_files=checked_files,
            mismatches=mismatches,
            missing_files=missing_files,
        )

        try:
            sidecar_path = package_path.with_suffix(".integrity_report.json")
            sidecar_path.write_text(
                json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to write integrity report sidecar for %s: %s", package_path, exc)

        return report


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
