# Epic KBI.3 Context: Source-sync

## Goal

Отслеживать источники и обновлять KB по delta документов с configurable validation/auto-merge (ADR-018). Credentials живут в n8n/vault; модуль принимает uniform delta.

## Stories

- Story KBI.3.1: Source registry and configuration
- Story KBI.3.2: Delta detection and cursor management
- Story KBI.3.3: Auto-merge policy engine
- Story KBI.3.4: Notification on merge
- Story KBI.3.5: Scheduler / poller

## Requirements & Constraints

Нет source-specific connectors (SharePoint/FTP). `credentials_ref` — ссылка, не секрет. `auto_merge=true` только при `trusted=true`. Auto-merge запрещён для `curated`, `structure`, untrusted. Bounded diff: `max_files_per_sync`, `max_lines_changed`. DecisionRecord auto-merge: `actor_type=source_sync`. PostgreSQL queue — KBI.4; persistence здесь in-memory (как KBI.1/2). Live GitLab не заявляется.

## Technical Decisions

Uniform `POST /sources/{id}/sync` с документами `{source_object_id, source_version, sha256, path, action}`. Cursor в модуле; GO stub для proposal/merge/decision. Scheduler ставит job по `poll_interval`, overlap дедуплицируется.

## Implementation result (2026-11-17)

Synthetic VERIFIED: specs `spec-kbi-3-1`…`3-5` done; `uv run pytest -q src/kb-ingestion/tests` → 165 passed; ruff clean. Live GO/GitLab/n8n not claimed. Deferred to KBI.4: content-standard / FM keys / `CONFLICT_WITH_CURATED` / durable queue+cursor.

## Cross-Story Dependencies

KBI.2 GO client расширяется (submit + auto-merge decision). KBI.1 convert не вызывается из sync в этой фазе: delta уже нормализована n8n.
