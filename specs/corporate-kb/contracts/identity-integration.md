# Identity and AuthZ integration contract

**Статус:** PROPOSED для G0; нормативные границы AD-4–AD-6, AD-12 обязательны. Authority: [ARCHITECTURE-SPINE.md](../architecture-spine.md) и [ADR-10](../adr/ADR-010-ldap-oidc-identity.md). Сквозной flow: [integration.md](../integration.md).

Open WebUI commit, LDAP/OIDC seams, stable attributes, JIT, grants semantics, session/CSRF mechanics, nested groups, live subscriptions и group recheck — **UNKNOWN до T00**. Собственный LDAP/OIDC client или новый authentication protocol не создаётся.

## 1. Identity modes и stable identity

| Mode | Использование | Stable ID | Обязательные проверки |
| --- | --- | --- | --- |
| `ldap` AD | Upstream Open WebUI LDAP authentication | AD `objectGUID` | Read-only bind, LDAPS/StartTLS, nested groups, empty-password reject, JIT |
| `ldap` OpenLDAP | Тот же configuration-driven seam | `entryUUID` | Те же controls в применимом provider profile |
| `oidc` | Upstream Open WebUI OIDC authentication | `sub` в пределах configured issuer mapping | Issuer-scoped namespace, session/JIT/grants/revocation behavior |

Email/login не используются как identity key. Rename сохраняет ProposalRecord/DecisionRecord/history/review attribution. OIDC `sub` из разных issuers не смешивается в один key namespace без отдельного design.

CVE-2026-44551 и пустой LDAP password проверяются negative test на pinned commit. Невозможность получить stable ID или fresh groups — BLOCKED, не fallback на email.

## 2. Login и JIT flow

1. Пользователь аутентифицируется через supported upstream LDAP/OIDC path.
2. Identity adapter получает trusted server-side identity attributes; browser payload не является доказательством.
3. Adapter нормализует `{stable_id,username,display_name,groups[]}`, разрешает nested AD groups и фиксирует `group_snapshot_at`.
4. При первом login JIT создаёт/обновляет только upstream identity и managed grants projection. GitLab business user не создаётся.
5. Adapter загружает согласованный access+approval policy bundle **отдельно для каждого Space**, вычисляет effective Space/path scopes с собственными policy/group snapshots и выдаёт server-side [AuthzContext v2](authz-context.schema.json).
6. Managed KB UI получает только effective experience. Personal Notes и ordinary chats сохраняют upstream semantics и не наследуют managed corpus grants автоматически.
7. Review queue назначается группе из approval policy, не персональному GitLab account.

Joiner получает grants/queue через JIT или group refresh. Mover получает новые scopes/queue и теряет старые. Leaver проходит revocation barrier. Ошибка синхронизации не расширяет права.

## 3. Versioned policy bundle

[access-policy](access-policy.schema.json) и [approval-policy](approval-policy.schema.json) активируются как один согласованный unit:

- одинаковые `policy_bundle_id`, `repository_id`, `space_id`;
- полные `access_policy_revision` и `approval_policy_revision` из Git;
- canonical paths с NFC/forward slashes и запретом `..`;
- default private, один repository=Space;
- group grants как норма, personal grants только с justification+approval evidence;
- path-scoped approver rules с `approvers_required=1` и `self_approval_allowed=false`; unique rule IDs/normalized prefixes и ровно одно longest-normalized-prefix правило на segment boundary без union менее специфичных groups.

Activation sequence:

1. Получить immutable policy snapshot через согласованный canonical-read adapter, не `kb_ops` table read.
2. Проверить closed schemas, groups, Spaces, paths, отсутствие page-level ACL и revision consistency.
3. Активировать access+approval атомарно; при ошибке сохранить предыдущий полностью согласованный bundle.
4. Идемпотентно синхронизировать managed upstream grants и `kb_authz` по desired-state hash.
5. Отправить `kb.access_policy.changed.v1`. Fresh deny действует до reindex.
6. При изменении group/policy увеличить revocation epoch и инвалидировать старые contexts/cursors/subscriptions.

Identity/AuthZ adapter — единственный writer managed grants и `kb_authz`. GO/retrieval/UI не пишут эту schema и не копируют её privileges в собственные tables.

## 4. AuthzContext contract

Каждый request использует server-issued [AuthzContext](authz-context.schema.json):

| Поле | Использование |
| --- | --- |
| `context_id`, `issuer` | Correlation/audit; не bearer credential |
| `stable_id`, `actor_type` | Trusted principal и human/agent/connector/internal_ci/service classification |
| `space_scopes[]` | Независимые `{space_id,repository_id,capabilities,policy_bundle_id,access_policy_revision,approval_policy_revision,group_snapshot,revocation_epoch}` для каждого repository=Space |
| `space_scopes[].group_snapshot` | `{snapshot_id,captured_at,membership_sha256,groups[]}` с effective direct/nested groups именно для этого Space |
| `path_scopes[]` | Proposal/review/merge routing, не page-level read ACL; каждый path scope обязан ссылаться на существующий Space entry |
| `evaluated_at`, `expires_at` | Freshness/TTL barrier; каждый per-Space `group_snapshot.captured_at` проверяется относительно них |
| `revocation_epoch` | Actor/session epoch плюс независимые per-Space epochs; cursor хранит весь набор |

