"""PostgreSQL operational-schema backup service (read-only pg_dump)."""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from backup.app.models.backup import PostgresExport, PostgresExportFile

logger = logging.getLogger(__name__)


class PostgresBackupServiceError(Exception):
    """Raised when a PostgreSQL backup operation fails."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class PostgresBackupService:
    """Read-only exporter for operational PostgreSQL schemas.

    Uses ``pg_dump`` subprocess by default.  The subprocess runner can be
    overridden in tests to avoid a real PostgreSQL dependency.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        db: str,
        schemas: list[str] | None = None,
        pg_dump_command: list[str] | None = None,
        run_command: Any | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.schemas = list(schemas) if schemas else ["kb_authz", "kb_ops", "kb_index"]
        self.pg_dump_command = pg_dump_command or ["pg_dump"]
        self._run_command = run_command if run_command is not None else subprocess.run

    def dump_schemas(
        self,
        space_id: str,
        output_dir: Path,
    ) -> PostgresExport:
        """Dump schema-only and data-only SQL for each operational schema.

        Returns a ``PostgresExport`` describing the produced files and their
        SHA-256 hashes.  Raises ``PostgresBackupServiceError`` on failure.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        files: list[PostgresExportFile] = []

        env = {**os.environ, "PGPASSWORD": self.password}
        base_command = [
            *self.pg_dump_command,
            "--host",
            self.host,
            "--port",
            str(self.port),
            "--username",
            self.user,
            "--dbname",
            self.db,
            "--no-owner",
            "--no-privileges",
        ]

        for schema in self.schemas:
            for kind, extra_args in [("schema", ["--schema-only"]), ("data", ["--data-only"])]:
                file_path = output_dir / f"{schema}_{kind}.sql"
                command = [*base_command, *extra_args, "--schema", schema]
                try:
                    with file_path.open("wb") as f:
                        result = self._run_command(
                            command,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            env=env,
                            check=False,
                            timeout=300,
                        )
                    if result.returncode != 0:
                        stderr = (
                            result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
                        )
                        logger.error("pg_dump failed for %s %s: %s", schema, kind, stderr)
                        raise PostgresBackupServiceError(
                            "PG_DUMP_FAILED",
                            f"pg_dump failed for {schema} ({kind}): {stderr}",
                        )
                except FileNotFoundError as exc:
                    raise PostgresBackupServiceError(
                        "PG_DUMP_NOT_FOUND",
                        f"pg_dump not found: {exc}",
                    ) from exc
                except PostgresBackupServiceError:
                    raise
                except Exception as exc:
                    raise PostgresBackupServiceError(
                        "POSTGRES_BACKUP_ERROR",
                        f"unexpected error dumping {schema} ({kind}): {exc}",
                    ) from exc

                sha256 = _sha256_file(file_path)
                files.append(
                    PostgresExportFile(
                        schema_name=schema,
                        kind=kind,
                        path=str(file_path.relative_to(output_dir.parent)),
                        sha256=sha256,
                    )
                )

        return PostgresExport(space_id=space_id, files=files)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
