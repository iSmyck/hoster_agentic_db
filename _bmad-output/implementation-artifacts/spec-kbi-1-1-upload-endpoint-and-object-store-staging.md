---
title: 'KBI.1.1 Upload endpoint and object-store staging'
type: 'feature'
created: '2026-11-16'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '1be726da0115f325bc2afe8be9e4124894b18cfb'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-1-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет входа, куда n8n отдаёт один файл. Без staging с `object_id`, `sha256`, `version_id`, `size` и `media_type` конвертацию не к чему привязать.

**Approach:** `POST /api/kb/v1/ingest/convert` в новом `src/kb-ingestion` проверяет профиль и размер до записи и кладёт сырые байты в бакет `kb-ingest`. Парсеры и Git — не эта стори.

## Boundaries & Constraints

**Always:**
- Форма: `space_id`, `client_id`, `data_profile`, `file`. `legal_basis` обязателен только при `pii_permitted`.
- Профиль только `strict` или `pii_permitted`. Иначе 400 `INVALID_DATA_PROFILE`.
- `pii_permitted` без непустого `legal_basis` → 400 `LEGAL_BASIS_REQUIRED`, put не вызывается.
- Размер > 104857600 → 413 `SIZE_LIMIT_EXCEEDED`, put не вызывается. Ровно 100 МиБ допустим.
- Id непустые и `^[a-zA-Z0-9_/-]+$`, иначе 400 `INVALID_SPACE_ID` / `INVALID_CLIENT_ID`.
- Нет part `file` → 422 `MISSING_FILE`.
- 201: `object_id` (uuid hex, без имени файла), `sha256`, `version_id`, `size`, `media_type`.
- Ошибки: `{"code","message"}`. Пустой Content-Type → `application/octet-stream`.
- Ключ `{space_id}/{client_id}/{object_id}`. Метаданные `sha256`, `media_type`. Без секретов — in-memory stub.

**Never:**
- Не менять backup, ingestion, git-orchestrator, retrieval, session, `scripts/local_stack.py`.
- Не писать в `kb-backups` и не импортировать адаптер backup.
- Не парсить файл, не строить Markdown, front matter, dry-run и не писать в Git.
- Не добавлять auth.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| strict | валидные id, файл ≤ лимита | 201, байты и sha256 в stub | N/A |
| pii ok | `pii_permitted` + `legal_basis` | 201 | N/A |
| pii blocked | `pii_permitted`, basis пуст | put не вызван | 400 `LEGAL_BASIS_REQUIRED` |
| oversize | 104857601 байт | put не вызван | 413 `SIZE_LIMIT_EXCEEDED` |
| exact limit | 104857600 байт | 201 | N/A |
| bad profile | `data_profile=open` | put не вызван | 400 `INVALID_DATA_PROFILE` |
| bad id | пустой или `../x` | put не вызван | 400 `INVALID_SPACE_ID` или `INVALID_CLIENT_ID` |
| no file | нет part `file` | put не вызван | 422 `MISSING_FILE` |
| media type | `Content-Type: application/pdf` | `media_type=application/pdf` | пустой заголовок → `application/octet-stream` |

</frozen-after-approval>

## Code Map

- `src/ingestion/app/main.py` — образец `create_app` и `app.state`. Не менять.
- `src/ingestion/app/api/router.py` — образец `{"code","message"}`. Не менять.
- `src/backup/app/adapters/object_store.py` — metadata `sha256` и version. Не импортировать.
- `src/backup/app/api/router.py:27` — regex id. Их код размера `UPLOAD_TOO_LARGE` не копировать.
- `src/backup/app/services/object_store.py:117` — id с именем файла. Здесь uuid hex.
- `pyproject.toml:33` — добавить только `src/kb-ingestion/tests` в `testpaths`.

## Tasks & Acceptance

**Execution:**
- [x] `src/kb-ingestion/app/adapters/object_store.py` -- put/get и in-memory stub -- тесты без MinIO
- [x] `src/kb-ingestion/app/core/config.py` -- лимит и бакет `kb-ingest` -- без секретов по умолчанию
- [x] `src/kb-ingestion/app/services/staging.py` -- отказы до put, непрозрачный id -- AC
- [x] `src/kb-ingestion/app/api/router.py` -- POST convert и GET `/health` -- контракт
- [x] `src/kb-ingestion/app/main.py` -- `create_app(object_store=...)` -- подмена stub
- [x] `src/kb-ingestion/tests/test_convert_upload.py` -- вся матрица -- отказы не пишут объект
- [x] `pyproject.toml` -- testpaths -- pytest видит пакет

**Acceptance Criteria:**
- Given валидная форма, when POST convert, then ответ содержит пять полей staging, и байты читаются из stub по `object_id`.
- Given отказ до staging, when POST convert, then stub пуст.

## Implementation Notes

- Сервис `src/kb-ingestion/`, alias импорта `kb_ingestion` в тестах (каталог с дефисом).
- `validate_metadata()` вызывается до чтения тела upload.
- MinIO-адаптер и `local_stack` закрыты в KBI-901/905 (synthetic; live MinIO ACL BLOCKED).

## Spec Change Log

## Review Triage Log

| Finding | Verdict | Evidence / route |
|--------|---------|------------------|
| Чтение тела до валидации metadata | high → fixed | patch: `validate_metadata` перед `read` |
| Дубль size-check router + service | low → fixed | patch: только `StagingService._validate_size` |
| MinIO/bucket не подключён | false | spec: stub без секретов в KBI.1.1 |
| `ObjectStoreError` не используется | defer | KBI-102 / real adapter |
| Тест 100 МиБ тяжёлый | low → accept | один матричный кейс, редкий в CI |
| party-mode в diff | false | untracked, не в коммите |
| edge-case / verification layers | — | subagent 403; повтор в сессии — ниже |
| 2026-11-17 manual edge-case | low → accept | `ObjectStoreError`/IO на put — defer KBI-102; 0-byte upload — допустим |
| 2026-11-17 manual edge-case | patch | whitespace `legal_basis` — тест добавлен |
| 2026-11-17 manual verification-gap | defer | `run_service` без kb-ingestion — KBI-905; матрица покрыта pytest |
| 2026-11-17 manual verification-gap | low → accept | полный `pytest` root — вне scope стори |

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_convert_upload.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
