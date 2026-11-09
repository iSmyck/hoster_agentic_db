# ADR-07 — Client packaging and license

**ID/Title:** ADR-07 / Клиентская упаковка, изоляция deployment и лицензионные ограничения  
**Status:** **Proposed** до T00 baseline, GitLab edition review и юридической license/SBOM проверки; не разрешает commercial distribution или production rollout. GitLab placement и Shared/Dedicated exception уточнены отдельным owner-approved ADR-17 от 2026-11-09.
**Date:** 2026-11-06  
**Requirements/AD links:** R01, R05, R14–R18; I02–I04, I09; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-2, AD-4, AD-11, AD-12, AD-14; [spec.md](../spec.md): T00, T11, T18.

## Context

Продукт должен повторно развёртываться у hoster.ai и внешних клиентов без отдельной code branch на каждого. Клиентские различия касаются repositories, identity/group mapping, data profile, approved providers и resources; они не должны расползаться по fork. Общие secrets, DB, index или backups между клиентами нарушают изоляцию.

Open WebUI license не является обычной MIT; branding/notices нельзя удалять по умолчанию. GitLab CODEOWNERS/approval/branch semantics зависят от выбранной version/edition, но бизнес-approval в любом случае принадлежит GO/approval-policy, а не GitLab users. Licenses моделей, extraction/OCR, plugins и dependencies проверяются отдельно. Конкретные версии и правовые заключения пока отсутствуют.

## Decision

1. Поставлять **один reusable core + versioned configuration/adapters** на dedicated client deployment. Клиентские code branches запрещены; изменения общего ядра проходят product review.
2. Каждый клиент получает независимые GitLab repositories по ADR-16, configuration, PostgreSQL/index, object storage, secrets, client backup packages и approved egress. Cross-client credentials/data/cache не создаются. Размещение GitLab instance определяется ADR-17: Shared hosting допускается только с per-client groups/repositories, credentials и backup/restore; это не общий application/PostgreSQL/index/object/secrets data plane.
3. Open WebUI остаётся минимальным fork. Для каждого изменения ведётся **seam registry**: code reference, назначение, upstream dependency, tests, owner и upgrade risk. Managed KB включается feature flag; personal Notes и обычные чаты сохраняются.
4. Identity подключается конфигурацией LDAP/OIDC по ADR-10; endpoint/provider/model parameters, data profile и source adapters — deployment configuration. Конкретные URLs, model IDs, dimensions и editor не фиксируются этим ADR.
5. **Branding и notices выбранного Open WebUI baseline сохраняются.** White-label/rebrand, изменение notices или распространение иного пакета требуют license review и отдельного решения владельца; автоматический rebrand не входит в объём.
6. До коммерческого распространения выполняется license/SBOM review core, fork seams, plugins, models, extraction/OCR assets и transitive dependencies. Утверждение «бесплатный стек» не используется: GitLab edition, инфраструктура, inference, хранение и сопровождение учитываются отдельно.
7. T00 фиксирует Open WebUI commit/tag и GitLab version/edition. До этого capabilities не считаются подтверждёнными. Недостаток необходимой GitLab capability останавливает G0/design для license/design decision; обходной непроверенный enforcement не объявляется эквивалентом.
8. Upgrade package включает pinned baselines, migration/rollback runbook, regression suite, проверку branding/notices, seam registry и повторный license/SBOM review. Upstream migrations остаются upstream-owned по ADR-15.
9. Поставка и rollout выполняются только после соответствующих gates и отдельных owner approvals; этот ADR не выбирает deployment toolchain. Kubernetes application namespace и размещение GitLab вне его lifecycle для соответствующего deployment profile зафиксированы отдельно ADR-17 и не выбирают конкретный packaging/orchestration tool.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Отдельный fork на клиента | Быстрая локальная кастомизация, но невоспроизводимые upgrades и поддержка | Запрещено как default |
| Единый shared application/PostgreSQL/index/object/secrets data plane | Меньше instances, но смешивает клиентские данные/secrets и усложняет изоляцию | Отклонено; Shared GitLab hosting допускается только в границах ADR-17 и не создаёт общий client data plane |
| Полный rebrand без legal review | Коммерчески удобно, но риск нарушения license/notices | Не разрешено |
| Зафиксировать предполагаемую GitLab edition сейчас | Упрощает смету, но опирается на непроверенные capabilities | Отложено до T00 |
| Переписать upstream auth/chat/RAG под packaging | Контроль кода, но большой fork и upgrade cost | Отклонено; reuse и seams |

## Consequences

### Positive

- Второй клиент проверяет repeatability без изменения core code.
- Независимые data/secrets ограничивают blast radius.
- Seam registry и SBOM делают upgrade/legal impact видимым до обязательств.
- Сохранение notices снижает лицензионный риск.

### Negative

- Dedicated instances требуют эксплуатации и мониторинга каждого контура.
- Ограничение кастомизации может требовать отказа от клиентских special cases.
- Legal/edition unknowns могут заблокировать поставку после проектирования.

### Cost

- Нужны deployment automation, isolated backup/restore, upgrade/rollback rehearsals и повторные юридические проверки.
- Поддержка нескольких pinned baselines и инфраструктура/inference/GitLab не считаются бесплатными; смета составляется после T00.

## Verification / T00 evidence

- **T00:** сохранить sanitized baseline record с фактическими Open WebUI commit/tag, GitLab version/edition, license texts/notices и capability matrix. До фактической проверки юридический и GitLab статус — UNKNOWN/BLOCKED, не PASS.
- A19/A20: второй synthetic client разворачивается новыми repositories + config + independent data/credentials без code edits; personal Notes и normal chats проходят regression.
- Проверить изоляцию secrets/data/backups/egress, отсутствие cross-client cache и невозможность использовать credentials одного клиента в другом.
- Upgrade/rollback rehearsal на pinned baseline: seam tests, branding/notices diff, SBOM/license delta, database ownership и restore procedure.
- Перед commercial distribution получить явное legal/owner review. **Текущее состояние:** второй deployment, license opinion и upgrade drill отсутствуют.

## Related contracts

- Dedicated deployment configuration, versioned adapters, seam registry, feature flags.
- LDAP/OIDC group mapping, data profiles `strict`/`pii_permitted`, provider/egress allowlist.
- Independent clone/manifest/backup package; PostgreSQL writer/role matrix.
- Pinned dependency/SBOM/license inventory и upgrade/rollback runbook.
- [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-06](ADR-006-portability-retention.md), [ADR-10](ADR-010-ldap-oidc-identity.md), [ADR-15](ADR-015-postgresql-schema-ownership.md), [ADR-16](ADR-016-repository-per-space.md), [ADR-17](ADR-017-gitlab-deployment-topology.md).
