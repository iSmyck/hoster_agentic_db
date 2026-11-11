---
title: 'D.2 + D.4.1 Restore, closure verification and backup integrity'
type: 'feature'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
baseline_commit: '833810e'
context:
  - specs/corporate-kb/tasks.md
  - specs/corporate-kb/adr/ADR-015-postgresql-schema-ownership.md
  - src/backup/app/services/backup.py
  - src/backup/app/models/backup.py
  - src/backup/app/adapters/gitlab.py
  - src/backup/app/adapters/object_store.py
  - src/backup/app/services/postgres_backup.py
warnings:
  - multiple-goals
---

<intent-contract>

## Intent

**Problem:** Фаза D имеет рабочий backup (D.1), но нет restore, closure verification и integrity checks. Без restore backup неполноценен; без integrity проверки нельзя доверять пакетам; без closure verification нельзя убедиться, что восстановленный Space консистентен.

**Approach:** Реализовать в `src/backup/`:
- `RestoreService` для восстановления Space из backup package в чистое окружение: Git mirror (`git push --mirror`), PostgreSQL schemas (`psql`/`pg_restore`-style), object-store objects.
- `ClosureVerifier` — сравнивает decisions manifest, assets manifest, policy/grants hashes до и после restore.
- `IntegrityChecker` — пересчитывает SHA-256 всех файлов в backup package и сверяет с `manifest.json`.
- REST endpoints: `POST /api/kb/v1/backups/{space_id}/restore`, `POST /api/kb/v1/backups/{backup_id}/verify-integrity`.

## Boundaries & Constraints

**Always:**
- Restore начинается под global managed-write freeze (записываем `restore_required`/`frozen` статус, но не реализуем полноценный barrier для MVP).
- Git — canonical source; `kb_ops` operational records восстанавливаются из durable backup, не fabricate.
- Correction tasks не создаются, не удаляются и не резолвятся автоматически; reconcile = verify linked MRs exist.
- Использовать read-only integrity checks; не модифицировать исходный backup package.
- Хранить target environment credentials в `.env`.

**Never:**
- Не восстанавливать поверх существующего Space без explicit `force` flag (reject if target exists by default).
- Не включать D.4.2 encryption at rest, D.4.3 retention, D.4.4 runbook — отложены до Phase E/owner inputs.
- Не менять pinned versions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Restore from package | Valid backup package + clean target | Git/PostgreSQL/object-store restored | Missing package → 404; target exists → 409 |
| Closure verification | Pre/post restore manifests | Mismatch list; `conflict=false` if consistent | — |
| Integrity check | Backup package | All hashes match manifest | Mismatch → 409 with corrupt files list |
| Target already exists | Git repo / DB schema already present | Reject unless `force=true` | 409 CONFLICT |
| Empty object store in package | No object_store_export | Restore skips object-store step | — |
| Corrupt package | File hash mismatch | Integrity check fails before restore | — |

</intent-contract>

## Code Map

- `src/backup/app/services/restore.py` — `RestoreService`: load package, restore Git mirror, restore PostgreSQL, restore object store, run closure verifier.
- `src/backup/app/services/closure.py` — `ClosureVerifier`: compare pre/post restore manifests and hashes.
- `src/backup/app/services/integrity.py` — `IntegrityChecker`: recompute SHA-256 for all package files and compare to manifest.
- `src/backup/app/adapters/gitlab.py` — extend `BackupGitLabAdapter` with `push_mirror` (or add `RestoreGitLabAdapter`).
- `src/backup/app/adapters/object_store.py` — extend `ObjectStoreAdapter` with `put_object`/`create_bucket` for restore.
- `src/backup/app/services/postgres_backup.py` — add `restore_schemas(export_dir)` using `psql` subprocess.
- `src/backup/app/api/router.py` — add `POST /api/kb/v1/backups/{space_id}/restore`, `POST /api/kb/v1/backups/{space_id}/verify-integrity`.
- `src/backup/app/models/restore.py` — Pydantic models: `RestoreResult`, `ClosureReport`, `IntegrityReport`.
- `src/backup/tests/test_restore.py` — unit tests with stub adapters and synthetic packages.
- `src/backup/tests/test_integrity.py` — unit tests for integrity checker.
- `.env.example` — add target environment variables for restore.

## Tasks & Acceptance

