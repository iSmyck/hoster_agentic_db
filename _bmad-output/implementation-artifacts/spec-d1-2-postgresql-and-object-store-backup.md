---
title: 'D.1.2 PostgreSQL and object-store backup (with C.1.1 MinIO staging)'
type: 'feature'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_commit: '5714de6'
context:
  - specs/corporate-kb/tasks.md
  - specs/corporate-kb/content-standard.md
  - specs/corporate-kb/adr/ADR-015-postgresql-schema-ownership.md
  - src/backup/app/services/backup.py
  - src/backup/app/models/backup.py
  - src/backup/app/api/router.py
  - src/backup/app/core/config.py
warnings:
  - multiple-goals
---

<intent-contract>

## Intent

**Problem:** Для полноценного D.1.2 требуется object-store staging (C.1.1). Сейчас MinIO закомментирован в `docker-compose.yml`, object-store adapter отсутствует, а backup умеет только Git mirror + metadata. Без object-store backup невозможно сохранить immutable raw files/assets и восстановить их при disaster recovery.

**Approach:** Вернуть существенную часть C.1.1 (MinIO/S3 adapter, file upload staging, assets manifest) и на её основе реализовать D.1.2: бэкап PostgreSQL operational schemas (`kb_authz`, `kb_ops`, `kb_index`) и object-store buckets/versions. Расширить существующий `src/backup/` сервис новыми endpoint'ами и интегрировать PostgreSQL/object-store export в per-Space backup package.

## Boundaries & Constraints

**Always:**
- Использовать MinIO как object store (owner decision G1-D5).
- Хранить object-store credentials только в `.env`, не коммитить.
- Backup PostgreSQL выполнять read-only (`pg_dump` или SQLAlchemy SELECT) без изменения схем.
- Backup object-store выполнять read-only (list objects/versions, GET content, compute SHA-256).
- Backup package должен включать `postgres_export/`, `object_store_export/`, `assets_manifest.json`, `manifest.json` с хэшами.
- Secrets/config policy хранить отдельно, не включать в обычный export.

**Never:**
- Не реализовывать connector framework (C.2), parsing pipeline (C.3), content-standard enforcement queue (C.4) — они остаются в бэклоге.
- Не реализовывать media classification (C.1.2) — остаётся в бэклоге.
- Не писать в canonical Git и не модифицировать PostgreSQL schemas.
- Не менять pinned versions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| File upload staging | `POST /api/kb/v1/objects/upload` with file + space_id | Object stored in MinIO, returns `{object_id, version_id, sha256, size}` | Invalid space_id → 400; bucket missing → 502 |
| Assets manifest | Space with staged objects | `assets_manifest.json` lists все объекты с version_id/sha256 | — |
| PostgreSQL backup per schema | `kb_authz`/`kb_ops`/`kb_index` schemas | SQL dump/JSON export в backup package | DB unreachable → 502 |
| Object-store backup | Bucket with versions | All object versions copied to backup dir с SHA-256 | Store unreachable → 502 |
| Combined backup package | Space with Git + PostgreSQL + objects | `manifest.json` hashes all parts | Hash mismatch → 500 |
| Empty object store | Space без объектов | Empty `object_store_export/`, valid manifest | — |

</intent-contract>

## Code Map

