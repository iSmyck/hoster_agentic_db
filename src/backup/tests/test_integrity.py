"""Unit tests for the backup package IntegrityChecker."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from backup.app.models.backup import BackupManifest, FileHash
from backup.app.services.integrity import IntegrityChecker, IntegrityCheckerError


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def valid_package(tmp_path: Path) -> Path:
    package = tmp_path / "pkg"
    package.mkdir()

    content = b"hello world"
    data_file = package / "data.txt"
    data_file.write_bytes(content)

    manifest = BackupManifest(
        space_id="demo-space",
        backup_id="b1",
        head_sha="a" * 40,
        hour_bucket="2026010100",
        files=[FileHash(path="data.txt", sha256=_sha256(content))],
    )
    _write_json(package / "manifest.json", manifest.model_dump(mode="json"))
    return package


def test_valid_package_passes(valid_package: Path) -> None:
    checker = IntegrityChecker()
    report = checker.verify(valid_package)

    assert report.verified is True
    assert report.checked_files == 1
    assert report.mismatches == []
    assert report.missing_files == []
    assert report.space_id == "demo-space"
    assert report.backup_id == "b1"
    assert (valid_package / "integrity_report.json").exists()


def test_corrupt_file_fails(valid_package: Path) -> None:
    data_file = valid_package / "data.txt"
    data_file.write_bytes(b"tampered")

    checker = IntegrityChecker()
    report = checker.verify(valid_package)

    assert report.verified is False
    assert len(report.mismatches) == 1
    assert report.mismatches[0]["path"] == "data.txt"
    assert report.mismatches[0]["expected"] == _sha256(b"hello world")
    assert report.mismatches[0]["actual"] == _sha256(b"tampered")


def test_missing_file_reported(valid_package: Path) -> None:
    (valid_package / "data.txt").unlink()

    checker = IntegrityChecker()
    report = checker.verify(valid_package)

    assert report.verified is False
    assert report.checked_files == 0
    assert report.missing_files == ["data.txt"]


def test_missing_package_raises(tmp_path: Path) -> None:
    checker = IntegrityChecker()
    with pytest.raises(IntegrityCheckerError) as exc_info:
        checker.verify(tmp_path / "missing")
    assert exc_info.value.code == "PACKAGE_NOT_FOUND"


def test_missing_manifest_raises(valid_package: Path) -> None:
    (valid_package / "manifest.json").unlink()
    checker = IntegrityChecker()
    with pytest.raises(IntegrityCheckerError) as exc_info:
        checker.verify(valid_package)
    assert exc_info.value.code == "MANIFEST_MISSING"
