# ADR-18 — Source-sync auto-merge policy

**ID/Title:** ADR-18 / Политика auto-merge для source-sync  
**Status:** **Accepted by project owner 2026-11-14**; реализация зависит от результатов T00/G0 и последующих gates. Не разрешает production migration, corpus load или rollout без отдельных owner approvals.  
**Date:** 2026-11-14  
**Requirements/AD links:** R06, R07, R12, R13, R16, R18; I01, I02, I06, I14; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-1–AD-3, AD-9, AD-13, AD-16; [content-standard.md](../content-standard.md): части A–C; [spec.md](../spec.md): T12, T15, T16; [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-11](ADR-011-two-phase-publication.md).  
**Amends:** ADR-04, ADR-11 — запрет auto-merge после cutover для source-managed детерминированной синхронизации.

## Context

Первоначальные решения ADR-04/ADR-11 запрещали auto-merge для всех managed changes после cutover, включая source-managed синхронизацию. Это устраняло риск silent content drift, но создавало operational bottleneck: каждое delta-обновление из SharePoint/FTP/GitLab требовало human DecisionRecord, даже для тривиальных изменений.

Owner пересмотрел требование: continuous source-sync должен поддерживать **configurable auto-merge** для trusted sources. Бюрократия per-update review признана избыточной для сценариев, где источник является authoritative system of record, а специалисты валидируют финальную базу периодически, а не каждый diff.

Решение не отменяет human review для `curated` документов, начальной структуризации KB (`structure`) или untrusted sources.

## Decision

### 1. Per-source auto-merge configuration

Каждый source в `kb-ingestion` имеет конфигурацию:

- `validation_required: boolean` — обязателен human DecisionRecord перед merge.
- `auto_merge: boolean` — разрешён auto-merge без human DecisionRecord.
- `trusted: boolean` — источник является authoritative system of record.

**Инвариант:** `auto_merge=true` допустимо только при `trusted=true`. Иначе registration/sync отклоняется с `AUTO_MERGE_REQUIRES_TRUSTED`.

### 2. Условия auto-merge

GO выполняет auto-merge для source-sync proposal только если **все** условия выполнены:

1. `source.trusted = true` и `source.auto_merge = true`.
2. `source.validation_required = false`.
3. Target document имеет `ownership_mode = source_managed` или `migrated`.
4. Diff удовлетворяет bounded policy:
   - не более `max_files_per_sync` изменённых файлов;
   - не более `max_lines_changed` строк;
   - нет изменений в `front-matter` `access`/`owner`/`status` (запрещённые ключи);
   - нет удаления документа без явного `tombstone` record.
5. Content-standard enforcement пройден: front-matter-v2 valid, data barrier пройден, critical media либо отсутствует, либо `verification_status=verified`.
6. Нет конфликта с `curated` правками: three-way merge не требует human resolution.
7. GO merge service identity имеет техническую возможность merge; proposal создан через GO API с корректным `origin` record.

### 3. Audit, notification и rollback

- Каждый auto-merge создаёт DecisionRecord с `actor_type=source_sync`, `decision=accepted`, `rationale="auto-merge per source policy"`.
- Merge commit содержит standard Decision trailers и ссылку на `source_id`, `source_version`, `sync_run_id`.
- Editors, подписанные на изменённый path, получают notification после proven merge.
- Rollback выполняется через revert-MR/new commit; auto-merge не исключает recovery barrier.
- Все auto-merges попадают в audit log и доступны для reconciliation.

### 4. Fallback to human review

Auto-merge отклоняется и переводится в MR + human review при:

- Любом нарушении условий из §2.
- `CONFLICT_WITH_CURATED` — source update пересекается с незаmerged curated proposal.
- `POLICY_BUNDLE_MISMATCH` — access/approval policy revision изменилась между proposal и merge.
- `BOUND_EXCEEDED` — diff превышает настроенные лимиты.

### 5. Запреты

- Auto-merge запрещён для `curated` документов.
- Auto-merge запрещён для начальной `structure` фазы.
- Auto-merge запрещён для untrusted sources.
- Auto-merge не применяется к `live_operational` typed read-only bindings.
- Auto-merge не отменяет MR creation: proposal/MR создаётся всегда для audit trail, даже если merge выполняется автоматически.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Human review для всех source updates | Максимальный контроль, но operational bottleneck и бюрократия | Отклонено owner |
| Auto-merge для всех sources | Минимум работы, но риск silent drift от untrusted sources | Отклонено; только trusted |
| Auto-merge без bounded diff | Простая реализация, но риск массовых нежелательных изменений | Отклонено; bounds обязательны |
| Auto-merge без DecisionRecord | Меньше записей, но нарушает audit trail и R07/R08 | Отклонено; DecisionRecord обязателен |
| Periodic batch review вместо auto-merge | Меньше MR, но задержка обновлений и сложность batching | Не выбрано |

## Consequences

### Positive

- Trusted source-sync обновляет KB без per-update бюрократии.
- Audit trail и rollback сохраняются через DecisionRecord/MR/trailers.
- Curated контент и начальная структуризация остаются под human control.
- Bounded diff ограничивает blast radius ошибочного source update.

### Negative

- Trusted source может внести нежелательные изменения без immediate human review.
- Требуется дополнительная policy engine, notification и audit instrumentation.
- Необходим мониторинг auto-merge quality и periodic reconciliation.

### Cost

- Реализация policy engine, source config schema, notification service, bounded diff checker.
- Operational work: настройка trusted sources, мониторинг auto-merge, periodic review.
- Сроки и бюджет не оцениваются этим ADR.

## Verification

- **Policy gate tests:** source с `auto_merge=true` и `trusted=false` отклоняется.
- **Bounded diff tests:** diff сверх лимита переводится в human review.
- **Curated protection:** auto-merge для `curated` документа отклоняется.
- **Audit tests:** каждый auto-merge создаёт DecisionRecord с `actor_type=source_sync` и корректными trailers.
- **Notification tests:** editor получает notification после proven auto-merge.
- **Rollback tests:** revert-MR после auto-merge восстанавливает предыдущее состояние.
- **Fallback tests:** `CONFLICT_WITH_CURATED`, `POLICY_BUNDLE_MISMATCH`, `BOUND_EXCEEDED` переводят в human review.
- **Live sandbox:** проверить на synthetic source, что auto-merge проходит end-to-end без human DecisionRecord и не оставляет recovery barrier.

## Related contracts

- Source registry config: `source_type`, `source_ref`, `trusted`, `auto_merge`, `validation_required`, `poll_interval`, bounds.
- `ProposalRecord` / `DecisionRecord` с `actor_type=source_sync`.
- `origin` record (`source-origin-v1`) с `source_id`, `source_version`, `source_content_sha256`.
- Merge trailers: `Source-Sync-Id`, `Source-Version`, `Sync-Run-Id`.
- Notification subscription: `editor_stable_id`, `space_id`, `path`, `channel`.
- [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-11](ADR-011-two-phase-publication.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-13](ADR-013-merge-serialization-recovery.md), [ADR-14](ADR-014-canonical-decision-record.md), [ADR-15](ADR-015-postgresql-schema-ownership.md), [ADR-16](ADR-016-repository-per-space.md).