- `docker-compose.yml` — uncomment MinIO service; add `minio_data` volume.
- `src/backup/app/core/config.py` — добавить `BACKUP_MINIO_ENDPOINT`, `BACKUP_MINIO_ACCESS_KEY`, `BACKUP_MINIO_SECRET_KEY`, `BACKUP_MINIO_USE_SSL`, `BACKUP_MINIO_BUCKET`, `BACKUP_POSTGRES_*` vars.
- `src/backup/app/adapters/object_store.py` — `ObjectStoreAdapter` ABC + `MinioObjectStoreAdapter` (upload, list_objects, get_object, list_object_versions).
- `src/backup/app/services/object_store.py` — staging service: `stage_file`, `build_assets_manifest`.
- `src/backup/app/services/postgres_backup.py` — `PostgresBackupService`: `dump_schema(schema_name)` using `pg_dump` subprocess or SQLAlchemy metadata export; read-only.
- `src/backup/app/services/backup.py` — extend `BackupService` to optionally include `postgres_export/` and `object_store_export/` in the package; update `_assemble_package` / `_compute_manifest`.
- `src/backup/app/models/backup.py` — добавить `ObjectStoreExport`, `AssetsManifest`, `PostgresExport` модели.
- `src/backup/app/api/router.py` — добавить `POST /api/kb/v1/objects/upload`, `POST /api/kb/v1/backups/{space_id}/full` (Git + PostgreSQL + object store).
- `src/backup/scripts/smoke_backup.py` — extend to verify object-store backup when sandbox available.
- `src/backup/tests/test_object_store.py` — unit tests с mock MinIO adapter.
- `src/backup/tests/test_postgres_backup.py` — unit tests для `PostgresBackupService`.
- `.env.example` — добавить MinIO/Postgres backup переменные.

## Tasks & Acceptance

**Execution:**
- [x] `docker-compose.yml` -- uncomment MinIO service and volume -- чтобы backup мог работать против реального object store.
- [x] `src/backup/app/core/config.py` -- добавить MinIO и Postgres backup settings с префиксами `BACKUP_*` -- configuration for new adapters.
- [x] `src/backup/app/adapters/object_store.py` -- реализовать `ObjectStoreAdapter` порт и `MinioObjectStoreAdapter` -- upload, list, get, list versions.
- [x] `src/backup/app/services/object_store.py` -- реализовать `stage_file(space_id, path, content)` и `build_assets_manifest(space_id)` -- C.1.1 staging essence.
- [x] `src/backup/app/services/postgres_backup.py` -- реализовать `PostgresBackupService.dump_schemas()` для `kb_authz`, `kb_ops`, `kb_index` -- D04.
- [x] `src/backup/app/services/backup.py` -- добавить `_backup_postgres`, `_backup_object_store`, интегрировать их в `create_full_backup` -- D05 + package assembly.
- [x] `src/backup/app/models/backup.py` -- добавить Pydantic модели для object-store и postgres exports.
- [x] `src/backup/app/api/router.py` -- добавить endpoints для upload и full backup.
- [x] `src/backup/tests/test_object_store.py` -- unit tests с stub object-store adapter.
- [x] `src/backup/tests/test_postgres_backup.py` -- unit tests с SQLite/in-memory engine.
- [x] `src/backup/tests/test_backup_service.py` -- extend existing tests to cover full backup package.
- [x] `src/backup/scripts/smoke_backup.py` -- extend smoke to verify full backup.
- [x] `.env.example` -- добавить MinIO/Postgres backup variables.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- обновить `d.1.2-postgresql-and-object-store-backup: done`, `c.1.1-minio-object-store-staging: done`.

**Acceptance Criteria:**
- Given valid file upload, when `stage_file` called, then object stored in MinIO with SHA-256 and version_id returned.
- Given Space with staged objects, when assets manifest built, then it lists all objects with version_id and sha256.
- Given running PostgreSQL with `kb_authz`/`kb_ops`/`kb_index`, when PostgreSQL backup runs, then dumps contain schema-owned tables without data loss.
- Given MinIO bucket with object versions, when object-store backup runs, then all versions copied to backup dir with matching SHA-256.
- Given full backup completed, when manifest verified, then hashes of postgres_export, object_store_export, mirror.git, metadata.json, kb_ops_export.json match.

## Design Notes

- MinIO bucket naming: `kb-backups-{space_id}` or single `kb-backups` bucket with `space_id/` prefix. Use single bucket with prefixes to simplify sandbox.
- Object versions: MinIO supports versioning if enabled on bucket; fallback to `etag` as version identifier.
- PostgreSQL backup: use `pg_dump --schema-only` + `pg_dump --data-only` per schema, or SQLAlchemy `MetaData.reflect()` + `SELECT` per table. For sandbox simplicity, prefer `pg_dump` subprocess with read-only connection string.
- Full backup endpoint optionally includes object-store; `POST /api/kb/v1/backups/{space_id}/mirror` remains Git-only for backward compatibility.
- Assets manifest format follows content-standard.md: `{object_id, version, sha256, size, media_type, source_ref}`.

