# ADR-10 — LDAP/OIDC identity

**ID/Title:** ADR-10 / Стабильная LDAP/OIDC identity, группы и revocation barrier  
**Status:** **Accepted** по spec решением владельца от 2026-11-06; дополнен AuthzContext, schema ownership и policy consistency во время architecture coaching. Реализация зависит от результатов T00; upstream capabilities не считаются подтверждёнными.  
**Date:** 2026-11-06  
**Requirements/AD links:** R05, R11, R15–R18; I03, I06, I09, I12; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-4–AD-6, AD-8, AD-12; [spec.md](../spec.md): раздел 5, T00, T03, A24–A26.

## Context

Email/login могут меняться и не должны разрывать историю, proposal attribution или очередь ревью. Платформа использует бизнес-аккаунты Open WebUI, тогда как GitLab identity нужна только инженерному контуру; бизнес-владельцы вообще не имеют GitLab user records. Зависимость от GitLab LDAP group sync поэтому не требуется и не должна предполагаться.

LDAP/OIDC отвечает «кто ты», платформа — «что тебе можно». Права не помещаются в атрибуты документов и не строятся внутри AD. Групповое членство устаревает в кэшах; revocation должен прекращать новые retrieval/tool payloads, exports, merges и live subscriptions, хотя уже доставленный браузеру/модели текст отозвать невозможно.

## Decision

1. Переиспользовать upstream Open WebUI LDAP/OIDC authentication и зрелые библиотеки; собственный LDAP/OIDC client не создавать. Deployment выбирает режим `ldap` или `oidc` конфигурацией без клиентской code branch.
2. Identity adapter нормализует `{stable_id, username, display_name, groups[]}`. `stable_id`: AD `objectGUID`, OpenLDAP `entryUUID` или OIDC `sub`. Email/login как identity key запрещены; IDs не переиспользуются.
3. Целевые LDAP controls: read-only bind, LDAPS/StartTLS, обязательный отказ на пустой пароль, nested AD groups, JIT provisioning. Это **UNKNOWN до T00** на выбранном commit, включая регрессионный тест CVE-2026-44551; документация другого release не является evidence.
4. Versioned Git policy отображает внешние группы на scoped roles, Spaces и path-scoped approver roles. Access и approval policy входят в один `policy_bundle_id`; `access_policy_revision` и `approval_policy_revision` — полные Git SHA, согласованные между IAM и GO.
5. Identity/AuthZ adapter — единственный writer managed grants в upstream и `kb_authz`. Он не заменяет upstream owner таблиц users/sessions/chats/model connections. Secrets bind находятся только в deployment secret mechanism.
6. Двухслойная RBAC: бизнес Reader/Author/Owner/Space admin/Instance admin использует платформенные scoped capabilities и upstream additive grants; GitLab RBAC/CODEOWNERS — только engineering. Default private; документ наследует ACL Space. Разные ACL требуют разных Spaces/repositories.
7. Поле `access` во front matter не является самостоятельным источником прав. Personal grants — только явно аудируемое исключение. Tree/titles/snippets/chunks/files/history/export/search/tools применяют один серверный authorization contract.
8. Каждый запрос получает server-issued **`AuthzContext`**: `stable_id`, effective Space/path scopes, `policy_bundle_id`, access/approval revisions, `evaluated_at`, `group_snapshot_at`. Actor/groups/tenant от LLM не принимаются. Длительные операции обновляют контекст перед каждым payload/export/merge.
9. Группы обновляются не реже 15 минут и перепроверяются при merge, export и выдаче закрытых страниц. Session TTL и live subscriptions ограничены; revocation event закрывает live subscriptions. **Revocation SLO ≤ 30 минут**; sensitive operations применяют ближайшую перепроверку. Другие SLO этим ADR не устанавливаются.
10. Review queues назначаются группам. Joiner/mover/leaver меняет grants и очередь через группы; переименование login/email сохраняет `stable_id`, историю и MR attribution.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Email/login как ключ | Простое сопоставление, но rename разрывает историю и approvals | Запрещено |
| Авторизация через LDAP-атрибуты документов/page ACL | Ближе к каталогу, но drift с платформенной RBAC и сложный perimeter | Отклонено |
| GitLab LDAP group sync для бизнеса | Требует GitLab users/edition capabilities и смешивает контуры | Не используется |
| Собственный LDAP/OIDC client | Полный контроль, но дублирование upstream auth и security surface | Отклонено до доказанного пробела/ADR |
| Проверка групп только при login | Меньше нагрузки, но не выполняет revocation barrier | Отклонено |
| Персональные grants как норма | Гибкость, но неаудируемый drift | Только аудируемое исключение |

## Consequences

### Positive

- Стабильная attribution сохраняется при rename и mover-сценариях.
- Одна групповая policy управляет UI, tools, retrieval, export и approval.
- Нет зависимости бизнес-контура от GitLab users/group sync.
- Перепроверки ограничивают окно отзыва прав перед sensitive operations.

### Negative

- Group refresh и recheck добавляют нагрузку и зависимость от IdP.
- JIT/nested groups/stable attributes могут потребовать минимальные adapters после T00.
- Revocation не удаляет уже доставленный текст из браузера, чата или модели.

### Cost

- Нужны identity mapping, group snapshots, recheck paths, cache invalidation и integration fixtures для AD/OpenLDAP/OIDC.
- Каждый supported IdP/profile требует security/regression tests; точные эксплуатационные параметры определяются отдельно.

## Verification / T00 evidence

- **T00:** на закреплённом upstream commit проверить code references LDAP/OIDC, stable attributes, nested AD groups, JIT, read-only bind, LDAPS/StartTLS, grants и group recheck. Пробел фиксируется как adapter design или stop condition, не как предполагаемая capability.
- A24: пустой LDAP-пароль и невалидные credentials отклонены, включая CVE-2026-44551 regression; секреты не попали в logs/evidence.
- A25: удаление из группы прекращает private page/search/tools/history/export не позднее утверждённого barrier; merge/export отклоняются при ближайшей recheck; live subscription закрывается.
- A26: rename login/email сохраняет stable identity/history/MR; mover меняет Space/path scopes и review queue. Проверить потерю права между review и merge → ноль canonical writes.
- Cross-Space IDOR и anti-enumeration; IAM и GO используют одинаковый `policy_bundle_id` и revisions; front matter `access` не расширяет права.
- **Текущее состояние:** реальные IdP/upstream проверки не выполнялись; mocked login не засчитывается как PASS.

## Related contracts

- Identity normalization `{stable_id, username, display_name, groups[]}`, JIT/group snapshots.
- Versioned access policy и `approval-policy.yaml`, `policy_bundle_id`, full policy revision SHA.
- Server-issued `AuthzContext`, managed upstream grants и `kb_authz` single writer.
- Revocation/session/live-subscription barrier; group-assigned review queues.
- [ADR-03](ADR-003-retrieval-adapter.md), [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-09](ADR-009-platform-review-ux.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-15](ADR-015-postgresql-schema-ownership.md), [ADR-16](ADR-016-repository-per-space.md).
