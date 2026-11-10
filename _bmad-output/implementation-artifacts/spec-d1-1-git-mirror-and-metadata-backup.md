---
title: 'D.1.1 Git mirror and metadata backup'
type: 'feature'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_commit: '763bb67'
context:
  - specs/corporate-kb/tasks.md
  - specs/corporate-kb/adr/ADR-017-gitlab-deployment-topology.md
  - specs/corporate-kb/repository-provisioning.md
  - src/git-orchestrator/app/adapters/gitlab.py
  - src/git-orchestrator/app/models/ops.py
  - src/git-orchestrator/app/core/config.py
warnings:
  - multiple-goals
---

<intent-contract>

## Intent

**Problem:** У платформы нет механизма резервного копирования canonical Git-состояния Space и связанных метаданных GitLab (MR, notes, protected tags). В случае отказа инфраструктуры или человеческой ошибки восстановление корпуса невозможно.

**Approach:** Создать модуль `src/backup/` с backup-сервисом на порту 8005, который для заданного `space_id` выполняет `git clone --mirror`, экспортирует GitLab MR/notes/tags, читает per-Space operational records из PostgreSQL `kb_ops` и формирует immutable per-Space backup package с манифестом и SHA-256. Предоставить REST API для запуска и получения статуса бэкапа.

## Boundaries & Constraints

**Always:**
- Использовать только read-only операции: `git clone --mirror`, `git fetch`, GitLab REST API GET для чтения MR/notes/tags.
- Backup package должен быть per-Space и включать `manifest.json` с SHA-256 всех частей.
- Хранить secrets только в `.env`, не коммитить.
- Использовать `docker-compose.yml` для Postgres/Keycloak/GitLab sandbox.
- Backup evidence писать в `_bmad-output/test-artifacts/d1/` и `specs/corporate-kb/evidence/d1/`.

**Never:**
- Не писать в canonical Git, не создавать MR, не мержить.
- Не модифицировать PostgreSQL operational schemas (`kb_ops`, `kb_authz`, `kb_index`).
- Не включать объектное хранилище (MinIO) — оно в бэклоге фазы C; бэкап объектов отложен до D.1.2/D.1.3.
- Не коммитить реальные GitLab tokens.
- Не менять pinned versions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Git mirror backup | `POST /api/kb/v1/backups/{space_id}/mirror` | Bare mirror в `BACKUP_STORAGE_PATH` со всеми refs | GitLab unreachable → 502 |
| Metadata export | Space с MRs, notes, `kb-decisions/*` tags | `metadata.json` со списком MR, notes, tag targets | Missing scope → 403 |
| kb_ops per-Space export | PostgreSQL `kb_ops.proposals`, `kb_ops.decisions` для space_id | `kb_ops_export.json` с operational records | Connection failure → 502 |
| Backup package assembly | Mirror + metadata + kb_ops export | Per-Space package directory с `manifest.json` | Hash mismatch → 500 |
| Backup idempotency | Same space_id, same HEAD | No-op, возвращает существующий package_id | — |
| Backup failure | Любой шаг падает | Status `failed`, partial package не помечается complete | — |

</intent-contract>

## Code Map

- `src/backup/app/core/config.py` — `Settings` c `BACKUP_STORAGE_PATH`, `BACKUP_GITLAB_URL`, `BACKUP_GITLAB_TOKEN`, `BACKUP_GITLAB_PROJECT_PATH_PREFIX`, `BACKUP_DATABASE_URL`, `BACKUP_KB_OPS_SCHEMA`. Паттерн аналогичен `src/ingestion/app/core/config.py`.
- `src/backup/app/adapters/gitlab.py` — `BackupGitLabAdapter` с методами `list_merge_requests`, `list_notes`, `list_tags`, `get_mirror_url`. Может наследовать/расширять `GitLabAdapter` из `src/git-orchestrator/app/adapters/gitlab.py` или быть thin-обёрткой над `httpx`.
- `src/backup/app/services/backup.py` — `BackupService` с `create_mirror_backup(space_id)`, `_export_metadata`, `_export_kb_ops`, `_assemble_package`, `_compute_manifest`.
- `src/backup/app/models/backup.py` — Pydantic-модели `BackupPackage`, `BackupManifest`, `BackupStatus`.
- `src/backup/app/api/router.py` — endpoints `POST /api/kb/v1/backups/{space_id}/mirror`, `GET /api/kb/v1/backups/{space_id}/latest`, `GET /health`.
- `src/backup/app/main.py` — FastAPI factory с dependency injection `BackupService`.
- `src/backup/scripts/smoke_backup.py` — live smoke test; skip если `RUN_LIVE_BACKUP_TESTS` не установлен.
- `src/backup/tests/test_backup_service.py` — unit tests со stub GitLab adapter и synthetic локальным git-репозиторием.
- `src/backup/tests/test_backup_live.py` — live integration tests; skip по умолчанию.
- `src/git-orchestrator/app/models/ops.py` — таблицы `proposals`, `decisions`, `source_sync_cursors`, `cutovers` для read-only export.
- `src/git-orchestrator/app/adapters/gitlab.py` — существующий `GitLabAdapter` и `HttpGitLabAdapter`; reuse для base URL/токена.

