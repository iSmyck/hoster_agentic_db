# Epic KBI.4 Context: Content-standard enforcement and job queue

## Goal

Перед любым canonical write (GO proposal/merge) проверить front-matter-v2 и data barrier. Ingestion jobs ретраятся с backoff и уходят в DLQ с sanitised reason. Метрики очереди наблюдаемы.

## Stories

- Story KBI.4.1: Front-matter-v2 validator
- Story KBI.4.2: Data barrier gate
- Story KBI.4.3: Job queue with retry and DLQ

## Requirements & Constraints

`additionalProperties` и ключ `access` (также `owner`/`status`) → `FRONT_MATTER_INVALID`. `source_managed` без `origin` → `ORIGIN_REQUIRED`. `archived=true` xor `archive` → `ARCHIVE_INVARIANT_VIOLATION`. Data profile `strict` / `pii_permitted`; synthetic PII canaries only. `pii_permitted` без `legal_basis` → `LEGAL_BASIS_REQUIRED`. External provider при PII → `EGRESS_FORBIDDEN`.

PostgreSQL product schema не расширяем (AGENTS.md, ADR-015): durable jobs принадлежат GO/`kb_ops`. Здесь — in-memory queue с той же семантикой (retry, DLQ, metrics). Live PostgreSQL BLOCKED.

## Technical Decisions

HTTP: `POST /validate/front-matter`, `POST /validate/data-barrier`, `POST /jobs`, `POST /jobs/tick`, `GET /jobs/metrics`. Convert/run и source-sync вызывают те же validators до GO. PII в convert даёт `status=blocked` + correction task, не canonical write.

## Implementation result (2026-11-17)

Synthetic VERIFIED: specs `spec-kbi-4-1`…`4-3` done; `uv run pytest -q src/kb-ingestion/tests` → 186 passed; ruff clean. Live PostgreSQL/GO/hoster.ai not claimed.

## Cross-Story Dependencies

KBI.1 draft generator и KBI.2.4 submit уже зовут jsonschema; 4.1 добавляет archive/origin mapping. KBI.3 `data_profile` начинает enforcement. KBI.5 не трогаем.