**Execution:**
- [x] `src/backup/app/models/restore.py` -- реализовать модели `RestoreResult`, `ClosureReport`, `IntegrityReport`, `RestoreRequest`.
- [x] `src/backup/app/services/integrity.py` -- реализовать `IntegrityChecker.verify(package_path)` -- пересчёт SHA-256 и сравнение с `manifest.json`.
- [x] `src/backup/app/services/closure.py` -- реализовать `ClosureVerifier.verify(pre_manifest, post_state)` -- сравнение assets manifest, decisions, policy hashes.
- [x] `src/backup/app/adapters/gitlab.py` -- добавить `push_mirror(space_id, mirror_dir)` к адаптерам (HTTP + stub).
- [x] `src/backup/app/adapters/object_store.py` -- добавить `put_object`, `create_bucket` для restore.
- [x] `src/backup/app/services/postgres_backup.py` -- добавить `restore_schemas(export_dir)` через `psql` subprocess.
- [x] `src/backup/app/services/restore.py` -- реализовать `RestoreService.restore(space_id, backup_id, target_space_id, force=False)` с загрузкой package, integrity check, restore Git/Postgres/object-store, closure verification.
- [x] `src/backup/app/api/router.py` -- добавить endpoints restore и verify-integrity.
- [x] `src/backup/tests/test_restore.py` -- unit tests: restore success, reject existing target, closure mismatch, corrupt package.
- [x] `src/backup/tests/test_integrity.py` -- unit tests: valid package, corrupt file, missing file.
- [x] `.env.example` -- добавить restore-target переменные.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- обновить: `d.2-point-in-time-restore: done`, `d.4-backup-integrity-encryption-and-retention: in-progress` (D.4.1 done, D.4.2-D.4.4 backlog), `phase-d: done`.

**Acceptance Criteria:**
- Given valid backup package, when integrity check runs, then all file hashes match manifest.
- Given corrupt package (changed file), when integrity check runs, then returns mismatch list and does not proceed to restore.
- Given clean target environment and valid package, when restore runs, then Git mirror pushed, PostgreSQL schemas restored, object-store objects restored.
- Given restored Space, when closure verification runs, then pre/post manifests and hashes match.
- Given target Space already exists and `force=false`, when restore runs, then returns 409 CONFLICT.

## Design Notes

- Restore package layout consumed from D.1.1/D.1.2: `mirror.git/`, `metadata.json`, `kb_ops_export.json`, `postgres_export/`, `object_store_export/`, `assets_manifest.json`, `manifest.json`.
- Git restore: `git push --mirror <target_url>` from `mirror.git/`; target URL from `BACKUP_RESTORE_GITLAB_URL`/token/prefix settings.
- PostgreSQL restore: run `psql -f {schema}_schema.sql` then `psql -f {schema}_data.sql` for each schema, using restore-target DB connection string.
- Object-store restore: create target bucket per client/space, `put_object` for each exported version using recorded SHA-256 as metadata.
- Closure verification: compare `assets_manifest.json` objects count/hashes, `metadata.json` tags count, `kb_ops_export.json` decisions count. Does not compare full content byte-by-byte.
- Integrity checker writes result to `integrity_report.json` inside package dir (read-only sidecar).

## Verification

**Commands:**
- `uv run pytest -q src/backup/tests` -- expected: all pass.
- `uv run ruff check src/backup` -- expected: clean.
- Live restore test skipped unless `RUN_LIVE_RESTORE_TESTS=1`.

## Review Triage Log

### 2026-11-10 — Initial draft
- (none)

### 2026-11-10 — Post-implementation review fixes
- `[high] [patch]` Restore now uses separate `BACKUP_RESTORE_POSTGRES_*` credentials instead of reusing the source backup PostgreSQL service.
- `[high] [patch]` `_target_exists` checks the GitLab default branch and PostgreSQL schemas; non-404 errors are no longer swallowed.
- `[high] [patch]` `BackupGitLabAdapter.push_mirror` no longer returns the token-embedded URL in its result dict.
- `[high] [patch]` `PostgresBackupService.count_decisions` parameterized `space_id` via psql variables and added `schemas_exist()`.
- `[high] [patch]` `verify-integrity` endpoint returns HTTP 409 on mismatch; restore aborts with HTTP 409 on integrity failure.
- `[medium] [patch]` `backup_id` sanitized to prevent filesystem traversal.
- `[medium] [patch]` Integrity/restore status sidecars moved outside the package directory.
- `[medium] [patch]` Object-store restore creates the target bucket and uses percent-encoded filenames.
- `[low] [patch]` `RestoreResponse`/`IntegrityResponse` schemas include `restored_at`/`checked_at`.
- `[low] [patch]` Sprint status corrected: D.4 is `in-progress`, duplicate D.4.x keys removed.

## Auto Run Result

- `uv run pytest -q src/backup/tests` — 51 passed, 1 skipped, 1 warning (Starlette deprecation).
- `uv run ruff check src/backup` — clean.
- `uv run pytest -q` — 307 passed, 5 skipped, 1 warning.
- Live restore tests skipped unless `RUN_LIVE_RESTORE_TESTS=1`.