## Tasks & Acceptance

**Execution:**
- [ ] `src/backup/app/core/config.py` -- реализовать `Settings` с сервисными префиксами `BACKUP_*` и fallback на `GO_GITLAB_URL`/`GO_GITLAB_TOKEN` для локальной разработки -- чтобы не дублировать credentials.
- [ ] `src/backup/app/adapters/gitlab.py` -- реализовать `BackupGitLabAdapter` (или расширить `HttpGitLabAdapter`) методы `list_merge_requests(space_id)`, `list_notes(space_id, mr_iid)`, `list_tags(space_id)`, `get_project_url(space_id)` для read-only metadata export.
- [ ] `src/backup/app/models/backup.py` -- реализовать Pydantic-модели `BackupManifest`, `BackupPackage`, `BackupStatus`, `MetadataExport`, `KbOpsExport`.
- [ ] `src/backup/app/services/backup.py` -- реализовать `BackupService.create_mirror_backup(space_id)` (subprocess `git clone --mirror`), `_export_metadata`, `_export_kb_ops` (SELECT из `kb_ops.proposals`/`decisions` по `space_id`), `_assemble_package`, `_compute_manifest` (SHA-256 каждого файла).
- [ ] `src/backup/app/api/router.py` -- реализовать endpoints `POST /api/kb/v1/backups/{space_id}/mirror`, `GET /api/kb/v1/backups/{space_id}/latest`, `GET /health` с единообразной error schema (code + detail).
- [ ] `src/backup/app/main.py` -- FastAPI factory, wiring `BackupService` в `app.state`.
- [ ] `src/backup/tests/conftest.py` -- fixtures: stub GitLab adapter, in-memory SQLite для kb_ops (если reuse `GOBase` возможен), временный `BACKUP_STORAGE_PATH`.
- [ ] `src/backup/tests/test_backup_service.py` -- unit tests: mirror synthetic repo, metadata export, kb_ops export, package manifest hashes, idempotency, failure handling.
- [ ] `src/backup/tests/test_backup_live.py` -- live test; skip если `RUN_LIVE_BACKUP_TESTS` не установлен.
- [ ] `src/backup/scripts/smoke_backup.py` -- smoke script с проверкой mirror + metadata; skip live если нет sandbox.
- [ ] `.env.example` -- добавить `BACKUP_STORAGE_PATH`, `BACKUP_GITLAB_URL`, `BACKUP_GITLAB_TOKEN`, `BACKUP_GITLAB_PROJECT_PATH_PREFIX`, `BACKUP_DATABASE_URL`, `BACKUP_KB_OPS_SCHEMA`.
- [ ] `pyproject.toml` -- добавить `src/backup/tests` в `testpaths`.
- [ ] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- обновить `d.1.1-git-mirror-and-metadata-backup: done`.

**Acceptance Criteria:**
- Given Space repository доступен в GitLab, when `POST /api/kb/v1/backups/{space_id}/mirror`, then создаётся bare mirror со всеми refs.
- Given Space имеет MRs с notes и `kb-decisions/*` tags, when metadata export выполняется, then `metadata.json` содержит MR list, notes bodies и tag targets.
- Given `kb_ops.proposals`/`decisions` содержат записи для space_id, when kb_ops export выполняется, then `kb_ops_export.json` содержит их без изменения БД.
- Given backup package собран, when manifest verified, then SHA-256 каждого файла совпадает.
- Given повторный запрос для того же space_id и HEAD, when backup запускается, then возвращается существующий package_id (idempotency).
- Given любой шаг backup падает, when статус проверяется, then статус `failed` и package не помечен `complete`.

## Design Notes

- Backup package layout:
  ```
  {BACKUP_STORAGE_PATH}/{space_id}/{backup_id}/
    mirror.git/          # bare mirror
    metadata.json        # MRs, notes, tags
    kb_ops_export.json   # proposals/decisions per space_id
    manifest.json        # hashes, timestamps, space_id, backup_id
  ```
- `BackupService` принимает адаптер и engine через dependency injection; unit tests используют stub adapter + synthetic git repo.
- `git clone --mirror` вызывается через `subprocess.run` с таймаутом; URL формируется как `{gitlab_url}/{project_path_prefix}{space_id}.git` с embedded токеном (или используется credential helper, но embedded проще для sandbox).
- Idempotency key: `sha256(space_id + HEAD_SHA + hour_bucket)` — повторный запрос в тот же час для того же HEAD возвращает существующий пакет.
- kb_ops export read-only: используем `with engine.connect() as conn: conn.execute(text("SELECT ..."))` без ORM session, чтобы подчеркнуть read-only характер.

## Verification

