# ADR-17 — GitLab deployment topology and tenant profiles

**ID/Title:** ADR-17 / Размещение GitLab вне клиентского application namespace  
**Status:** **Accepted by project owner 2026-11-09.** Зафиксированы deployment boundary и профили Shared/Dedicated; production rollout, конкретные instances, endpoints, namespaces и corpus остаются отдельными owner/gate decisions.  
**Date:** 2026-11-09  
**Approver:** Anton Smychkin, project owner  
**Requirements/AD links:** R05, R06, R14, R17, R18; I02–I04, I09, I10; A19, A20, A33; T18, T18a, T18b/G3; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-2, AD-4, AD-11, AD-16, AD-17; [spec.md](../spec.md): раздел 9.  
**Reference input:** owner-provided `Reference architecture клиентских AI-решений внешнего трека` v1.0, 2026-10-29, RA-1/RA-3/RA-4/RA-10; reviewed at `/Users/antonsmychkin/Downloads/reference-architecture.md` on 2026-11-09. Это contextual owner input, а не repository-pinned normative dependency.

## Context

Для описанного владельцем Kubernetes deployment profile клиентское приложение разворачивается в собственном namespace. Это owner-selected application deployment boundary в рамках данного ADR, а не требование Kubernetes для всех будущих standalone/on-prem профилей. Namespace является единицей поставки и учёта, но сам по себе не обеспечивает сетевую, RBAC, data или failure-domain isolation. Размещение GitLab внутри того же namespace и release lifecycle связывало бы удаление/пересоздание приложения с каноническими repositories, GitLab metadata, persistent volumes, upgrades и backups.

Связь с reference input: RA-1 реализуется trusted tenant/profile bindings; RA-3 — запретом считать namespace достаточной изоляцией; RA-4 — отделением stateful GitLab от application lifecycle; RA-10 — обязательными per-client backup/restore, upgrade и offboarding controls. Эти ссылки не утверждают readiness существующей площадки.

При этом разные клиенты имеют разные требования к изоляции. Standard-профиль должен допускать общий hardened GitLab instance с разграничением клиентов, а клиент с более строгими security/compliance требованиями — отдельный инстанс без изменения продуктового кода.

Общий GitLab instance не должен становиться общим canonical repository, общим credential perimeter или общим client-facing backup/export/restore perimeter. Каноническая изоляция по-прежнему определяется правилом ADR-16: один repository = один Space.

## Decision

1. **GitLab является отдельным platform data service вне клиентского application namespace и вне его application release lifecycle.** Application deployment не устанавливает GitLab image, Pod, StatefulSet или PVC и не удаляет их при install/upgrade/recreate/rollback/uninstall. Application ServiceAccounts, lifecycle hooks и controllers не получают RBAC/API permissions на управление GitLab workloads, PVC или их namespace. Приложение получает только versioned endpoint configuration и secret references.
2. Tenant profile выбирает один из двух режимов:
   - `shared` для Standard: общий hardened self-hosted GitLab instance;
   - `dedicated` для Isolated/Dedicated: отдельный GitLab instance клиента.
   Фактический instance, endpoint, placement, network perimeter и owner выбираются deployment configuration; этот ADR не назначает production resources.
3. В `shared` каждый клиент получает приватную GitLab group namespace `kb-<client>/`, а каждый Space — отдельный repository `kb-space-<space_slug>` по ADR-16. Клиенты не разделяют canonical repository, blobs, refs, history, cutover, index/export perimeter или managed grants. Общий instance не считается общим canonical store.
4. В `dedicated` используются тот же pinned GitLab version/edition и общий versioned configuration template, что и в reusable delivery package. Отдельными являются instance, hostname/endpoints, IdP bindings, secrets, tokens, storage, network rules, backups и restore environment. Изменение продуктового кода или создание client code branch не требуется и не допускается.
5. **Общая конфигурация означает общий pinned baseline и versioned template, но не одинаковые секреты или параметры подключения.** Client-specific values содержат только nonsecret configuration и opaque secret references. Secret values не входят в GitOps configuration, export или sanitized evidence.
6. Credentials разделяются по клиенту и capability:
   - отдельные GO proposal/read и GO merge service identities для каждого клиента;
   - отдельные agent, connector, CI/index, backup/mirror и export credentials;
   - только GO merge identity соответствующего клиента имеет normal managed merge permission в его repositories после cutover;
   - каждый managed credential имеет explicit scope `(tenant_id,space_id,repository_id,capability)`; membership в client group сама по себе не даёт доступ ко всем Spaces клиента;
   - cross-client tokens, shared Maintainer service account и повторное использование чужого credential в managed workload path запрещены;
   - business users не получают GitLab user records по ADR-12.

   Единственное исключение из cross-client restriction — отдельные restricted platform instance-admin и platform DR identities. Они принадлежат platform control plane, хранятся вне клиентских namespaces, инвентаризированы и аудируются, не закрепляются за клиентом или GO и не используются для normal managed read/propose/merge/export. Их privileged canonical bypass обрабатывается по G0-D3; platform DR access не создаёт client-facing credential или restore unit.
