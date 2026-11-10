"""Unit tests for PostgresBackupService."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

import pytest

from backup.app.services.postgres_backup import PostgresBackupService, PostgresBackupServiceError


def _fake_run(returncode: int = 0, stderr: bytes = b"") -> Any:
    class Result:
        def __init__(self) -> None:
            self.returncode = returncode
            self.stderr = stderr

    def run(*args: Any, **kwargs: Any) -> Any:
        stdout = kwargs.get("stdout")
        if stdout is not None:
            stdout.write(b"-- synthetic pg_dump output\n")
        return Result()

    return run


def test_dump_schemas_creates_files() -> None:
    service = PostgresBackupService(
        host="localhost",
        port=5432,
        user="corp_kb",
        password="secret",
        db="corp_kb",
        schemas=["kb_authz", "kb_ops", "kb_index"],
        run_command=_fake_run(),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = Path(tmpdir) / "postgres_export"
        export = service.dump_schemas("demo-space", export_dir)

        assert export.space_id == "demo-space"
        assert len(export.files) == 6
        for schema in ["kb_authz", "kb_ops", "kb_index"]:
            schema_file = export_dir / f"{schema}_schema.sql"
            data_file = export_dir / f"{schema}_data.sql"
            assert schema_file.exists()
            assert data_file.exists()
            assert schema_file.read_bytes() == b"-- synthetic pg_dump output\n"


def test_dump_schemas_hashes_match() -> None:
    service = PostgresBackupService(
        host="localhost",
        port=5432,
        user="corp_kb",
        password="secret",
        db="corp_kb",
        schemas=["kb_ops"],
        run_command=_fake_run(),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = Path(tmpdir) / "postgres_export"
        export = service.dump_schemas("demo-space", export_dir)

        for file_info in export.files:
            file_path = (Path(tmpdir) / file_info.path).resolve()
            expected = hashlib.sha256(file_path.read_bytes()).hexdigest()
            assert file_info.sha256 == expected


def test_dump_schemas_failure_raises() -> None:
    service = PostgresBackupService(
        host="localhost",
        port=5432,
        user="corp_kb",
        password="secret",
        db="corp_kb",
        schemas=["kb_ops"],
        run_command=_fake_run(returncode=1, stderr=b"connection refused"),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = Path(tmpdir) / "postgres_export"
        with pytest.raises(PostgresBackupServiceError) as exc_info:
            service.dump_schemas("demo-space", export_dir)
        assert exc_info.value.code == "PG_DUMP_FAILED"


def test_dump_schemas_pg_dump_not_found() -> None:
    def fail(*args: Any, **kwargs: Any) -> Any:
        raise FileNotFoundError("pg_dump")

    service = PostgresBackupService(
        host="localhost",
        port=5432,
        user="corp_kb",
        password="secret",
        db="corp_kb",
        schemas=["kb_ops"],
        run_command=fail,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = Path(tmpdir) / "postgres_export"
        with pytest.raises(PostgresBackupServiceError) as exc_info:
            service.dump_schemas("demo-space", export_dir)
        assert exc_info.value.code == "PG_DUMP_NOT_FOUND"