## Verification

**Commands:**
- `docker compose up -d postgres keycloak gitlab minio` -- expected: services healthy.
- `uv run pytest -q src/backup/tests` -- expected: all pass.
- `RUN_LIVE_BACKUP_TESTS=1 PYTHONPATH=src uv run python src/backup/scripts/smoke_backup.py` -- expected: exit 0 if sandbox available.
- `uv run ruff check src/backup` -- expected: clean.

## Review Triage Log

### 2026-11-10 — Initial draft
- (none)

### 2026-11-10 — Post-implementation review fixes
- `postgres_backup.py`: merged `env` with `os.environ`, added subprocess `timeout=300`.
- `object_store.py`: split `status_code`/`s3_code` on `ObjectStoreAdapterError`; SHA-256 metadata now mandatory (no ETag fallback); `source_ref` persisted in metadata; `StubObjectStoreAdapter.get_object(version=None)` returns latest version.
- `router.py`: upload size limited by `BACKUP_MAX_UPLOAD_SIZE_BYTES` (413 if exceeded); `space_id` validated on full backup endpoint.
- `backup.py`: object filenames sanitized aggressively; duplicate destination versions raise `DUPLICATE_OBJECT_VERSION`.
- `models/backup.py`: renamed `version_id` → `version` in `ObjectStoreEntry` to match content-standard.md.
- Added endpoint failure-path tests for object-store/Postgres 502 responses and upload missing-bucket 502.

### 2026-11-10 — Phase D adversarial review (Chunk 2)
- `[high]` `[patch]` `MinioObjectStoreAdapter` auto-created bucket on init, hiding the "bucket missing → 502" contract; removed auto-creation.
- `[high]` `[patch]` ETag was used as a fallback `version_id` and then passed to `get_object(version_id=etag)`, breaking non-versioned buckets; removed ETag fallback.
- `[high]` `[patch]` `list_object_versions` did not filter S3 delete markers; filtered them out.
- `[medium]` `[patch]` `BackupService._backup_object_store` reached through `ObjectStoreService` to the adapter; added service methods `get_object_content`/`list_object_versions`.
- `[medium]` `[patch]` Object export filenames used lossy `_` substitution causing collisions; switched to percent-encoding.
- `[medium]` `[patch]` `StubObjectStoreAdapter` sorted versions lexicographically (`v9` > `v10`); fixed numeric sorting.
- `[medium]` `[patch]` `MinioObjectStoreAdapter.get_object` leaked connections on read failure; added `try/finally`.
- `[medium]` `[patch]` Unclassified `ObjectStoreServiceError` defaulted to HTTP 500; changed default to 502.
- `[medium]` `[patch]` `create_app` auto-wired a default MinIO adapter even when an injected `BackupService` had none; now respects the injected service.
- `[medium]` `[patch]` `pg_dump` timeout was hard-coded 300s; added `BACKUP_PG_DUMP_TIMEOUT_SECONDS`.
- `[medium]` `[patch]` `pg_dump` wrote directly to final file; switched to atomic `.sql.tmp` + rename.
- `[low]` `[patch]` Upload response omitted `version_id`; added it alongside `version`.
- `[low]` `[patch]` Upload endpoint did not declare HTTP 413 response; added it.
- `[low]` `[patch]` `docker-compose.yml` MinIO healthcheck used `curl` (not in image); replaced with `mc ready local`.

## Auto Run Result

- 2026-11-10: `uv run pytest -q` → 291 passed, 5 skipped, 1 warning; `uv run ruff check src/backup` → clean. Live MinIO/PostgreSQL sandbox verification BLOCKED (no running sandbox in this environment).