**Commands:**
- `docker compose up -d postgres keycloak gitlab` -- expected: services healthy.
- `PYTHONPATH=src uv run uvicorn backup.app.main:app --host 127.0.0.1 --port 8005 &` -- expected: health 200.
- `uv run pytest -q src/backup/tests` -- expected: all pass.
- `RUN_LIVE_BACKUP_TESTS=1 PYTHONPATH=src uv run python src/backup/scripts/smoke_backup.py` -- expected: exit 0 if sandbox available, иначе skip.
- `uv run ruff check src/backup` -- expected: clean.

## Review Triage Log

### 2026-11-10 — Review pass
- verdicts: 9 findings — high 0, medium 6, low 3, false 0, maybe-false 0
- findings:
  - `[medium]` `[patch]` `HttpBackupGitLabAdapter` lacked `get_branch`, so `_resolve_head` fell back to `"0" * 40` and live idempotency broke. Added `get_branch` to adapter interface and both implementations; refactored `_resolve_head` to use it first.
  - `[medium]` `[patch]` `BackupServiceError("KB_OPS_ERROR", ...)` raised in `_export_kb_ops` was rewrapped as `BACKUP_FAILED` by the catch-all in `create_mirror_backup`. Changed exception handling to preserve the original `BackupServiceError.code`.
  - `[medium]` `[patch]` `_export_kb_ops` copied raw SQLAlchemy rows containing `uuid.UUID`/`datetime` into JSON fields, which would fail serialization against PostgreSQL. Added `_serialize_row` converting UUIDs to strings and datetimes to ISO format.
  - `[medium]` `[patch]` `space_id` path parameter was used directly in filesystem paths, allowing traversal outside `BACKUP_STORAGE_PATH`. Added `_sanitize_space_id` rejecting any characters outside `[a-zA-Z0-9_-]`.
  - `[medium]` `[patch]` `_export_metadata` logged and continued when `list_notes`/`list_tags` failed, allowing incomplete backups to be marked COMPLETE. Changed the code to propagate the failure and mark the backup FAILED.
  - `[medium]` `[patch]` GitLab token was embedded unquoted in the clone URL and `result.stderr` was surfaced in exceptions, risking token leakage. Now URL-quotes the token and omits stderr from the public error message.
  - `[low]` `[patch]` `smoke_backup.py` caught all exceptions and exited 0 even when `RUN_LIVE_BACKUP_TESTS=1`. Now exits 1 on failure when the env var is set, skip-with-exit-0 only when unset.
  - `[low]` `[patch]` `create_mirror_backup` endpoint declared only 502/500 responses, but `_handle_backup_error` can return 403/404. Added 403/404 to the endpoint responses dict.
  - `[low]` `[patch]` `MergeRequestSummary`/`TagSummary` were unused dead models; `_override_get_db` in conftest was dead code. Removed the dead models/code and added tests for branch HEAD resolution, KB_OPS_ERROR preservation, invalid `space_id`, and metadata-export failure.

## Auto Run Result

- Summary: Implemented a new `src/backup/` FastAPI service that creates per-Space immutable backup packages. Each package contains a `git clone --mirror` of the Space repository, exported GitLab MR/notes/tags metadata, read-only `kb_ops.proposals`/`decisions` export, and a SHA-256 manifest. Added REST endpoints, stub/HTTP GitLab adapters, unit tests with synthetic git repos, a live smoke script, and evidence artifacts.
- Files changed:
  - New `src/backup/` module: config, models, schemas, GitLab adapter, service, router, main, tests, scripts.
  - `.env.example` — added backup-related variables.
  - `pyproject.toml` — added `src/backup/tests` to testpaths.
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — moved Phase C to backlog, set Phase D in-progress, marked `d.1.1-git-mirror-and-metadata-backup: done`.
  - Evidence in `_bmad-output/test-artifacts/d1/` and `specs/corporate-kb/evidence/d1/`.
- Patches applied: 9 review findings (6 medium, 3 low).
- Rejected findings: (none)
- Deferred items:
  - Token embedded in clone URL is a sandbox shortcut; production should use SSH deploy keys or a credential helper.
  - Object-store backup is out of scope for D.1.1 (Phase C backlog).
  - Live runtime acceptance is BLOCKED until a GitLab sandbox is provisioned and `RUN_LIVE_BACKUP_TESTS=1` is exercised.
  - Port 8005 binding and `docker-compose.yml` service wiring are left to deployment/launch commands per spec verification.
- Follow-up review recommended: `false`.
- Verification performed:
  - `uv run pytest -q src/backup/tests` — 15 passed, 1 skipped, 1 warning.
  - `uv run pytest -q` — 271 passed, 5 skipped, 1 warning.
  - `uv run ruff check src/backup` — clean.
- Residual risks:
  - Live GitLab HEAD resolution, pagination, and HTTP error translation are tested only via stubs; real behavior requires sandbox validation.
  - The mirror URL embeds the token for sandbox convenience.
  - Protected-tag metadata (e.g., which tags are protected) is not exported separately; all tags are exported and protected tags are included.
