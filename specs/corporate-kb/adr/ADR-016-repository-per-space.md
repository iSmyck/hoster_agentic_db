# ADR-16 — One repository per Space

**ID/Title:** ADR-16 / Один GitLab repository = один Space  
**Status:** **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00**. Правило периметра зафиксировано, но naming/group layout/provisioning и production corpus не утверждены.  
**Date:** 2026-11-06  
**Requirements/AD links:** R02, R04, R05, R11–R14, R16, R17; I02, I08–I13; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-1, AD-3, AD-4, AD-6, AD-9, AD-11; [spec.md](../spec.md): разделы 3.2 и 5.

## Context

Ранняя логическая модель допускала Space как repository или корневую папку. При совместном хранении нескольких ACL Spaces в одном repository Git blobs и history становятся общими: фильтрация дерева/search не закрывает clone/export/history disclosure, а protected branch, credentials, cutover и backup получают разные бизнес-периметры в одном физическом объекте.

В MVP документ наследует единый ACL Space. Разные ACL требуют разных Spaces. Path-scoped approver roles остаются возможны внутри Space, но это review policy, а не arbitrary page-level ACL. Физический 1:1 perimeter нужно зафиксировать до согласования repository layout и создания production corpus.

## Decision

1. **В MVP один GitLab repository соответствует ровно одному Space, и один Space занимает ровно один repository.** Несколько ACL Spaces не разделяют Git blobs, refs или history. Более ранняя альтернатива «корневая папка = Space» отклонена для MVP.
2. Repository объединяет единый периметр:
   - Space ACL и versioned access/approval policies;
   - protected target branch и GO/agent/connector credentials;
   - document revisions, proposals/decisions и cutover;
   - index snapshots/generations/profiles;
   - clone/export, mirror backup и restore.
3. `space_id` — стабильный lowercase slug; `document_id` — opaque UUID, не зависящий от пути. Папки и path scopes организуют дерево/review внутри Space, но не создают независимый security perimeter.
4. Default private. Каждый документ и attachment revision наследует ACL Space. Если двум группам нужны разные права на чтение/history/files/export, содержимое разделяется на разные Spaces/repositories **до production corpus load**.
5. Поле `access` во front matter не является самостоятельным источником прав и не создаёт page-level ACL. Авторизация tree/titles/snippets/chunks/files/history/export/search/tools использует versioned policy и server-issued AuthzContext.
6. Бизнес-пользователи не получают GitLab users по ADR-12; repository perimeter применяется GO/Identity adapter к платформенным grants. Engineering GitLab RBAC действует внутри того же repository perimeter и не расширяет business grants.
7. Full clone/export допускается только при export permission на Space **и всю его историю** по ADR-06. Filtered export или удаление истории требуют отдельного privileged workflow. Индекс/retrieval не используются как обход этого ограничения.
8. Cutover, write freeze, `HEAD == cutover_sha`, preflight и activation выполняются отдельно для каждого Space/repository. Merge serialization key включает `repository_id` и target branch; active index pointer сериализуется per `(space_id,profile_id)` across all generations с current fence/latest ancestry/run CAS; per-generation lock alone недостаточен.
9. Naming, GitLab group layout, repository creation/order, source bindings и migration конкретных существующих корпусов остаются **UNKNOWN до T00/owner decision**. Это не откладывает правило 1:1 и не разрешает заранее создавать production corpus.
10. Обязательный page-level ACL с прямым доступом людей к Git является stop-триггером для пересмотра Git-native модели по ADR-08. Нельзя молча эмулировать его front matter, search filters или folder export.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Один repository, Space = корневая папка | Меньше repositories, но общие blobs/history/backup и риск cross-Space disclosure | Отклонено для MVP |
| Несколько ACL Spaces в repository с document-level filtering | Меньше администрирования, но clone/history/export обходят filters | Отклонено |
| Repository на документ | Максимальная изоляция, но чрезмерный lifecycle/review/provisioning overhead | Отклонено |
| GitLab subgroup как единственная граница | Удобная иерархия, но не разделяет blobs/history внутри repository | Недостаточно |
| Front matter `access` как page ACL | Гибкость метаданных, но drift между Git, index и AuthZ | Не является источником авторизации |

## Consequences

### Positive

- ACL, Git history, credentials, index и export имеют один доказуемый периметр.
- Full clone не раскрывает историю другого Space внутри того же repository.
- Cutover, recovery, retention и restore планируются независимо по Space.
- Устраняется неоднозначность root-folder mapping перед миграцией корпуса.

### Negative

- Число repositories и связанных policies/credentials/CI jobs растёт.
- Разделение существующего corpus требует предварительного ACL/provenance анализа.
- Общие знания между Spaces требуют явного контентного процесса без совместного скрытого history perimeter.

### Cost

- Нужны repository provisioning, per-Space CI/index/backup и управление политиками.
- Миграция и второй клиент требуют повторяемой конфигурации; конкретная layout/стоимость определяются после T00 и source audit.

## Verification / T00 evidence

- **T00:** подготовить repository-per-Space provisioning design с synthetic fixtures; проверить protected branches, scoped tokens, tag refs, webhooks, export/backup semantics на выбранном GitLab baseline без создания production corpus.
- Cross-Space adversarial tests: пользователь одного Space не получает tree/titles/snippets/chunks/files/history/export/tools другого; смена document path/front matter не меняет perimeter; anti-enumeration сохраняется.
- Clone/mirror каждого repository содержит только соответствующий Space history/decisions/assets references; filtered export не выдаётся за поддерживаемый полный export без отдельного workflow.
- Независимые cutover/preflight/activation и late index jobs двух Spaces не меняют чужие active pointers. Merge locks различаются по `(repository_id, target_branch)`.
- Проверить, что разные ACL приводят к разным repositories до import, а `approval-policy.yaml` path scopes не становятся скрытой page-level read ACL.
- **Текущее состояние:** naming/layout/provisioning не выбраны, production repositories/corpus не создавались, integration evidence отсутствует.

## Related contracts

- `space_id`, `repository_id`, document/source IDs и Space/path scopes.
- Versioned access policy + `approval-policy.yaml`; AuthzContext и managed grants.
- Per-repository cutover/protection/merge lock; per-Space index generation/profile/pointer.
- Clone/export/decisions/assets manifests, mirror backup и restore closure.
- [ADR-03](ADR-003-retrieval-adapter.md), [ADR-05](ADR-005-index-delivery.md), [ADR-06](ADR-006-portability-retention.md), [ADR-10](ADR-010-ldap-oidc-identity.md), [ADR-11](ADR-011-two-phase-publication.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-13](ADR-013-merge-serialization-recovery.md).
