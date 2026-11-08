# DocOps correction task API and operational record

**Статус:** PROPOSED / DESIGN_NOT_EXECUTED. Машинная форма — [docops-correction-task-v1](docops-correction-task.schema.json) и [OpenAPI create/get/resolve/cancel](openapi.yaml). Этот документ фиксирует semantic contract для E04.7/T07b и T01 negative vectors; он не является выполненной реализацией, integration PASS или production approval.

## 1. Граница и владельцы

Correction task — **GO-owned operational record в `kb_ops`**, создаваемый действием «нашёл ошибку» на authorized exact document revision. Только GO пишет current projection, append-only task events, restricted sanitized evidence payload и общую idempotency registry. Identity/AuthZ поставляет fresh per-Space `authz-context-v2`, policy bundle/revisions и group/revocation/actor epochs.

Task не является:

- canonical document или его revision;
- ProposalRecord, ProposalVersion или DecisionRecord;
- canonical document status или частью `draft/in_review/published/indexed/archived/conflicted`;
- DocOps `valid_until` projection со states `scheduled/due/in_review/resolved/removed`;
- вторым write path в GitLab, `kb_authz`, `kb_index` или upstream tables.

Task/API никогда не редактирует, не публикует, не архивирует и не удаляет canonical content. Изменение содержимого требует обычный E04.1/E04.2/E04.4 ProposalRecord/MR/canonical human DecisionRecord/GO merge.

## 2. Identity, owner и exact revision

- `requester_stable_id`, `resolved_by_stable_id`, `cancelled_by_stable_id` выводятся только из trusted server context. Browser, agent, connector и LLM не задают actor как доказательство.
- `owner={kind:user|group,stable_id}` вычисляется из действующей `approval-policy.yaml` и согласованного policy bundle. Front matter, model arguments и client-supplied owner не используются.
- Group owner назначает очередь группе; mutation выполняет конкретный trusted actor с текущей group/path role. Stable external identity сохраняется при login/email rename.
- `space_id`, `repository_id`, `document_id` обязаны соответствовать одному repository=Space binding. `document_revision_sha` — полный lowercase exact Git SHA ревизии, на которой сообщена ошибка.
- При новом HEAD исходный `document_revision_sha` не перепривязывается. Correction MR создаётся от fresh HEAD с полным diff/conflict review; silent rebase/rebind запрещён. Конфликт требует новой ProposalVersion.
- Create/get/resolve/cancel и internal event projections используют fresh per-Space AuthzContext и anti-enumeration. Чужой Space возвращает safe `NOT_FOUND` либо `FORBIDDEN` по policy без metadata/payload disclosure.

## 3. Evidence и linked MR

Create обязан содержать sanitized `evidence={summary}` и `evidence_sha256`. Hash вычисляется как SHA-256 от JCS (RFC 8785) UTF-8 closed evidence object. No-MR resolution и cancellation также требуют reason, evidence object и соответствующий новый hash. Сервер проверяет hash до side effect.

Evidence payload хранится только в restricted GO-owned evidence storage, связанном с task events. Обычный API response возвращает hash, но не payload. Raw evidence, secrets, unredacted personal data и unrelated private content запрещены в logs, metrics, traces, ordinary export и model arguments.

`linked_mr=null` означает отсутствие связанного MR. Иначе объект содержит:

- `proposal_id` и exact `proposal_sha` существующего governed ProposalVersion в том же Space/repository;
- `merge_commit_sha=null`, пока governed merge отсутствует или не доказан;
- full `merge_commit_sha` только после verified GO merge с canonical decision, exact parents/trailers/note+tag evidence.

Linked MR не заменяет ProposalRecord/DecisionRecord и сам по себе не доказывает merge или corrected/published state.

## 4. Versioned lifecycle

```text
open --durable valid linked MR--> in_review
open/in_review --authorized conclusive resolution--> resolved
open/in_review --authorized cancellation--> cancelled
resolved/cancelled --terminal; no reopen through replay-->
```

- Create возвращает `open`, либо `in_review`, если валидный optional `linked_mr` уже durable.
- Если MR создаётся позже, trusted correction workflow вызывает внутреннюю GO `LinkCorrectionMR` command с task ID, exact proposal identity, ожидаемой `task_version` и idempotency metadata. Публичного ad-hoc link endpoint нет. GO проверяет governed MR, append `linked` event, увеличивает `task_version` и переводит `open → in_review`.
- `in_review` не означает corrected/published. Open/in_review correction продолжает normal MR/human decision/GO merge.
- `resolved` с content correction допускается только после verified governed outcome и non-null `merge_commit_sha`. `resolved` без MR требует reason + resolution evidence hash и означает только задокументированную disposition, а не исправление канона.
- `cancelled` разрешён авторизованному requester/owner по действующей policy и требует reason + cancellation evidence hash. Canonical content не меняется.
- `resolved` и `cancelled` terminal. Reopen, обратные transitions и изменение terminal actor/reason запрещены. Повтор той же операции возвращает existing record через idempotency, а не новый transition.
- `task_version` — monotonic server CAS version. Resolve/cancel/internal link требуют текущую версию; stale version не мутирует task/events/registry.

## 5. Public endpoints

Все paths находятся под логическим `/api/kb/v1`. Mutations требуют `browserSession + csrfToken` и `Idempotency-Key`; agent/connector credentials не имеют correction-task mutation capability.

