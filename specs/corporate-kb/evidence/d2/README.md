# D.2 + D.4.1 Restore, closure verification and backup integrity — implementation evidence

**Status:** implementation complete; review pass applied; unit tests pass; live acceptance BLOCKED by unavailable GitLab/PostgreSQL/MinIO restore sandbox.

## Summary

Implemented restore, closure verification, and integrity checking per `spec-d2-d4-1-restore-closure-integrity.md`:

- `src/backup/app/models/restore.py` — Pydantic models: `RestoreRequest`, `RestoreResult`, `RestoreStep`, `RestoreStatus`, `IntegrityReport`, `ClosureReport`, `ClosureMismatch`.
- `src/backup/app/services/integrity.py` — `IntegrityChecker.verify(package_path)`: recomputes SHA-256 for every manifest-listed file and reports mismatches/missing files.
- `src/backup/app/services/closure.py` — `ClosureVerifier.verify(package_path, target_space_id)`: compares pre-backup tag count, kb_ops decision count, and object-store object hashes/counts against the restored target.
- `src/backup/app/services/restore.py` — `RestoreService.restore(...)`: loads package, runs integrity check, checks target existence, restores Git mirror, PostgreSQL schemas, object-store objects, and runs closure verification.
- `src/backup/app/adapters/gitlab.py` — added `get_default_branch` and `push_mirror` to `BackupGitLabAdapter` (HTTP + stub).
- `src/backup/app/adapters/object_store.py` — added `put_object` and `create_bucket` for restore.
- `src/backup/app/services/postgres_backup.py` — added `restore_schemas(export_dir)` via `psql` subprocess, `schemas_exist()` for target checks, and parameterized `count_decisions`.
- `src/backup/app/api/router.py` — endpoints `POST /api/kb/v1/backups/{space_id:path}/restore` and `POST /api/kb/v1/backups/{space_id:path}/verify-integrity`.
- `src/backup/app/main.py` — `RestoreService` is now wired with separate restore-target PostgreSQL credentials.
- `src/backup/tests/test_restore.py` — unit tests for restore success, target-exists rejection, force overwrite, corrupt-package abort, closure mismatch, missing package, and endpoint contracts.
- `src/backup/tests/test_integrity.py` — unit tests for valid package, corrupt file, and missing file.
- `.env.example` — added `BACKUP_RESTORE_*` target-environment variables.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `d.2-point-in-time-restore: done`, `d.4.1-integrity-verification: done`, `d.4-backup-integrity-encryption-and-retention: in-progress`, D.4.2–D.4.4 in backlog.

## Review fixes applied (Chunk 3)

- `RestoreService` now uses a separate restore-target `PostgresBackupService` built from `BACKUP_RESTORE_POSTGRES_*` settings instead of reusing the source backup service.
- `_target_exists` now checks the GitLab default branch (not hard-coded `main`) and the PostgreSQL operational schemas; non-404 GitLab errors and PostgreSQL check failures surface as `TARGET_CHECK_FAILED` (HTTP 502) instead of being treated as "target missing".
- `BackupGitLabAdapter.push_mirror` no longer returns the credential-embedded URL; it uses `urlparse`/`urlunparse` for safer URL construction.
- `PostgresBackupService.count_decisions` now uses `psql` variable substitution (`:'space_id'`) instead of string interpolation.
- `verify-integrity` endpoint returns HTTP 409 when the integrity check fails, with the full report in the response body.
- `restore` endpoint returns HTTP 409 when the package fails the integrity check instead of returning HTTP 200 with a failed status.
- `backup_id` is sanitized in `RestoreService` to prevent directory traversal.
- Integrity and restore status sidecars are written next to the package directory (`{package}.integrity_report.json`, `{package}.restore_status.json`) rather than inside it, preserving the immutable package contents.
- Object-store restore now calls `create_bucket` before `put_object`.
- Object-store restore filenames use the same percent-encoding scheme as backup to avoid collisions.
- `RestoreResponse` and `IntegrityResponse` schemas now include `restored_at` / `checked_at`.
- Sprint status corrected: D.4 is `in-progress` (only D.4.1 done) and duplicate D.4.x keys were removed.

## Verification

```text
PYTHONPATH=src uv run pytest -q src/backup/tests
60 passed, 1 skipped, 1 warning in 6.48s
```

```text
uv run ruff check src/backup
All checks passed!
```

```text
PYTHONPATH=src uv run pytest -q
316 passed, 5 skipped, 1 warning in 12.12s
```

## Blockers / remaining risk

- **Live runtime acceptance is BLOCKED.** Real `git push --mirror`, `psql` restore, and MinIO `put_object` are verified only with stubs and synthetic fixtures. A gated live test (`RUN_LIVE_RESTORE_TESTS=1`) was not added because it requires a provisioned GitLab/PostgreSQL/MinIO target environment.
- Closure verification does not compare policy/grants hashes (spec intent mentions them; no policy/grants artifact is produced by the current backup package).
- Managed-write freeze is implemented only as a restore-status sidecar, not as a distributed write barrier.