Agent/connector schema constraints допускают только read/search/propose/source_read и path propose; merge/review/export/manage_grants/index_write им не выдаются. Internal CI получает только read/index_write и не получает path approver scopes. Это дополнительный contract guard, не замена GitLab enforcement.

Context не передаётся модели как self-asserted authority и не является merge credential. GO всё равно выполняет sensitive recheck, retrieval повторно авторизует каждый payload.

## 5. Sensitive recheck и long operations

Перед merge/export/private page:

1. Перепроверить stable identity и external groups у provider/fresh group path.
2. Подтвердить один policy bundle и полные revisions **для конкретного Space**, не заимствуя их из другого Space multi-Space context.
3. Вычислить capability на конкретный Space/path, не только global role.
4. Для merge проверить approver ≠ author/version_author/requester.
5. Выдать refreshed short-lived context. При unavailable/stale recheck операция fail closed.

Long-running retrieval, streaming, import и export обновляют/подтверждают context **перед каждым новым payload/batch**. Multi-Space cursor/subscription хранит полный per-Space набор snapshots/profiles/bundles/revisions/group snapshots/epochs и не сохраняет право доступа навсегда. При смене revisions или revocation epoch хотя бы одного задействованного Space прежний context недействителен для sensitive operation.

Provider outage не разрешает бесконечный cached allow. Sensitive operations не выполняются по устаревшему allow; обычные payloads не выходят за подтверждённый freshness/SLO barrier.

## 6. Revocation barrier

- Фоновый group refresh выполняется не реже 15 минут.
- Revocation SLO для private pages/search/agent tools/history/files/export — **≤30 минут**.
- Merge/export/private page denial происходит при ближайшем sensitive recheck, потенциально раньше фонового цикла.
- `kb.access.revoked.v1` инвалидирует contexts/cursors/derived grants и закрывает live subscriptions.
- Streaming прекращает новые payloads после revoke. Уже отправленный browser/model текст невозможно «забыть»; chat retention регулируется отдельно.
- История Git, stable attribution, proposals и decisions не переписываются при mover/leaver.

Старый group sync не перезаписывает более свежий snapshot. Grant/policy sync идемпотентна по bundle+revisions+snapshot+desired-state hash и не создаёт duplicate grants.

## 7. Session, CSRF и service boundaries

| Boundary | Обязательное правило |
| --- | --- |
| Browser reads | Authenticated upstream session + server AuthzContext; anonymous managed reads отсутствуют |
| Browser mutations | Session + CSRF + Idempotency-Key + capability recheck; double click/reload сохраняет тот же key |
| Agent calls | Отдельный bounded credential и run context; browser session не переиспользуется как agent privilege |
| CI callbacks | Отдельный internal CI credential; нет human/session context и merge grants |
| Webhooks | Отдельная webhook credential и verified event identity; payload actor не доверен |
| Merge service | Отдельный credential, не выдаётся Identity adapter как upstream grant и недоступен другим processes |

OpenAPI logical session/CSRF names не являются утверждением фактических upstream names. Их mapping проверяется T00 без ослабления server checks.

## 8. Errors и anti-enumeration

- `NOT_FOUND` скрывает protected object вне visible scope.
- `FORBIDDEN` используется, когда denial разрешено раскрыть.
- `AUTHZ_CONTEXT_STALE` — refresh перед payload; cursor не помогает.
- `GROUP_SNAPSHOT_STALE` — sensitive operation fail closed.
- `POLICY_REVISION_MISMATCH` — остановить operation до одного bundle.
- `IDENTITY_UNAVAILABLE` — нет новых privileged grants/merge/export; retryable по сбою.
- `APPROVER_CONFLICT` — self-approval или потерянный path/group role.
- `INVALID_POLICY` — не активировать partial bundle.

## 9. Export и restore identity mapping

Export содержит policy bundle+revisions и grants mapping hash, но не bind secrets, session tokens или credentials. Full export требует fresh export/history permission на Space и каждого batch.

Restore применяет explicit external group/stable ID mapping через Identity adapter, пересобирает `kb_authz` из Git policy+IdP и не восстанавливает privileges из непроверенного DB backup. Cross-client identities, secrets и grants не смешиваются.

## 10. Обязательные проверки

После T00: LDAP/OIDC happy path, empty/invalid password reject, stable ID при rename, nested groups, JIT без GitLab business account, two-Space different bundle/group snapshot search+cursor, cross-Space IDOR, mover/leaver, revoke между candidate/payload/review/merge/export/stream, group/policy revision mismatch, duplicate/identical/overlapping approval prefixes и longest-prefix groups, partial activation, stale snapshot race и personal Notes/ordinary chat regression. Реальные IdP/upstream проверки пока отсутствуют; mocked login не считается PASS.