| Operation | Endpoint | Request/result |
|---|---|---|
| Create | `POST /spaces/{space_id}/docops/correction-tasks` | Body: path-matching `space_id`, `document_id`, exact `document_revision_sha`, evidence object+hash, optional linked MR, body/header-matching `idempotency_key`. Server derives requester/repository/owner and returns `201` для new task или `200` для identical replay. |
| Get | `GET /spaces/{space_id}/docops/correction-tasks/{task_id}` | Freshly authorized exact task/state/owner/revision/evidence-hash/linked-MR view. Raw evidence payload не возвращается. |
| Resolve | `POST /spaces/{space_id}/docops/correction-tasks/{task_id}/resolve` | Owner-only. Body: matching `space_id/task_id`, current `task_version`, idempotency key, reason, optional linked MR. MR-based resolution требует verified governed merge. Без linked MR обязательны evidence object+hash. |
| Cancel | `POST /spaces/{space_id}/docops/correction-tasks/{task_id}/cancel` | Уполномоченный requester/owner по policy. Body: matching `space_id/task_id`, current `task_version`, idempotency key, reason, evidence object+hash. |

Response использует только closed `docops-correction-task-v1`. `task_id` server-generated UUID и не переиспользуется. `created_at/updated_at/resolved_at/cancelled_at` — UTC RFC 3339 server timestamps.

## 6. Idempotency и ошибки

Каждая mutation использует общую tuple:

```text
(verified actor,
 normalized operationId + route template,
 concrete path parameters,
 Idempotency-Key,
 SHA-256(JCS(normalized request payload)))
```

Identical replay возвращает durable current result без второго task event, version increment, MR link или иного side effect. Reuse key с другим actor/route/concrete path/payload возвращает `IDEMPOTENCY_KEY_REUSED` и ноль writes. Body/header key и path/body `space_id/task_id` сверяются до side effect.

| Condition | Error | Mutation |
|---|---|---|
| Unauthorized actor/owner или stale AuthzContext | `FORBIDDEN`/`NOT_FOUND`, `AUTHZ_CONTEXT_STALE`, `POLICY_REVISION_MISMATCH` по policy | Ноль task/event/content writes |
| Reused key under another tuple | `IDEMPOTENCY_KEY_REUSED` | Ноль writes |
| Stale `task_version`, changed exact revision/binding | `REVISION_CONFLICT` | Ноль writes |
| Invalid transition, terminal mutation без identical replay, missing no-MR evidence | `INVALID_STATE` | Ноль writes |
| MR missing, wrong Space/SHA или governed outcome not conclusive | `REVISION_CONFLICT`/`INVALID_STATE` | Ноль writes |
| Required GitLab/IdP/DB operation unavailable | `UPSTREAM_UNAVAILABLE` | Не optimistic success; durable state reconciled |

Все errors используют существующий `{code,message,request_id,details?,retryable}` shape с sanitized details. `FORBIDDEN/NOT_FOUND` выбирается по anti-enumeration policy.

## 7. Durability, backup, retention и rebuild

1. Current task projection, append-only events, restricted evidence payloads и idempotency records являются durable `kb_ops` operational state с единственным writer/migrator GO.
2. Эти записи **не полностью Git-derived**. Git clone, MR notes/tags и ordinary Space export не содержат исходный report, owner/actor disposition, evidence payload или все task transitions. Поэтому `kb_ops` backup обязателен и не заменяется Git mirror.
3. Backup включает согласованные current projections, events, evidence records и idempotency records с version/hash/closure evidence. Отдельные secrets policy и cross-client isolation сохраняются. Active open/in_review tasks и unresolved evidence нельзя удалять по generic TTL; terminal retention назначает owner.
4. Restore начинается с external global managed-write freeze. GO восстанавливает `kb_ops` backup, проверяет event sequence/hashes/perimeter и только затем reconciles linked MRs и canonical revisions. Git-derived `kb_ops` state rebuild выполняется отдельно и не стирает task state.
5. Missing/corrupt backup или недоказанный linked outcome оставляет affected operational scope unavailable/quarantined и требует incident review. Пустая БД не означает отсутствие tasks. Запрещено fabricate, silently drop, auto-resolve или auto-cancel tasks из Git alone.
6. После restore не выполняется automatic canonical correction или reopen. `in_review` остаётся review state, пока conclusive governed outcome не получен; content `resolved` по-прежнему требует verified merge evidence.

## 8. Обязательные DESIGN_NOT_EXECUTED vectors

[T01 CF-06/CF-10/CF-20/CF-25](t01-contract-tests.yaml) включает:

- create/get exact revision, trusted actor, policy owner и anti-enumeration;
- open → in_review → resolved/cancelled, terminal replay и invalid transitions;
- stale task version, changed document revision/policy, wrong path/body IDs;
- same-key replay и key reuse под other actor/route/path/payload с нулём writes;
- linked MR without merge proof, wrong Space/SHA и no-MR resolution без reason/evidence hash;
- direct canonical write/archive attempt через task API;
- kb_ops backup/restore без task fabrication/loss, linked-MR reconciliation и unavailable real checks как BLOCKED.

[Projection mapping](projection-mapping.md) отделяет correction task states от DocOps valid_until, Proposal и canonical document states.