7. В managed `shared` profile клиентские пользователи не получают GitLab Group Owner или instance-admin privileges. Platform владеет group/repository protections и privileged account inventory. Engineering access не даёт direct push/merge после cutover. Privileged admin/Owner bypass остаётся out-of-band incident с audit, reconciliation, affected-target quarantine и managed-write freeze по G0-D3 и ADR-13.
8. `shared` GitLab является **общим trust/failure domain**. Restricted admin access, periodic access review, audit, unexpected-HEAD/merge reconciliation, capacity monitoring и outage handling обязательны. Kubernetes NetworkPolicy и namespace RBAC не устраняют риски общего GitLab admin plane или внутреннего cross-client authorization defect. Если tenant требует отсутствия общего admin/data/failure domain, выбирается `dedicated`.
9. Client-facing backup/export/restore имеют per-client outer perimeter и независимые per-Space packages в обоих режимах. Каждый Space сохраняет собственные Git mirror со всеми refs, MR notes/metadata, decisions/assets/policies/grants manifests и immutable objects с собственным snapshot closure и возможностью независимого restore; общий client inventory не смешивает несколько Spaces в один неявный snapshot. Client-level configuration и required durable `kb_ops` operational backups связываются с явным набором Spaces и не заменяют per-Space closure. Cross-client mixed mirror/export/backup **как клиентский artifact или restore unit** запрещён. Platform-wide instance backup допускается только как restricted platform control-plane DR artifact внутри общего trust domain: он не выдаётся клиенту, не используется для per-client restore и не заменяет per-client package или clean isolated restore drill.
10. **Миграция существующего canonical Space между `shared` и `dedicated` не является config-only операцией и не определяется этим ADR.** До отдельного migration ADR и verified runbook она DEFERRED и не разрешается. Такой протокол обязан сохранить единый canonical writer под freeze, exact repository/note/tag/merge linkage, stable IDs и DecisionRecord/export verification, conclusive reconciliation и отсутствие dual-write. Создание нового dedicated deployment для нового клиента этим ограничением не заменяется; существующий corpus не копируется неявно.
11. Tenant profile содержит как минимум `gitlab_mode`, logical `gitlab_instance_id`, endpoint secret/config reference, client group, repository=Space bindings, credential references и backup/restore perimeter. `gitlab_mode`, `gitlab_instance_id`, endpoint и client group являются **client-level invariant**: все Spaces одного клиента используют одинаковые значения; mixed-mode внутри клиента не поддерживается. Эти значения могут повторяться в per-Space registry только как inherited read-only bindings, а не независимый Space override. `tenant_id`, client and Space bindings определяются platform trusted context, а не аргументами агента или браузера.
12. Pinned baseline GitLab CE `19.5.3-ce.0` сохраняется. Локальный T00 runtime evidence не подтверждает production Helm/deployment chart, HA, shared multi-client isolation или dedicated production restore. Эти проверки выполняются до соответствующих G3/production gates; недоступные проверки имеют статус BLOCKED.
13. Shared GitLab upgrade/config change является platform-level операцией над всеми размещёнными tenants. До изменения фиксируются affected tenants, compatible pinned target, maintenance/write-freeze coordination, backup readiness и rollback impact; один клиент не может независимо изменить версию или rollback общего instance. После изменения выполняются startup reconciliation и per-client negative checks перед staged activation. Dedicated upgrade использует тот же versioned change/rollback contract, но отдельный authorized maintenance window.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| GitLab внутри каждого клиентского application namespace | Простая первоначальная упаковка, но общий release/data lifecycle, риск удаления PVC и усложнённые upgrades/restore | Отклонено |
| Только общий GitLab для всех клиентов | Меньше эксплуатационных затрат, но общий admin/data/failure domain не подходит строгим security-профилям | Отклонено как единственный режим |
| Обязательно отдельный GitLab каждому клиенту | Сильная изоляция, но избыточная стоимость и upgrade/support overhead для Standard | Не является default; доступно через `dedicated` |
| Общий repository или shared history для нескольких клиентов | Меньше repositories, но нарушает canonical ACL/history/export perimeter | Запрещено ADR-16 |
| Общий cross-client GO/GitLab service account | Проще конфигурация, но confused-deputy и неограниченный blast radius | Запрещено |
| Client-managed Group Owner в shared managed profile | Self-service удобство, но возможность менять membership/protections в обход GO | Не допускается в managed profile |

