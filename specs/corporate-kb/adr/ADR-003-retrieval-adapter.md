# ADR-03 — Retrieval adapter

**ID/Title:** ADR-03 / Адаптер поиска и канонического чтения  
**Status:** **Proposed** до T00 audit существующего backend и ACL-aware recall benchmark; не является production approval.  
**Date:** 2026-11-06  
**Requirements/AD links:** R03, R04, R05, R11, R15, R16, R18; I03, I08–I12; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-4, AD-9, AD-13–AD-15; [spec.md](../spec.md): T00, T09, T10, T14, T19.

## Context

Сотрудник и агент должны получать exact/semantic retrieval по опубликованному корпусу, прямое чтение страницы или раздела и проверяемые citations. Индексированный текст не является оригиналом: выдача незакреплённого за `document_id` и revision SHA фрагмента может раскрыть отозванное, историческое или чужое содержимое. Фильтрация только после передачи chunks модели нарушает security boundary.

Существующий retrieval Open WebUI подлежит повторному использованию, но его реальные seams, backends, ACL semantics и SHA version mapping на выбранном commit ещё не исследованы. Качество ANN при ACL-фильтрации и русскоязычном корпусе нельзя выводить из общих бенчмарков. Кандидаты engine и модели не закреплены.

## Decision

1. Ввести тонкий **Retrieval adapter** между agent/UI и существующим retrieval/index backend. Adapter реализует единый порт exact/semantic search с явными `space`, `scope`, `mode`, bounded cursor/result limits и server-issued `AuthzContext`.
2. Search result содержит ссылки `document_id`, `document_revision_sha`, section/range и snapshot metadata, а не самостоятельную user-editable копию документа. Для содержательного ответа selected revision читается из канонического Git через GO; direct read поддерживает whole/section, bounds, cursor и явный `truncation`.
3. Индексируются только eligible paths активированного published `main`. Pending/rejected proposals, `inbox`, templates, служебные файлы и непроверенные critical media исключаются. Inactive cutover preflight не обслуживает retrieval.
4. Авторизация выполняется на сервере **до exposure** tree/titles/snippets/chunks/files/history/export и до формирования provider/LLM payload. Поле `access` во front matter не является самостоятельным источником прав. Отзыв ACL не ждёт переиндексации.
5. Candidate с устаревшим `revision_sha` отклоняется по stale policy; adapter повторно авторизует итоговый payload. Историческое содержимое не подставляется молча вместо текущего. Любой explicit historical read имеет отдельную авторизацию и маркировку revision.
6. Scopes page/subtree/Space/разрешённые Spaces вычисляются сервером. `actor`, `groups`, `tenant` и scope из аргументов модели не принимаются как доверенные.
7. Сначала аудируется и переиспользуется существующий backend. **Proposed для отдельного решения после benchmark:** pgvector + FTS; HNSW/IVFFlat, partitioning, iterative/exact fallback, гибридный retrieval и reranking выбираются только по ACL-aware recall, качеству citations, latency и стоимости на согласованном corpus. OpenSearch требует измеренной необходимости и отдельного ADR.
8. Embedding/chunking/profile version управляется ADR-05. Смена engine или profile не переписывает канон и не выполняет destructive live rebuild.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Прямые вызовы существующего retrieval из агента | Меньше кода, но разъезжаются ACL, SHA и stale semantics | Отклонено; нужен единый enforcement seam |
| Только direct read без retrieval | Простой канон, но не выполняет corpus search R04 | Отклонено; direct read дополняет поиск |
| Выдача chunks напрямую модели | Быстрее, но риск stale/disclosure и слабые citations | Отклонено |
| Немедленный выбор pgvector/FTS и ANN-параметров | Меньше аудита, но неизвестны filtered recall и upgrade cost | Отложено до T00/T19 benchmark |
| OpenSearch как обязательный backend | Дополнительный сервис и эксплуатационная сложность без доказанной необходимости | Вне MVP; отдельный ADR |

## Consequences

### Positive

- Один контур применяет ACL, revision и truncation для UI и tools.
- Канон остаётся в Git; retrieval rebuildable и не становится второй записываемой базой.
- Engine можно заменить без изменения document lifecycle и агентного contract.
- Citations привязаны к проверяемой странице, revision и разделу.

### Negative

- Повторное чтение Git и авторизация добавляют latency и нагрузку.
- Stale candidates могут уменьшать заполненность выдачи до завершения reconciliation.
- Требуется согласование upstream grants, index metadata и AuthzContext.

### Cost

- Нужны adapter, integration tests, ACL-aware benchmark и golden set с русскими документами.
- Каждый дополнительный engine/profile увеличивает стоимость migration, shadow evaluation и эксплуатации; численные бюджеты пока не утверждены.

## Verification / T00 evidence

- **T00:** закрепить baseline и дать code references существующего retrieval, grants, direct-read/extraction и adapter seams. Подтвердить либо зафиксировать пробел в exact-SHA/version mapping и ACL filtering.
- **T00/T19:** на synthetic и согласованном sanitized corpus сравнить candidate engines по exact/semantic recall под реальными Space/subtree ACL, включая русские слова, кириллические пути, повторные headings и длинные страницы. Пороги не выдумывать; результаты и конфигурацию сохранить как sanitized evidence.
- Детерминированно проверить: cross-Space IDOR; отсутствие private snippets/chunks/files/history в payload; pending/rejected/`inbox` exclusion; stale revision rejection; revoke до переиндексации; late index job; explicit truncation и citation revision.
- Проверить критические/рукописные media: без ручной транскрипции/сверки они не попадают в выдачу; автоматические описания помечены и ссылаются на оригинал.
- **Текущее состояние:** backend audit и benchmark не выполнялись; конкретный engine не утверждён, integration PASS отсутствует.

## Related contracts

- Logical tools: `search_documents`, `read_document`, `list_documents`, `get_document_links`; typed bounded schemas и error codes из spec.
- `AuthzContext`, Space/path scopes, anti-enumeration `NOT_FOUND`, stale/conflict errors и `/api/kb/v1` versioning.
- `index-snapshot-v1`: `snapshot_sha`, `document_revision_sha`, blob/content hash, dependency hash, generation/profile metadata.
- Canonical Git read через GO; rebuildable `kb_index`; approved provider/egress profile.
- [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-05](ADR-005-index-delivery.md), [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-10](ADR-010-ldap-oidc-identity.md), [ADR-16](ADR-016-repository-per-space.md).
