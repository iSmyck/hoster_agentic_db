# ADR-05 — Index delivery

**ID/Title:** ADR-05 / Доставка, версионирование и активация производного индекса  
**Status:** **Proposed** для G0; протокол подлежит T00 design validation, а engine specifics — **Proposed** до audit/benchmark. Не является production approval.  
**Date:** 2026-11-06  
**Requirements/AD links:** R04, R05, R11, R13, R18; I08–I11, I13, I14; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-3, AD-4, AD-9, AD-15, AD-16; [spec.md](../spec.md): T10, T12, T14, T19.

## Context

Webhooks могут теряться, дублироваться и приходить не по порядку; CI jobs завершаются после новых merges. Простое сравнение или сортировка SHA не устанавливает новизну revision. Индекс должен быть асинхронным и пересобираемым, но late job не вправе вернуть старый corpus в active search, а pending/rejected content не должен стать публичным через поиск.

ACL и attachments изменяются не только через document push. Кроме того, incremental index может отличаться от полного snapshot из-за зависимых ссылок, assets и extraction. Нужен протокол доставки, который допускает at-least-once events без потери correctness.

## Decision

1. GO принимает GitLab, AuthZ и attachment events, нормализует их и инициирует `IndexRequested` с exact SHA. **CI/index workers владеют index runs** и являются единственными writers `kb_index` и active index pointer.
2. Источник индекса — eligible corpus активированного published `main`; единственное исключение — inactive cutover preflight на exact `cutover_sha` по ADR-11. Preflight никогда не обслуживает retrieval до активации Space.
3. Обработка at-least-once, идемпотентная, с bounded retry, dead-letter/error state и периодической reconciliation `HEAD main vs index`. Потерянное событие обнаруживается догоняющим run; broker не добавляется без измеренной необходимости.
4. Только CI/index writer продвигает active pointer после полного успешного run. Публикация сериализуется **per `(space_id,profile_id)` across all generations** и атомарно выполняет CAS по expected current pointer/publication fence + latest Git ancestry + exact validated run/snapshot. Per-generation lock alone недостаточен: concurrent old/new publishers используют один Space/profile lock, stale owner обновляет ноль rows. Late/stale run не может перезаписать более новый active snapshot.
5. `main_generation` определяется **Git ancestry**, не лексикографической сортировкой SHA. History rewrite создаёт новую generation и требует full rebuild. `index_profile_version` отдельно версионирует embedding/chunking/extraction dependencies; смена профиля создаёт новый индекс без destructive live rebuild.
6. Контракт `index-snapshot-v1` различает `snapshot_sha`, `document_revision_sha`, blob/content hash и dependency hash. Incremental `ready/active` требует nonempty `closure.equivalence_evidence` для distinct full run+snapshot в conclusive canonical `ready/active` с `validated_at`, complete closure, `missing_inputs=[]`, exact+semantic hashes и совпадением perimeter/main SHA/generation/profile/closure hash. Requested/failed/empty prerequisite запрещён; при несовпадении выполняется full run.
7. В индекс попадают только eligible paths. `inbox`, templates, служебные файлы, pending/rejected и непроверенные critical media исключаются. Archive/delete убирает содержимое из нового snapshot; retrieval не ждёт этой работы для отзыва доступа.
8. Retrieval повторно авторизует payload и отклоняет stale `revision_sha` по ADR-03. UI различает published/indexed/pending/failed без превращения DB status в канон.
9. Выбор pgvector/FTS, ANN algorithm, partitioning, exact fallback, embedding/chunking/reranking и их параметров не закреплён: **Proposed до T00 audit и ACL-aware benchmark**.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Только webhooks без reconciliation | Меньше фоновой работы, но потерянное событие оставляет бессрочный drift | Отклонено |
| Синхронная индексация в merge | Простая видимость, но CI задерживает/блокирует canonical merge | Отклонено; индекс отделён |
| Active pointer пишет каждый worker без сериализации | Высокий параллелизм, но late job может активировать старый SHA | Отклонено |
| Сортировка commit SHA для freshness | Простое сравнение, но не отражает ancestry | Запрещено |
| Всегда full rebuild | Проще closure, но стоимость и lag растут с корпусом | Допускается только proven-equivalent incremental |
| Отдельный broker как обязательный компонент | Дополнительная инфраструктура до доказанной потребности | Не требуется MVP |

## Consequences

### Positive

- Duplicate/loss/reordering events не меняют канон и обнаруживаются reconciliation.
- Snapshot/generation/profile делают выдачу объяснимой и воспроизводимой.
- Можно безопасно вводить новый engine/profile через неактивный индекс.
- Полный rebuild из Git устраняет database drift.

### Negative

- Published и indexed состояния расходятся на время обработки.
- Dependency closure усложняет incremental indexing и evidence.
- Recovery после history rewrite требует полного rebuild и координации mirrors/retention.

### Cost

- Нужны CI orchestration, dead-letter handling, reconciliation, metrics и snapshot storage.
- Full/shadow rebuilds потребляют вычислительные и storage resources; freshness и бюджеты согласуются отдельно, без выдуманных SLO.

## Verification / T00 evidence

- **T00:** подтвердить существующий CI/index path, webhook/AuthZ/attachment seams, exact-SHA reads, schema writer roles и возможность восстановить active snapshot из Git.
- Integration tests: duplicate/out-of-order/lost webhook; bounded retry и dead-letter; CI outage; restart между run и pointer promotion; late old job; concurrent runs per Space; periodic reconciliation.
- Проверить archive/delete, ACL revocation до переиндексации, AttachmentChanged, исключение open/rejected MR и служебных paths.
- Сравнить incremental snapshot с full snapshot на одинаковом `main_sha`, включая links/assets/dependencies; history rewrite должен создать новую generation.
- Полный rebuild на clean `kb_index`; preflight недоступен retrieval до activation; sanitized evidence фиксирует corpus SHA, config/profile и результаты.
- **Текущее состояние:** реальные GitLab/CI проверки и benchmark не выполнялись; engine не выбран.

## Related contracts

- `IndexRequested` exact SHA, `AccessPolicyChanged`, `AttachmentChanged`, GitLab push/merge/archive events.
- `index-snapshot-v1`, index run/dead-letter metadata, active pointer, `main_generation`, `index_profile_version`.
- `kb_index` single-writer contract; GO webhook ingestion; Retrieval adapter stale/ACL recheck.
- Cutover preflight и Space activation; UI published/indexed/failed states.
- [ADR-03](ADR-003-retrieval-adapter.md), [ADR-06](ADR-006-portability-retention.md), [ADR-11](ADR-011-two-phase-publication.md), [ADR-15](ADR-015-postgresql-schema-ownership.md), [ADR-16](ADR-016-repository-per-space.md).