## Consequences

### Positive

- Удаление, rollback или recreate приложения не затрагивает GitLab data lifecycle.
- Standard использует общий platform service без смешивания canonical repositories, credentials и client backup packages.
- Dedicated-профиль повторяет тот же продуктовый deployment с изолированным GitLab и без client code branch.
- Per-client export/restore и credential boundary сохраняются независимо от физического размещения GitLab.
- Security-уровень выбирается декларативно через tenant profile.

### Negative

- Shared GitLab требует строгого admin governance и доказательства cross-client isolation на уровне самого GitLab.
- Per-client backup/restore из shared instance сложнее простого instance-wide snapshot.
- Dedicated instance увеличивает стоимость capacity, monitoring, upgrades и support.
- Переход существующего Space между режимами DEFERRED до отдельного migration ADR/runbook и не является простой сменой endpoint.

### Cost

- Нужны versioned tenant profiles, GitLab group/instance provisioning, per-client credentials и backup automation.
- До production требуются shared two-client и dedicated config-only deployment rehearsals, restore/upgrade evidence и security review.
- Shared и dedicated instances имеют разные recurring infrastructure/support costs; конкретные budgets и SLO остаются OWNER_TBD.

## Verification

- Rendered manifests, lifecycle hooks и RBAC клиентского application release не содержат GitLab workloads/PVC, prune/delete ownership на них или permissions управлять ими. Synthetic install, upgrade, recreate, rollback и uninstall не меняют repositories, MR notes/metadata, protected tags, GitLab workload/PVC inventory или stored refs before/after; API deletion от application identity отклоняется.
- Два synthetic клиента с минимум двумя Spaces у каждого на одном GitLab instance не могут читать, создавать proposals, merge, export или восстанавливать данные друг друга; credentials одного клиента отклоняются в perimeter другого, а wrong-Space credentials/operations отклоняются также внутри одного клиента. Все Spaces одного клиента имеют одинаковые inherited `gitlab_mode` и `gitlab_instance_id`; mixed-mode fixture отклоняется. Restricted platform admin/DR identities отсутствуют в client application namespaces и не работают как normal managed merge/export credentials.
- В shared profile отсутствуют client Group Owners и cross-client Maintainer identities; direct human/engineering/bot/CI merge запрещён, privileged unexpected history вызывает incident/quarantine.
- Каждый per-Space package с mirror + MR metadata + decisions/assets/policies/grants + objects восстанавливается независимо в clean isolated target без включения другого Space или клиента; client-level required `kb_ops` backup имеет explicit Space mapping и не смешивает их snapshot closure. Restricted platform-wide DR backup не выдаётся клиенту и не используется как его restore package.
- Dedicated второй клиент разворачивается из того же pinned core и configuration template без code edits, с отдельными endpoints, secrets, storage, network и backups.
- Shared upgrade rehearsal с двумя synthetic tenants проверяет affected-tenant inventory, coordinated freeze, backups, startup reconciliation, per-client negative controls и staged activation; independent per-client version change/rollback на одном instance отклоняется.
- Миграция существующего Space между профилями остаётся DEFERRED/BLOCKED до отдельного ADR и не считается проверенной этим решением.
- Реальные shared production instance, dedicated deployment, chart/HA и restore drills до выполнения имеют статус BLOCKED, а не PASS.

## Related contracts

- Tenant/deployment profile, `gitlab_mode`, logical `gitlab_instance_id`, endpoint and secret references.
- [repository-provisioning.md](../repository-provisioning.md): `kb-<client>/kb-space-<space_slug>`, repository=Space bindings.
- Versioned GO proposal/merge, agent, connector, CI/index and backup credential matrix.
- `export-manifest-v2`, Git mirror/MR metadata, decisions/assets/policies/grants manifests и clean restore closure.
- [ADR-07](ADR-007-client-packaging-license.md), [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-13](ADR-013-merge-serialization-recovery.md), [ADR-15](ADR-015-postgresql-schema-ownership.md), [ADR-16](ADR-016-repository-per-space.md).
