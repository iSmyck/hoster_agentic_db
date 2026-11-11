# D.1.2 PostgreSQL and object-store backup (with C.1.1 MinIO staging) — implementation evidence

**Status:** implementation complete; review pass applied; unit tests pass; live acceptance BLOCKED by unavailable MinIO/PostgreSQL sandbox.

## Summary

Implemented D.1.2 on top of the C.1.1 MinIO staging layer per `spec-d1-2-postgresql-and-object-store-backup.md`:

- `docker-compose.yml` — MinIO service and volume uncommented; healthcheck uses `mc ready local` instead of `curl`.
- `src/backup/app/core/config.py` — added MinIO, PostgreSQL backup, and `BACKUP_PG_DUMP_TIMEOUT_SECONDS` settings.
- `src/backup/app/adapters/object_store.py` — `ObjectStoreAdapter` port, `MinioObjectStoreAdapter`, and `StubObjectStoreAdapter`.
- `src/backup/app/services/object_store.py` — staging service with `stage_file`, `build_assets_manifest`, `get_object_content`, `list_object_versions`.
- `src/backup/app/services/postgres_backup.py` — `PostgresBackupService.dump_schemas` for operational schemas.
- `src/backup/app/services/backup.py` — `_backup_postgres` and `_backup_object_store` integrated into `create_full_backup`.
- `src/backup/app/models/backup.py` — `ObjectStoreExport`, `AssetsManifest`, `PostgresExport` models.
- `src/backup/app/api/router.py` — `POST /api/kb/v1/objects/upload`, `POST /api/kb/v1/backups/{space_id:path}/full`.
- `src/backup/tests/test_object_store.py` — adapter/service unit tests.
- `src/backup/tests/test_postgres_backup.py` — `PostgresBackupService` unit tests.
- `src/backup/tests/test_backup_service.py` — full-backup package tests.
- `.env.example` — MinIO/Postgres backup variables added.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `d.1.2-postgresql-and-object-store-backup: done`, `c.1.1-minio-object-store-staging: done`.

## Review fixes applied (Chunk 2)

- Removed bucket auto-creation from `MinioObjectStoreAdapter.__init__`; missing bucket now surfaces as `NoSuchBucket` → HTTP 502.
- Removed `etag` fallback from object version identifiers; only real `version_id` (or `"null"` for non-versioned buckets) is used, so `get_object` no longer receives an invalid version ID.
- Filtered S3 delete markers out of `list_object_versions`.
- Added `ObjectStoreService.get_object_content` and `list_object_versions`; `BackupService._backup_object_store` now uses the service layer instead of reaching through to the adapter.
- Replaced lossy filename sanitization with percent-encoding to avoid object/version collisions.
- Fixed `StubObjectStoreAdapter` version sorting to use numeric order (`v10` > `v9`).
- Added `try/finally` around `get_object` response handling to prevent connection leaks.
- Changed default mapping for unclassified `ObjectStoreServiceError` from HTTP 500 to HTTP 502.
- `create_app` no longer auto-wires a default MinIO adapter when an injected `BackupService` has no object-store service.
- Added configurable `BACKUP_PG_DUMP_TIMEOUT_SECONDS`.
- Made `pg_dump` output atomic via a `.sql.tmp` file + rename.
- Added `version_id` to `ObjectUploadResponse` alongside `version` to satisfy the spec's I/O matrix wording.
- Added OpenAPI 413 response declaration for the upload endpoint.

## Verification

```text
PYTHONPATH=src uv run pytest -q src/backup/tests
60 passed, 1 skipped, 1 warning in 9.22s
```

```text
uv run ruff check src/backup
All checks passed!
```

```text
PYTHONPATH=src uv run pytest -q
316 passed, 5 skipped, 1 warning in 20.67s
```

## Blockers / remaining risk

- **Live runtime acceptance is BLOCKED.** `RUN_LIVE_BACKUP_TESTS=1` and `docker compose up -d postgres keycloak gitlab minio` require a running sandbox. `MinioObjectStoreAdapter` and real `pg_dump` behavior are verified only with stubs and synthetic fixtures.
- Object-store backup currently copies versions of *current* objects only. Older versions of deleted objects are not enumerated because the seed list comes from `list_objects`. A future improvement could snapshot the bucket or scan all versioned keys.
