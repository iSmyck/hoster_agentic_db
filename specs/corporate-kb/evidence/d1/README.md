# D.1.1 Git mirror and metadata backup — implementation evidence

**Status:** implementation complete; review pass applied; unit tests pass; live acceptance BLOCKED by unavailable sandbox.

## Summary

Implemented the `src/backup/` service per `spec-d1-1-git-mirror-and-metadata-backup.md`:

- `src/backup/app/core/config.py` — `Settings` with `BACKUP_*` prefixes and fallback to `GO_GITLAB_URL`/`GO_GITLAB_TOKEN`.
- `src/backup/app/adapters/gitlab.py` — `BackupGitLabAdapter`, HTTP and stub implementations for read-only MR/note/tag export and default-branch resolution.
- `src/backup/app/models/backup.py` — Pydantic models for package, manifest, metadata and kb_ops exports.
- `src/backup/app/services/backup.py` — `BackupService` orchestrating `git clone --mirror`, metadata export, kb_ops read-only export (proposals, decisions, source_sync_cursors, cutovers), package assembly and SHA-256 manifest verification.
- `src/backup/app/api/router.py` — `POST /api/kb/v1/backups/{space_id:path}/mirror`, `GET /api/kb/v1/backups/{space_id:path}/latest`, `GET /health`.
- `src/backup/app/main.py` — FastAPI factory with dependency injection.
- `src/backup/tests/conftest.py` — fixtures for stub adapter, synthetic git repo, SQLite kb_ops and temporary storage.
- `src/backup/tests/test_backup_service.py` — unit tests for mirror creation, metadata/kb_ops export, manifest hashes, idempotency, default-branch HEAD resolution, nested space_id handling and failure handling.
- `src/backup/tests/test_backup_live.py` — live integration tests skipped unless `RUN_LIVE_BACKUP_TESTS=1`.
- `src/backup/scripts/smoke_backup.py` — smoke script that skips when sandbox is unavailable.
- `.env.example` — added backup configuration variables.
- `pyproject.toml` — added `src/backup/tests` to `testpaths`.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — added `d.1.1-git-mirror-and-metadata-backup: done`.

## Review fixes applied (Chunk 1)

- Allowed GitLab-style nested `space_id` values (`corp-kb/sales`) while rejecting path traversal.
- Changed idempotency key to `sha256(space_id + head_sha)` so repeated requests for the same HEAD return the existing package.
- Added `BackupGitLabAdapter.get_default_branch()` and used it for HEAD resolution instead of hard-coded `main`.
- Closed the backup-creation race with `package_path.mkdir(parents=True, exist_ok=False)`.
- Fixed GitLab pagination to use the `x-next-page` response header.
- Aligned API error schema with the spec: responses now return `{code, detail}`.
- Expanded kb_ops export to include `source_sync_cursors` and `cutovers`.
- Sort `get_latest` by `manifest.created_at` instead of filesystem mtime.
- Hardened row serialization for non-JSON kb_ops column types.
- Moved `status.json` to a package sidecar (`.status.json`) so the package directory contains only the spec-defined files.
- Mapped GitLab network/timeout failures to HTTP 502.

## Verification

```text
PYTHONPATH=src uv run pytest -q src/backup/tests
53 passed, 1 skipped, 1 warning in 11.72s
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

- **Live runtime acceptance is BLOCKED.** `RUN_LIVE_BACKUP_TESTS=1` requires a running GitLab sandbox (`docker compose up -d gitlab`) and a real Space. The implementation has been verified only with synthetic fixtures and a local bare repository.
- The `git clone --mirror` path embeds the token in the URL for sandbox simplicity. For production, a credential helper or SSH deploy key should be used instead.
- Object storage backup is explicitly out of scope for D.1.1 (deferred to D.1.2/D.1.3 per ADR-19 and the spec).
