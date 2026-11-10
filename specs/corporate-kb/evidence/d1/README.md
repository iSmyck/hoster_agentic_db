# D.1.1 Git mirror and metadata backup — implementation evidence

**Status:** implementation complete; unit tests pass; live acceptance BLOCKED by unavailable sandbox.

## Summary

Implemented the `src/backup/` service per `spec-d1-1-git-mirror-and-metadata-backup.md`:

- `src/backup/app/core/config.py` — `Settings` with `BACKUP_*` prefixes and fallback to `GO_GITLAB_URL`/`GO_GITLAB_TOKEN`.
- `src/backup/app/adapters/gitlab.py` — `BackupGitLabAdapter`, HTTP and stub implementations for read-only MR/note/tag export.
- `src/backup/app/models/backup.py` — Pydantic models for package, manifest, metadata and kb_ops exports.
- `src/backup/app/services/backup.py` — `BackupService` orchestrating `git clone --mirror`, metadata export, kb_ops read-only export, package assembly and SHA-256 manifest verification.
- `src/backup/app/api/router.py` — `POST /api/kb/v1/backups/{space_id}/mirror`, `GET /api/kb/v1/backups/{space_id}/latest`, `GET /health`.
- `src/backup/app/main.py` — FastAPI factory with dependency injection.
- `src/backup/tests/conftest.py` — fixtures for stub adapter, synthetic git repo, SQLite kb_ops and temporary storage.
- `src/backup/tests/test_backup_service.py` — unit tests for mirror creation, metadata/kb_ops export, manifest hashes, idempotency and failure handling.
- `src/backup/tests/test_backup_live.py` — live integration tests skipped unless `RUN_LIVE_BACKUP_TESTS=1`.
- `src/backup/scripts/smoke_backup.py` — smoke script that skips when sandbox is unavailable.
- `.env.example` — added backup configuration variables.
- `pyproject.toml` — added `src/backup/tests` to `testpaths`.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — added `d.1.1-git-mirror-and-metadata-backup: done`.

## Verification

```text
PYTHONPATH=src BACKUP_DATABASE_URL=sqlite:///:memory: BACKUP_KB_OPS_SCHEMA= KB_OPS_SCHEMA= GO_KB_OPS_SCHEMA= uv run pytest -q src/backup/tests
11 passed, 1 skipped, 1 warning in 2.46s
```

```text
uv run ruff check src/backup
All checks passed!
```

```text
PYTHONPATH=src BACKUP_DATABASE_URL=sqlite:///:memory: BACKUP_KB_OPS_SCHEMA= KB_OPS_SCHEMA= GO_KB_OPS_SCHEMA= uv run pytest -q
267 passed, 5 skipped, 1 warning in 8.54s
```

## Blockers / remaining risk

- **Live runtime acceptance is BLOCKED.** `RUN_LIVE_BACKUP_TESTS=1` requires a running GitLab sandbox (`docker compose up -d gitlab`) and a real Space. The implementation has been verified only with synthetic fixtures and a local bare repository.
- The `git clone --mirror` path embeds the token in the URL for sandbox simplicity. For production, a credential helper or SSH deploy key should be used instead.
- Object storage backup is explicitly out of scope for D.1.1 (deferred to D.1.2/D.1.3 per ADR-19 and the spec).
