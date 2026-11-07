# ADR-15 — PostgreSQL schema ownership

**ID/Title:** ADR-15 / Единственный writer каждой PostgreSQL-схемы  
**Status:** **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00**. Один PostgreSQL instance на клиента — DESIGN assumption, подлежащая подтверждению на pinned upstream deployment; не production approval.  
**Date:** 2026-11-06  
**Requirements/AD links:** R04, R05, R07–R11, R14, R17, R18; I07–I11; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-2, AD-4, AD-7–AD-9, AD-11, AD-12; [spec.md](../spec.md): T00, T03, T05, T10, T18.

## Context

Open WebUI, Identity/AuthZ adapter, GO и indexer имеют разные lifecycle и rebuild semantics. Shared-table writes и чужие migrations создают неопределённое владение, усложняют upstream upgrades и делают rebuild опасным. Один dedicated instance удобен эксплуатационно, но не должен означать общий privileged DB user или отсутствие component boundaries.

Canonical documents/proposals/decisions находятся в GitLab. Поэтому потеря projection не должна превращаться в потерю канона, а попытка другого компонента исправить чужую таблицу не должна становиться скрытым командным API.

## Decision

1. Для каждого клиента используется **один dedicated PostgreSQL instance**, содержащий upstream-owned tables и независимые `kb_authz`, `kb_ops`, `kb_index` со отдельными DB roles. Instance не делится между клиентами. Физическая совместимость с pinned upstream проверяется T00.
2. Владение и единственный writer:

| Схема / данные | Единственный writer и migration owner | Разрешённый доступ других компонентов |
|---|---|---|
| `upstream` / upstream-owned tables | Open WebUI upstream components и upstream migrations | Продуктовые компоненты используют supported upstream seams, не произвольные shared writes |
| Managed upstream grants | Только Identity/AuthZ adapter в рамках upstream grant semantics | Остальные читают эффект через AuthZ/upstream contracts |
| `kb_authz` | Только Identity/AuthZ adapter | Server-side AuthZ read contracts; никаких writes от GO/UI/agent |
| `kb_ops` | Только GO | Status/query contracts; reconciliation и rebuild выполняет GO |
| `kb_index` | Только CI/index workers | Retrieval read-only; GO не пишет index tables/pointer |

3. Межкомпонентный доступ осуществляется через versioned contracts/API/events, а не shared-table mutation. Отсутствие права записи проверяется DB role, а не только дисциплиной кода.
4. Upstream migrations **не переносятся** в продуктовые schemas и не переписываются fork. Каждый owning component версионирует, выполняет и откатывает собственные migrations в пределах его upstream/deployment conventions.
5. `kb_authz` хранит group snapshots/managed grant projections; источник — Git policy + IdP. `kb_ops` хранит proposal/decision/operation/webhook/source-sync projections и durable recovery barriers; canonical outcome — Git. `kb_index` хранит documents/chunks/embeddings/attachments/index runs как rebuildable projection Git + immutable assets.
6. Durable `recovery_required` и fencing metadata в `kb_ops` являются operational safety state, а не canonical DecisionRecord. При rebuild нельзя потерять или молча очистить неизвестный merge outcome: применяется quarantine/reconciliation ADR-13/ADR-14.
7. Retrieval имеет только необходимый read access к `kb_index` и не получает writer role. Agent, browser, connector и CI не имеют доступа к merge credential; DB credentials выдаются по least privilege и не помещаются в logs/export.
8. Credentials и bind secrets принадлежат deployment secret mechanism, а не продуктовым tables. Raw private content в logs/audit/unapproved export не записывается.
9. Один instance не создаёт общий multi-tenant canonical store. При невозможности безопасно совместить upstream и продуктовые ownership/migrations требуется G0 design review выбранного физического разделения, а не скрытое ослабление single-writer rule.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Одна общая schema и DB superuser | Простой старт, но непредсказуемые writes/migrations и большой blast radius | Отклонено |
| Отдельный PostgreSQL instance каждому компоненту | Сильнее физическая изоляция, но больше эксплуатационная стоимость | Не default; возможен пересмотр при T00 stop condition |
| GO пишет index status напрямую | Удобный workflow, но два writers и гонки active pointer | Запрещено |
| Retrieval обновляет own cache в `kb_index` | Локально удобно, но нарушает rebuild/single-writer semantics | Запрещено |
| Копировать upstream migrations в fork | Видимость контроля, но upgrade drift и двойное владение | Запрещено |
| DB как canonical decision store | Простые транзакции, но противоречит ADR-08/14 и Git export | Отклонено |

## Consequences

### Positive

- Однозначный migration owner и writer для каждой схемы.
- DB roles дают проверяемую защиту от cross-component writes.
- Upstream upgrades отделены от продуктовых migrations.
- Projections можно удалять/пересобирать без изменения Git канона, с сохранением recovery safety semantics.

### Negative

- Межкомпонентные запросы требуют contracts вместо ad-hoc joins/writes.
- Несколько roles/migration pipelines усложняют deployment.
- Operational recovery barrier требует отдельной сохранности даже при rebuild disposable projections.

### Cost

- Нужны role/migration automation, ownership tests и contract-level integration.
- Dedicated instance, backup/restore и rebuild drills требуются для каждого клиента; физическая альтернатива оценивается только при доказанной несовместимости.

## Verification / T00 evidence

- **T00:** на pinned upstream deployment подтвердить фактические schema/migration conventions, возможность отдельных roles и supported grant seams. Сохранить code references; до проверки один instance остаётся ASSUMPTION.
- Негативные DB tests: Identity adapter не пишет `kb_ops`/`kb_index`; GO не пишет `kb_authz`/`kb_index`/произвольные upstream tables; indexer пишет только `kb_index`; retrieval read-only; unmanaged component не меняет upstream grants.
- Migration test каждого owner на synthetic instance: повтор/upgrade/rollback по поддерживаемой процедуре, отсутствие скопированных upstream migrations и чужих DDL writers.
- Rebuild tests: `kb_index` из Git + assets; `kb_ops` Git-derived state из notes/tags/merges; `kb_authz` из Git policy + IdP. Unknown merge recovery остаётся blocked до reconciliation.
- Restore/upgrade drill подтверждает, что secrets отсутствуют в tables/logs/evidence, а client instances изолированы.
- **Текущее состояние:** migrations не запускались, baseline и DB integration evidence отсутствуют.

## Related contracts

- DB role/writer matrix и per-component migration ownership.
- `kb_authz`: group snapshots/managed grants; `kb_ops`: operations/decisions/webhooks/source-sync/recovery; `kb_index`: snapshots/chunks/embeddings/attachments/runs.
- Identity/AuthZ, GO и CI/index APIs/events; Retrieval read-only contract.
- Backup/rebuild/restore procedures и decision recovery barrier.
- [ADR-03](ADR-003-retrieval-adapter.md), [ADR-05](ADR-005-index-delivery.md), [ADR-06](ADR-006-portability-retention.md), [ADR-10](ADR-010-ldap-oidc-identity.md), [ADR-13](ADR-013-merge-serialization-recovery.md), [ADR-14](ADR-014-canonical-decision-record.md).
