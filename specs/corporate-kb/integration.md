# Corporate Agentic Knowledge Platform — integration specification

**Статус:** DESIGN DRAFT / PROPOSED для G0. Документ задаёт сквозные integration contracts и обязательное поведение собственных компонентов. Он не разрешает implementation, production migration, corpus load, deploy или включение egress и не является security/design approval владельца.

**Приоритет:** [ARCHITECTURE-SPINE.md](architecture-spine.md), AD-1–AD-17 → [spec.md](spec.md), R01–R18 и I01–I14 → принятые [ADR](adr/README.md) → [architecture.md](architecture.md) и component designs. При расхождении применяется более высокий приоритет, а не молчаливое объединение правил.

**UNKNOWN до T00:** Open WebUI commit/tag и code paths, GitLab version/edition и API semantics, toolchain, session/CSRF/token mechanisms, webhook headers, CI transport, Git object format, editor, retrieval engine, model IDs/dimensions, source connector, object-store layout, numeric production limits и остальные SLO. Все routes ниже — **PROPOSED собственные GO contracts**, не Open WebUI upstream routes. Отсутствие реальной интеграционной проверки обозначается BLOCKED, не PASS.

## 1. Состав пакета

| Слой | Артефакты |
| --- | --- |
| Общая карта | [contracts/README.md](contracts/README.md) |
| Machine API | [contracts/openapi.yaml](contracts/openapi.yaml) — OpenAPI 3.1 `/api/kb/v1` |
| Agent boundary | [contracts/agent-tools.yaml](contracts/agent-tools.yaml) |
| Event boundary | [contracts/events.yaml](contracts/events.yaml) |
| Git/GitLab | [contracts/gitlab-integration.md](contracts/gitlab-integration.md) |
| Identity/AuthZ | [contracts/identity-integration.md](contracts/identity-integration.md), [authz-context.schema.json](contracts/authz-context.schema.json) |
| Inference | [contracts/inference-integration.md](contracts/inference-integration.md) |
| Sources/storage | [contracts/source-storage-integration.md](contracts/source-storage-integration.md), [source-origin.schema.json](contracts/source-origin.schema.json) |
| Canonical content | [front-matter.schema.json](contracts/front-matter.schema.json), [access-policy.schema.json](contracts/access-policy.schema.json), [approval-policy.schema.json](contracts/approval-policy.schema.json) |
| Review/audit | [proposal-record.schema.json](contracts/proposal-record.schema.json), [decision-record.schema.json](contracts/decision-record.schema.json) |
| Index/export | [index-snapshot.schema.json](contracts/index-snapshot.schema.json), [export-manifest.schema.json](contracts/export-manifest.schema.json) |
| DocOps/mappings/tests | [docops-review-metadata.schema.json](contracts/docops-review-metadata.schema.json), [projection-mapping.md](contracts/projection-mapping.md), [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml) |

## 2. Архитектурная граница и владение состоянием

GitLab владеет canonical Markdown/front matter, revisions, branches, MR/proposals, ProposalRecords, DecisionRecords, cutover и access/approval policies. GO — единственный координатор canonical Git writes и **всех** business/engineering/source-managed merges после cutover. Open WebUI — продуктовая оболочка; CI/index workers — writers пересобираемых projections; PostgreSQL не участвует в canonical write path.

**Один GitLab repository = один Space = один ACL/history/cutover/index/export perimeter.** Корневая папка не является отдельным Space или read ACL. Path prefixes в approval policy задают только review routing. Разные права на tree/history/files/export требуют разных repositories/Spaces до corpus load. `access` во front matter не имеет authorization effect.

| State | Owner | Единственный writer / integration rule |
| --- | --- | --- |
| Documents, revisions, proposals, decisions, policies | GitLab | Только GO координирует managed writes; DB — projection |
| Users, sessions, chats, model connections | Open WebUI upstream | Только supported upstream seams; managed KB не меняет personal Notes/ordinary chats |
| Identity groups | LDAP/OIDC | Identity/AuthZ adapter нормализует stable ID и snapshots |
| Managed grants и `kb_authz` | Git policy + IdP | Только Identity/AuthZ adapter |
| Operations, webhooks, source cursors, recovery barriers, `kb_ops` | GitLab/source registry + operational safety state | Только GO; другие components не пишут tables |
| Chunks, embeddings, snapshots, active pointer, `kb_index` | Git + immutable assets | Только CI/index workers; retrieval read-only |
| Originals/large assets | Immutable/versioned object storage | Scoped ingestion/export adapters; mutable current URL без hash не версия |
| Secrets | Deployment secret mechanism | Не хранятся в Git, product tables, logs, manifests или model payloads |

Межкомпонентный доступ идёт через versioned contracts, не cross-schema writes. Browser и agent не подключаются к PostgreSQL напрямую.

## 3. Authentication и execution capability matrix

Фактические upstream mechanisms — UNKNOWN T00. Ниже обязательное разделение полномочий, а не выбор token format. OpenAPI использует logical placeholders и не утверждает имена production cookies/headers.

| Caller/channel | Credential и request context | Разрешено | Категорически запрещено |
| --- | --- | --- | --- |
| Browser/human | Authenticated upstream session; server AuthzContext; для каждой mutation CSRF по проверенному upstream/GO mapping | Read/search; drafts/proposals по grants; human review/accept/reject/cancel; privileged import/export/cutover при отдельных capabilities | Anonymous managed API; self-asserted actor/groups/tenant; direct Git write/merge; использование browser credential как service token |
| Bounded agent | Отдельный bounded service credential + server-issued run/AuthzContext; requester/run только trusted orchestration | Typed `list/search/read/links/get_proposal/propose_create/propose_edit` в effective scope; curated single-page body create и отдельная `AgentAnchoredPatchChange` с required body section | `editProposalVersion`, whole-document/front matter replacement, merge/accept/reject/cancel, grants, archive/restore/import commit/export/cutover, attachment management, arbitrary Git push, shell/terminal, generic SQL, arbitrary filesystem, Tool Creation, arbitrary Python Tools, bulk/subtree operations |
| Connector | Отдельные `connectorCredential` и source read credential с минимальным source-binding scope; не browser/agent identity | Dry-run/staging и post-cutover source proposals через GO; source observations, non-live cursor reads и registered typed live reads | Pre-cutover controlled bulk, merge/auto-merge, grants, index writes, arbitrary source queries, live_operational cursors, передача source credential модели |
| Internal CI/index | Отдельный internal CI credential; read-only exact-main Git access; только index-writer DB role | Exact snapshot reads, approved extraction/embedding, index runs/status callbacks, single pointer writer | Merge, grants, canonical writes, agent tools, mutable URL reads, прямая выдача preflight/partial index |
| Webhook caller | Отдельная webhook credential; authenticity/replay verification; verified event identity | Только normalized event intake и dedupe | Выбор active SHA без Git read, merge, grants, index pointer updates, trust к actor из payload |
| GO merge service | Отдельная merge service identity, недоступная UI/agent/connector/CI/general proposal adapters | Только verified human apply через GO merge coordinator | Экспорт credential в tool/browser/model; использование для proposal-only paths |

Запрет agent privileged capabilities действует для direct/deferred/note-attached/ordinary/native/temporary chats, automation, channels, external OpenAPI и `call_tool`, независимо от роли chat user. Отсутствие tool в schema не является security boundary: GO, Identity/AuthZ, GitLab protected rules и credential scopes должны независимо отклонять bypass.

Human apply никогда не экспортируется как LLM tool. Содержимое документов, источников, rationale/evidence и tool results — недоверенные данные, не инструкции по расширению scope.

## 4. Общий API contract

### 4.1. Trusted context и versioning

1. Каждый managed request проходит upstream authentication либо verified service authentication, затем Identity/AuthZ выдаёт [AuthzContext](contracts/authz-context.schema.json).
2. `stable_id` — AD objectGUID, OpenLDAP entryUUID или issuer-scoped OIDC sub; email/login запрещены как identity key.
3. `actor`, `requester`, `tenant`, `space`, `run_id` и effective scopes принимаются только из trusted server context. Request/tool payload не может их самоподтвердить. В `authz-context-v2` каждый `space_scopes[]` самостоятельно содержит `space_id`, `repository_id`, `policy_bundle_id`, обе full revisions, `group_snapshot {snapshot_id,captured_at,membership_sha256,groups[]}` и per-Space `revocation_epoch`; top-level bundle/groups для нескольких Spaces не существует.
4. Собственный API версионируется `/api/kb/v1`; canonical records имеют явный `schema_version`. Closed objects используют `additionalProperties: false`.
5. IDs не переиспользуются. Revisions — только полный lowercase SHA; ancestry определяет порядок, не lexicographic compare.
6. Для каждого duplicated `space_id`, `document_id`, `proposal_id`, `import_id`, `run_id` сервер до любого side effect требует равенства path/body и trusted scope. Mismatch получает `VALIDATION_ERROR` либо anti-enumeration `NOT_FOUND` и ноль writes. Body/header idempotency keys равны; decision дополнительно требует `decision_id == body key == header`. Tool adapter строит route из одного canonical input, независимые route args не принимаются.
7. Обязательные equality/cross-field правила опубликованы в `x-contract-invariants` в [OpenAPI](contracts/openapi.yaml) и schemas; semantic validator обязателен наряду с JSON Schema. Полный canonical↔projection mapping находится в [projection-mapping.md](contracts/projection-mapping.md).

### 4.2. Idempotency каждой mutation

Каждая mutation, включая draft/propose/decision/import/export/cutover, dry-run staging, webhook intake и internal CI status, требует `Idempotency-Key`.

GO связывает key с:

```text
verified actor/service identity
+ normalized operationId/route template и concrete path parameters
+ SHA-256(normalized payload)
```

Normalized payload сериализуется детерминированно после schema validation; PROPOSED canonicalization — JCS RFC 8785, UTF-8. Body `idempotency_key`, если есть, совпадает с header. Для decision команды key равен UUID `decision_id`. До insert/side effect GO выполняет **global key-registry lookup по `Idempotency-Key`** и сравнивает actor, route, concrete path и payload; PK `(actor,route,key)` сам по себе не заменяет этот guard и нужен отдельный key registry/unique guard в projection.

- Повтор того же actor+route+payload+key возвращает тот же durable result/reference без нового side effect.
- Тот же key с другим actor, route или payload даёт `IDEMPOTENCY_KEY_REUSED` и ноль новых writes.
- Изменённое содержимое — новая операция/ProposalVersion, а не reuse key.
- До external merge timeout retry возможен только с тем же key и payload. После `merge_attempted` сначала обязателен reconciliation; новый key/decision ID для маскировки timeout запрещён.
- Дополнительный Git backstop: `(repository_id,target_branch,proposal_sha)` возвращает уже проверенный результат, а `unique(decision_id)` не допускает двух decision outcomes.
- Replay retention — UNKNOWN owner decision. Git-derived dedupe/recovery не зависит от бессрочной DB history.

### 4.3. Errors и anti-enumeration

Машинная ошибка: `{code,message,request_id,details?,retryable}`. `details` — только sanitized scalars без raw content/secrets. Существование protected object скрывается через `NOT_FOUND` там, где denial сам раскрыл бы информацию.

| Code | Обязательная семантика |
| --- | --- |
| `STALE_BASE` | Target HEAD не равен base; ноль main writes, требуется новая proposal от fresh HEAD |
| `PROPOSAL_VERSION_MISMATCH` | Expected/source SHA не совпал; старый approval/command не применяется |
| `REVISION_CONFLICT` | History cursor/head, root/parent ancestry или exact restore revision противоречат Git; restore выполняется только через новый revert-MR |
| `PATCH_AMBIGUOUS` | Ноль или несколько matches; patch не применяется |
| `POLICY_REVISION_MISMATCH` | Access/approval не из одного согласованного bundle; sensitive operation остановлена |
| `APPROVER_CONFLICT` | Approver совпал с author/version_author/requester либо потерял group/path role |
| `DECISION_INVALID` | Note/tag/hash/target/trailer mismatch; merge запрещён, quarantine |
| `RECOVERY_REQUIRED` | Все новые merges target заблокированы до conclusive reconciliation |
| `AUTHZ_CONTEXT_STALE` / `GROUP_SNAPSHOT_STALE` | Payload не выдаётся; сначала refresh/recheck |
| `INDEX_NOT_READY` | Нет validated active published snapshot; preflight/partial не обслуживает retrieval |
| `STALE_INDEX_CANDIDATE` | Candidate отклонён; historical content молча не подставляется |
| `DEPENDENCY_CLOSURE_MISMATCH` | Incremental publication запрещена; расширить closure или full rebuild |
| `SECURITY_REJECTED` / `PII_REVIEW_REQUIRED` | Input не попадает в corpus до закрытия соответствующего barrier |
| `UPSTREAM_UNAVAILABLE` | Retryability зависит от операции; merge outcome не объявляется failed по timeout |
| `LIMIT_EXCEEDED` | Применить explicit bounds; mutation не выполняется, read возвращает truncation только по контракту |

### 4.4. Cursor, truncation и limits

- List/search/read/links/history/review queues используют bounded `limit` и opaque cursor. Cursor связывается с normalized query, effective scope, полным per-Space набором snapshots/profiles, policy bundles/revisions, group snapshots и revocation epochs плюс actor epoch.
- Response содержит `truncation.truncated`, `reason`, `next_cursor`; direct read дополнительно ограничивает characters/bytes и передаёт section/occurrence для repeated headings. `truncated=false` требует `reason=none,next_cursor=null`; `truncated=true` требует non-none reason и non-null next cursor.
- Одно-Space cursor chain не смешивает snapshots. Multi-Space search fan-out сохраняет весь ordered per-Space набор на каждой странице; потеря/подмена хотя бы одного descriptor или epoch даёт explicit stale error, а не усечённый контекст.
- Revocation/stale policy инвалидирует cursor. Cursor не является credential и не сохраняет доступ после expiry.
- Numeric schema limits — PROPOSED exchange bounds, не production SLA/capacity commitments. Unlimited reads, source queries и export batches запрещены.

## 5. Cutover: первичная публикация под freeze

Детали Git protections: [gitlab-integration.md](contracts/gitlab-integration.md). Источники и dry-run: [source-storage-integration.md](contracts/source-storage-integration.md).

1. Согласовать repository=Space perimeter, source corpus, owner/data profile. Production corpus до этого не создаётся.
2. Выполнить import dry-run: deterministic path→ID map, provenance, links/anchors, attachment manifests, original/extracted hashes, losses/errors/security/PII/media gates. Canonical writes отсутствуют.
3. Допустить controlled engineering bulk push **только** в unpublished `main`, при закрытом пользовательском доступе и отсутствии published index. Per-page MR в этой ограниченной фазе не требуется.
4. Зафиксировать human validation sign-off и CutoverRecord: Space/repository, exact `cutover_sha/main_sha`, validation evidence, sign-off actor stable ID, UTC timestamp.
5. Включить **write freeze первым** и повторно проверить `HEAD == cutover_sha`. При mismatch остановиться; нельзя подписать один corpus, а активировать другой.
6. Создать protected cutover/validation tag и MR-only rules. Direct push закрыт для людей и всех bots; только merge service identity GO имеет merge permission.
7. Построить full **inactive preflight** exact `cutover_sha`: eligibility, exact+semantic, dependency closure, attachments/media и negative ACL checks. Обязательно `snapshot_sha == cutover_sha`, `purpose=cutover_preflight`, `serving_allowed=false`, state никогда не `active`. Preflight никогда не обслуживает retrieval.
8. После successful preflight создать **отдельные published run и non-preflight descriptor с новыми `run_id` и `snapshot_id`**, повторно полностью validated на том же SHA: `cutover_sha == main_sha == preflight.snapshot_sha == preflight.cutover_sha == published.snapshot_sha`. Preflight остаётся immutable non-serving; published имеет `purpose=published,is_preflight=false,state=active,serving_allowed=true` и все non-null ready hashes. Единственный writer сериализует publication **per Space+profile** и атомарно делает CAS по expected current pointer/publication fence + latest Git ancestry + exact validated run/snapshot; stale owner обновляет ноль rows. Затем GO активирует Space и пользовательский доступ. Обратный порядок запрещён.
9. После cutover любые managed changes идут через GO/MR/human merge. Исправления и restore — reviewed/revert MR, без history rewrite или возврата к bulk bypass.

Crash/replay идемпотентен по Space+`cutover_sha` только при сохранённом freeze и неизменном HEAD. Смена HEAD требует нового CutoverRecord, sign-off и preflight. До pointer+activation доступ остаётся закрыт.

## 6. Draft → propose → edit → review → decision → merge

### 6.1. Draft и ProposalVersion

1. UI получает authorized canonical read с exact `base_sha`. Agent получает тот же revision через bounded read.
2. Human autosave вызывает GO save-to-branch с idempotency; `main` не меняется, статус `draft`. Unsaved browser buffer не считается durable draft.
3. Create/edit proposal принимает exact base, supported single-page content/patch, rationale/evidence. Agent first vertical slice — только curated single-page body create и `AgentAnchoredPatchChange` с required section; `WholeDocumentChange`, front matter/origin/attachments/archive/access, `editProposalVersion` ему недоступны даже direct OpenAPI/call_tool. Human whole-document replacement и `editProposalVersion` — отдельные browser+CSRF operations.
4. GO проверяет author capability, source-managed local-edit prohibition, path/Unicode/front matter/stable IDs/links/attachments и patch uniqueness независимо от input schema. Whole-document replacement требует exact base и полного review; forbidden agent diff отклоняется GO без записи.
5. GO создаёт attributed branch commit, MR и append-only [ProposalRecord](contracts/proposal-record.schema.json) для `(proposal_id,proposal_sha)`. `main` остаётся неизменным; статус `in_review`.
6. Каждый record содержит `author_stable_id`, `version_author_stable_id`, `requester_stable_id`, `actor_type`, optional trusted `run_id`, rationale/evidence, exact base/proposal, idempotency key/payload hash и server timestamp. Bot/service identity не замещает principals.
7. Edit/rebase создаёт новый `proposal_sha`, `proposal_version_id`, `version_author_stable_id` и новый record. Прежний approval недействителен. Stale commands получают `PROPOSAL_VERSION_MISMATCH`.

### 6.2. Review

Review UI показывает exact base/proposal, «было/стало», все front matter changes, structure/tree, stable links, attachment additions/removals/revisions, media warnings, rationale/evidence и author/version_author/requester/run. Evidence visibility авторизуется отдельно.

Недостоверный diff/preview, XSS-risk rendering или скрытое machine-significant изменение блокирует merge. Automatic conflict merge и повторная LLM-генерация при apply запрещены.

MVP требует одного eligible approver из актуальной external group и path-scoped [approval policy](contracts/approval-policy.schema.json). `rule_id` и normalized prefixes уникальны; duplicate path (включая trailing-separator/NFC/NFD variants) делает bundle invalid. Для документа выбирается ровно одно **longest-normalized-prefix** правило на segment boundary; только его groups eligible, менее специфичные `/` или parent rules не расширяют approver set. Approver не совпадает ни с `author_stable_id`, ни с `version_author_stable_id`, ни с `requester_stable_id`. CODEOWNERS остаётся engineering-only и не заменяет business policy.

`GET /documents/{document_id}/history` возвращает business-доступные exact revisions с ancestry/cursor для restore→revert-MR. `GET /spaces/{space_id}/review-proposals` возвращает ACL-filtered group-assigned queue с exact base/proposal, policy revisions/group snapshot и truncation; GitLab user не требуется. Оба endpoint anti-enumeration safe.

### 6.3. Canonical DecisionRecord

До применения accept/reject/cancel GO создаёт один [DecisionRecord](contracts/decision-record.schema.json):

- UUID `decision_id`, proposal/repository/Space/target, exact `base_sha` и `proposal_sha`;
- `action = accepted|rejected|cancelled`, human `actor_stable_id`, UTC timestamp, rationale/evidence;
- `policy_bundle_id`, full `access_policy_revision` и `approval_policy_revision` из одного bundle;
- idempotency `payload_hash`, `record_sha256`, optional `supersedes_decision_id`.

PROPOSED hash: JCS UTF-8 record без `record_sha256`, SHA-256. Полный одинаковый JSON записывается:

1. в append-only structured MR note от GO — API/UI representation;
2. в protected annotated tag `kb-decisions/<decision_id>` на exact `proposal_sha` — Git-native durability anchor для accepted/rejected/cancelled.

Missing/mismatched note/tag, wrong target или hash делает decision `invalid`. Исправление — новый `decision_id` со `supersedes_decision_id`; старый JSON не редактируется. `note_id` назначается GitLab вне record и связывается через trailer/export. Физическая append-only/WORM capability GitLab — UNKNOWN T00.

Accepted merge commit имеет trailers:

```text
Decision-ID: <decision_id>
Decision-Note-ID: <canonical MR note ID>
Decision-Hash: <record_sha256>
Approved-by: <approver stable_id>
```

Reject/cancel создают тот же durable note+tag и закрывают MR без merge commit/main write. Все три actions попадают в decisions manifest export.

### 6.4. Human accept и merge

1. Human decision endpoint доступен только browser/session+CSRF и fresh approver capability; agent/connector routes не имеют этого полномочия.
2. GO берёт per-`(repository_id,target_branch)` advisory lock с owner/fencing token. Lock не охватывает review/LLM.
3. Под lock GO повторно проверяет groups, stable actor, Space/path approver, self-approval prohibition, один policy bundle+revisions, MR open, exact source `proposal_sha`, `target HEAD == base_sha`, полный review и отсутствие unresolved accept/recovery barrier.
4. Mismatch даёт forbidden/conflict/version error и ноль writes в `main`.
5. GO сохраняет note+tag DecisionRecord с `recorded accepted` и `attempts=[]`, затем в одной DB transaction переводит decision в `merge_attempted`, создаёт первую реальную merge operation и устанавливает durable per-target `recovery_required` с owner/fencing metadata. До этой transaction synthetic attempt/no-merge claim не создаётся.
6. Только merge service identity GO выполняет external exact-SHA merge. Squash, automatic rebase и fast-forward запрещены; создаётся настоящий merge commit.
7. Merge commit обязан находиться в target ancestry и иметь **first parent = `base_sha`, second parent = `proposal_sha`**, а также четыре совпадающих trailer.
8. Независимо от HTTP response GO читает GitLab и проверяет parents/trailers/note/tag/hash/Approved-by. Только это подтверждает `merged` и `merge_commit_sha`.
9. Повтор того же `decision_id` или уже применённого `(repository_id,target_branch,proposal_sha)` возвращает существующий Git-derived result без второго merge.
10. После conclusive target verification recovery barrier завершается. Webhook/reconciliation инициирует index отдельно; merge не ждёт indexing.

### 6.5. Decision outcome, projection mapping и retry

Canonical `accepted/rejected/cancelled` маппируются в operational `accept/reject/cancel` без изменения смысла. Integrity-valid `rejected` и `cancelled` имеют durable note+tag, verified MR closure и `DecisionResult.state=recorded`, **`attempts=[]`**, decision-level `reconciliation_evidence`, no merge/recovery/quarantine и не создают merge operation. В export их derived outcomes соответственно `rejected`/`cancelled`; это не подмена canonical action или добавление нового decision state. Missing/mismatched note/tag для любого action даёт `invalid` и не может выдаваться за normal reject/cancel closure. Полная таблица: [projection-mapping.md](contracts/projection-mapping.md).

Для accepted сохраняется пользовательский graph `recorded → merge_attempted → merged/failed/conflicted/invalid`. `DecisionResult.state=quarantined` не существует: quarantine — `state=merge_attempted + recovery_required=true + target_quarantined=true`. `DecisionResult.attempts[]` и export `publication.attempts[]` содержат только реальные durable merge operations, ordered oldest→newest; последняя определяет attempt outcome. `recorded accepted` имеет `attempts=[]` и не получает `no_merge_proven`: после note+tag, но до первой DB transaction допускается `recovery_required/target_quarantined=true` без утверждения, что merge отсутствует. `merged` требует `merge_proof` с merge SHA, repository/target ancestry, first/second parents, raw commit hash, четырьмя trailers и note/tag/hash verification; `DECISION_RESULT_MERGE_LINKAGE` связывает proof с parent decision/base/proposal/note/tag/actor, SHA без proof недостаточен.

| Outcome | Attempt/evidence | Retry/replay |
| --- | --- | --- |
| `recorded` accepted | `attempts=[]`; note+tag есть, real merge operation ещё не зарегистрирована; no-merge не утверждается | `retryable=false`; crash window допускает recovery/quarantine; replay не создаёт attempt |
| `merge_attempted` | Nonempty attempts; last `prepared/in_flight/completed/unknown`, `no_merge_proven=false`; target barrier | Unknown/quarantined, `retryable=false`, blind retry запрещён |
| `merged` | Last real attempt `request_state=completed`, полный merge proof | `retryable=false`; replay возвращает тот же Git-derived outcome |
| `failed` | Last real attempt `request_state=completed + no_merge_proven=true + per-attempt reconciliation_evidence` | `retryable=true` допустимо только после этих доказательств и fresh preconditions |
| `conflicted` | Conclusive conflict, no merge | Terminal, `retryable=false`; нужна новая ProposalVersion/review |
| `invalid` | Integrity mismatch; unknown merge не считается отсутствующим | Terminal, `retryable=false`; correction новый UUID+supersedes после reconciliation |

Identical replay одного `decision_id` не создаёт attempt и возвращает один текущий Git-derived outcome. Только recovery coordinator может после conclusive `failed` выполнить guarded recovery retry: новый `attempt_id`, **тот же `decision_id`**, exact base/proposal, fresh policy/group/HEAD checks и durable barrier. Это не HTTP replay и не новый decision outcome fork. `conflicted`/`invalid` такого перехода не имеют.

## 7. Crash recovery и timeout reconciliation (spec §7.1, §7.3)

`recovery_required` блокирует **все новые merges target**, не только повтор same MR. Потеря lock, fencing, timeout или новый GO owner не снимают barrier. Новый owner до нового decision сканирует unresolved accept DecisionRecords, потому что crash мог произойти между note/tag и DB transaction. Advisory lock не доказывает отмену уже отправленного GitLab request.

| Точка crash / сбой | Доказанное состояние | Обязательное восстановление | Запрещено |
| --- | --- | --- | --- |
| До записи note/tag | Canonical decision отсутствует; merge call ещё не допускался. Только одно representation = partial/mismatch | Повтор human apply с тем же idempotency context после fresh checks. Partial record перевести в invalid recovery | Merge по partial record; редактирование старого JSON |
| После durable note+tag, до merge | Decision существует как `recorded accepted`, `attempts=[]`; наличие merge и DB row не доказаны, no-merge не утверждается | Перед любым новым merge target восстановить `recovery_required/target_quarantined`; найти merge/request по decision/proposal. При доказанном отсутствии external call очистить recovery, оставив `attempts=[]`. При наличии real external attempt восстановить operation; `failed` только после request completion+no-merge evidence. Guarded recovery retry создаёт новый real attempt с тем же `decision_id` и fresh preconditions | Synthetic `not_started/no_merge_proven` attempt; новый decision ID для retry; replay как запуск attempt; другой merge target до reconciliation |
| Во время GitLab call / timeout | Outcome unknown; `merge_attempted` и barrier уже durable | Блокировать target; target-wide reconciliation MR/main/audit. `merged` только после parent/trailer/note/tag verification. Недоказуемый outcome оставить quarantined | Blind retry, снятие barrier по timeout, lock handover как разрешение нового merge |
| После принятия merge GitLab, до DB projection | Merge commit и note+tag — канон; projection отстает | Найти commit, проверить все связи, записать Git-derived `merged`, инициировать/reconcile index | Второй merge call; `failed` только из-за отсутствия DB row |
| Полная потеря `kb_ops` | Пустая DB не доказывает ни успех, ни отсутствие external call | Global bootstrap merge freeze; rebuild из protected tags/notes/MR/target histories/source registry; conservative per-target barriers; открытие только после target-wide conclusive reconciliation | Немедленно разрешить merges из-за пустой DB; доверять transient projection |

`failed` допустим только после Git-derived no-merge доказательства **и** завершения external request; лишь тогда `retryable` может быть true. `conflicted` и `invalid` terminal и никогда не retryable. `invalid` требует quarantine при любом недоказанном external outcome. Недоказуемый timeout остаётся `merge_attempted`+quarantined без срока автоматического «лечения».

## 8. Webhook ingestion → CI/index → retrieval

### 8.1. Event protocol

Machine envelopes и payloads: [events.yaml](contracts/events.yaml).

1. GitLab adapter проверяет webhook authenticity/replay через target capabilities UNKNOWN T00 и передаёт verified event identity, repository и payload hash в GO. Webhook payload — подсказка, не proof merge/active revision.
2. GO сохраняет inbox с idempotency actor+route+payload, deduplicates provider event и читает текущее GitLab state. Фиксируется observed exact `main_sha` по Git ancestry.
3. GO отправляет `kb.index.requested.v1` с Space/repository/target, exact `main_sha`, `main_generation_id`, `index_profile_version`, reason и preflight marker.
4. CI read-only credential читает exact main/cutover snapshot. Только eligible published corpus либо inactive cutover preflight допускается. Pending/rejected branches, `inbox`, templates, service files и unverified critical media исключаются.
5. Full/incremental workers строят exact и semantic projections в inactive storage. Attachment/link/policy/extraction/media dependencies входят в transitive closure.
6. Incremental `ready/active` публикуется только при nonempty `closure.equivalence_evidence`: distinct full run+snapshot в conclusive canonical `ready/active`, `validated_at`, complete closure, `missing_inputs=[]`, exact+semantic hashes и совпадение Space/repository/target/main SHA/generation/profile/closure hash. Requested/failed/empty prerequisite отклоняется; иначе closure расширяется или выполняется full run.
7. Validator проверяет exact+semantic readiness, IDs, archive/delete, attachment revisions, media admission и negative ACL cases.
8. Только single CI/index writer сериализует publication **per `(space_id,profile_id)` across generations** (`profile_id` соответствует `index_profile_version`) и после полного validated run атомарно выполняет CAS по expected current pointer/publication fence + latest Git ancestry + exact validated run/snapshot. Per-generation lock alone недостаточен. Concurrent old/new publishers используют один Space/profile lock; stale owner получает zero rows, late run помечается superseded и не откатывает pointer.
9. At-least-once delivery использует dedupe, bounded retry, dead-letter. Periodic HEAD/index reconciliation ловит lost/invalid webhooks и CI outage. CI failure не откатывает canonical merge.

### 8.2. ACL и attachment events

- `kb.access_policy.changed.v1` несёт `changes[]` с независимым per-Space `{space_id,repository_id,policy_bundle_id,access_policy_revision,approval_policy_revision,group_snapshot,revocation_epoch}` и `change_set_sha256`. Общий bundle/snapshot для нескольких Spaces запрещён. Fresh deny применяется немедленно; reindex обновляет metadata асинхронно и не является revocation barrier.
- `kb.access.revoked.v1` инвалидирует contexts/cursors и закрывает live subscriptions. Новые tree/titles/snippets/chunks/files/history/export/tool payloads прекращаются.
- `kb.attachment.changed.v1` связывает exact document revision с immutable `{object_id,version,sha256,size,media_type,source_ref}`, media admission и Space ACL. Тот же event/index/reconciliation контур обязателен.
- Archive/delete применяется только через новый canonical snapshot. Удаление projection без canonical proof запрещено.

### 8.3. Index snapshot semantics

[index-snapshot-v1](contracts/index-snapshot.schema.json) явно различает:

| Поле | Не смешивать |
| --- | --- |
| `snapshot_sha` | Exact `main` commit всего snapshot |
| `document_revision_sha` | Commit версии конкретного документа; не alias snapshot SHA |
| `blob_sha` / `content_sha256` | Идентичность bytes/no-op; не proof published revision |
| `dependency_sha256` | Hash inputs, влияющих на index representation документа |
| `dependency_closure` / top-level `closure` | Полный transitive input set и proof full/incremental equivalence |
| `main_generation` | Git ancestry generation; history rewrite → новое поколение + full rebuild |
| `index_profile_version` | Независимая версия chunking/embedding/extraction semantics |
| `preflight` | Full inactive exact cutover run; `snapshot_sha=cutover_sha`, `serving_allowed=false`, нет active state |
| preflight→published | Разные run/snapshot IDs, отдельный published non-preflight descriptor на exact same SHA; preflight никогда не мутирует в active |
| `serving_allowed` | Только `state=active + purpose=published + is_preflight=false`; requested/ready/preflight не serving |
| Ready hashes | Exact/semantic ready требует non-null 64-hex projection hashes; active требует все document/dependency/closure hashes и `missing_inputs=[]` |
| History rewrite | Новая generation + full rebuild; active incremental при rewrite запрещён |
| Pointer CAS | Per-Space/profile serialization + expected fence/latest ancestry/validated run; stale overwrite обновляет ноль rows |

### 8.4. Exact+semantic retrieval и stale candidate

1. Search получает query/mode и optional narrowing scope; server пересекает его с fresh AuthzContext. Для каждого requested Space существует отдельный repository/bundle/revisions/group snapshot/epoch entry; иначе весь запрос или соответствующий scope fail closed без заимствования контекста.
2. Retrieval read-only выполняет **per-Space fan-out**: exact или semantic candidate query в active published snapshot/profile каждого Space независимо. `SearchPage.snapshots[]` содержит полный набор per-Space descriptors; item хранит `space_id+snapshot_id+snapshot_sha`, citation повторяет тот же Space/document/revision. Нельзя отправить лишние private chunks модели и отфильтровать позже или объединить результаты под одним global snapshot.
3. Для каждого candidate проверяются его собственный active snapshot, document revision, eligibility, dependency metadata, per-Space policy/group/epoch и fresh ACL до title/snippet/chunk/file/history exposure. Cursor повторяет весь ordered snapshot/policy набор.
4. Candidate с inactive/stale `document_revision_sha`, archived/deleted content или revoked access отклоняется `STALE_INDEX_CANDIDATE`/`NOT_FOUND`.
5. Historical content не подставляется молча. Selected **current canonical read** — отдельная GO operation с новым revision/authorization; explicit historical read также отдельно маркируется и авторизуется.
6. Direct short-page/section read идёт через GO без обязательного global search и возвращает bounds/cursor/truncation/citations.
7. GitLab-outage stale read mode выключен по умолчанию и требует отдельного ADR. `live_operational` facts не извлекаются из устаревшего wiki snapshot.

## 9. Import и source synchronization

Полный протокол: [source-storage-integration.md](contracts/source-storage-integration.md).

- **Dry-run** принимает immutable source version/hash + normalized config hash, возвращает deterministic path→ID/provenance/links/attachments/errors и `canonical_writes=false`. Он не создаёт branch/MR/main commit/active index/merged cursor.
- **Commit** использует manifest hash и expected base. До cutover допускается только controlled unpublished staging/bulk path; после cutover всегда создаётся GO proposal с human review/merge. Повтор по hash/version — no-op или существующий outstanding proposal.
- `migrated`: старый источник не writer. `source_managed`: local edits запрещает GO, source updates только MR+human merge. `curated`: previous imported base + current curated + incoming сравниваются без overwrite; конфликт явный. `live_operational`: только `readLiveOperational` typed bounded read-only result с `snapshot_time`, immutable source version/hash, `canonical_writes=proposal_cursor_effects=index_writes=false`; нет wiki/MR/document/index/seen/proposed/merged cursor.
- Versioned `document-front-matter-v2` является отдельным schema contract change, предусмотренным content-standard v2.3 §4.4, и явно добавляет canonical `links[]` по target document UUID и `valid_until` (`date|null`), сохраняя `origin` как provenance и запрещая `access`/`live_operational`. `migrated` и `source_managed` требуют origin; `origin.ownership_mode` всегда равен outer mode. `DOC-0001` source IDs сохраняются без lowercase normalization. Markdown body links и front matter links проецируются в один stable-ID graph; resolved target UUID обязан совпадать с target projection.
- [docops-review-metadata-v1](contracts/docops-review-metadata.schema.json) — revision-bound projection canonical valid_until/provenance, не второй канон. Future date → `scheduled`, expired по server UTC → `due` + queue/`kb.docops.review_requested.v1`, removed → `review_required=false,valid_until=null`. `GET /spaces/{space_id}/docops/review-queue` авторизует каждый item; expiry не даёт access и не архивирует автоматически.
- `archived=true` требует `archive`, а наличие `archive` требует `archived=true`. Restore — reviewed revision `archived=false` без archive. Replacement target должен быть другим active document в same Space; descendants не архивируются/не удаляются неявно — каждый обрабатывается в том же reviewed MR или получает repaired parent/link.
- Для каждого source object не более одного outstanding proposal. `seen` продвигается после durable observation, `proposed` — после durable MR+ProposalRecord, `merged` — только после проверенного Git merge. Reject/conflict/timeout/indexing не продвигают `merged`. `seen/proposed/merged` version+hash существуют только парами; `proposal_pending` требует proposed pair + outstanding ID/SHA, а `merged` и остальные non-pending states очищают оба outstanding fields. Stable merged proposal audit восстанавливается из merge evidence, не из outstanding cursor.
- Source deletion создаёт tombstone/obsolete review, не молчаливое deletion. Traversal, symlinks, executable HTML/MDX, secrets, oversized/decompression inputs отклоняются.

## 10. Export, backup и restore closure

Full export доступен только human/service operational context с export permission на Space **и всю его историю**, fresh group recheck и повторной авторизацией каждого batch. Обычный agent/search/read credential не даёт clone.

[export-manifest-v2](contracts/export-manifest.schema.json) требует:

1. согласованный `git clone` exact repository snapshot, единый format ID `git_clone_with_manifests`, явные refs с full object SHA, peeled target и SHA-256 exported raw object bytes;
2. IDs/tree/links/origin и document revision/content hashes; обязательный `documentEntry.valid_until`, равный canonical front-matter-v2 на exact revision и входящий в documents manifest/restore roundtrip;
3. protected cutover/decision tag refs, включая `refs/tags/kb-decisions/<uuid>` с `protected=true`;
4. **decisions manifest** для accepted/rejected/cancelled: полный DecisionRecord, `record_sha256`, MR note ID/body hash/`canonical_json_sha256`/metadata ref, tag object/target/raw content и тот же canonical JSON hash. `body_sha256`, `record_sha256` (record без hash field) и `canonical_json_sha256` (полный record включая hash field) не смешиваются;
5. explicit `publication.outcome + real attempts + recovery evidence` для каждого decision. Accepted `recorded/merge_attempted/failed/conflicted/invalid` экспортируется **без merge** с recovery evidence; `recorded accepted` имеет `attempts=[]` без no-merge claim, `rejected/cancelled` — `attempts=[]` и verified decision-level MR closure без merge operation. Только `merged` требует merge commit SHA/proof: repository/target ancestry, first/second parents, raw commit hash, все `Decision-ID/Decision-Note-ID/Decision-Hash/Approved-by` trailers и canonical note/tag/hash linkage. Cross-proposal note/tag/hash/merge linkage запрещён;
6. **assets manifest**: immutable object/version/storage ref, content SHA-256, size, media type, source ref и export status; mutable current URL недопустим. `exported_object_sha256` обязателен только для `exported`, запрещён для `missing/rejected` и равен attachment+actual bytes для exported;
7. policy bundle+revisions, policy content hashes и grants mapping hash;
8. closure hashes для refs/documents/decisions/assets/policies/repository tree. `complete=true` требует `decisions_complete=assets_complete=authorization_complete=true`, пустой `missing[]`, все assets `exported`, полный decisions closure и успешную fresh authorization каждого batch. Любой missing/rejected asset или пропущенный decision/batch делает `complete=false` и добавляет stable missing entry.

`ExportJob.state=ready` допустим только при наличии manifest со всеми complete flags и closure выше; `{export_id,state=ready}` без manifest невалиден. Terminal `incomplete` содержит `closure.complete=false` и error/missing evidence, `failed` не выдаёт complete claim. Ни ready, ни incomplete не разрешает missing assets маскировать пустым `missing[]`.

Manifest не заменяет canonical note+tag; он сохраняет GitLab-only MR metadata и позволяет проверить closure. Secrets, private chats и неутверждённые payloads исключены. Filtered export/history removal/hard purge — отдельный privileged workflow, в MVP отключён.

Backup включает Git mirror со всеми refs, GitLab metadata, object storage, config и secrets policy. Restore drill: clone+manifests → clean dedicated instance → explicit policy/grant mapping → conservative `kb_ops` recovery/rebuild → full `kb_index` rebuild → closure/parent/trailer/note/tag/assets checks. RPO/RTO и retention — UNKNOWN owner decisions.

## 11. Identity и revocation summary

Полный контракт: [identity-integration.md](contracts/identity-integration.md).

- Upstream LDAP/OIDC authentication и JIT переиспользуются; собственный auth protocol/LDAP/OIDC client не создаётся.
- Stable ID не зависит от login/email rename. JIT не создаёт GitLab business users; review queues назначаются группам.
- Access+approval policies активируются атомарно как один bundle **для каждого Space** с полными SHA. Частичный bundle не выдаётся; per-Space context хранит собственные bundle/revisions/group snapshot/epoch. Approval prefixes проходят duplicate validation и longest-normalized-prefix selection.
- Groups обновляются не реже 15 минут; merge/export/private page требуют fresh recheck именно нужного per-Space snapshot. Long operations обновляют AuthzContext перед каждым payload/batch.
- Provider outage не разрешает безграничный cached allow. Sensitive operations fail closed.
- Revocation SLO ≤ 30 минут; revoke закрывает live subscriptions и предотвращает новые payloads. Уже доставленный browser/model текст не считается reversible.
- LDAP read-only bind, LDAPS/StartTLS, nested AD groups и обязательный отказ пустого пароля, включая CVE-2026-44551 regression, — UNKNOWN T00 до pinned baseline test.

## 12. Managed inference summary

Полный контракт: [inference-integration.md](contracts/inference-integration.md).

- Все chat/task/title/summary/extraction/embedding/reranker/OCR/vision calls идут через managed Open WebUI model connections и approved provider inventory. Endpoints/model IDs/dimensions/versions — configuration UNKNOWN T00.
- `strict` — default: owner + completed data barrier до corpus; каждое PII hit получает human disposition, unresolved блокирует admission.
- `pii_permitted` требует documented legal basis, собственный согласованный hoster.ai/client inference и усиленные access/retention rules; внешний PII egress запрещён.
- Unplanned provider fallback запрещён во всех profiles, включая auxiliary/indexing calls. Fallback возможен только как явно inventoried и profile-approved config, не как скрытый retry на другого provider.
- Provider credentials принадлежат model connection/deployment secrets и не передаются agent/tool/document. Raw private content допустим только в авторизованном payload внутри profile; logs/audit/unapproved export его не содержат.
- Streaming, sequential/parallel tools, malformed args, cancellation/retry/timeouts и cold offline startup проверяются на реальном согласованном endpoint. Без credentials результат BLOCKED; mocks не считаются PASS.

## 13. Security, observability и обязательные проверки

### 13.1. Security invariants

- Default private; tree/titles/snippets/chunks/files/history/export/evidence авторизуются до payload, включая provider payload.
- Preview защищает от XSS/executable HTML/MDX и раскрывает hidden front matter/link/attachment changes.
- Attachment revision наследует Space ACL и связывается с document revision; automatic media description маркируется и ссылается на original. Critical/handwritten media без human transcription/verification не индексируется.
- CI не делает post-merge push производных files в `main`. `INDEX.md` — build artifact либо часть того же reviewed MR.
- Hard purge/history rewrite, admin break-glass, page-level ACL, multiple approvers/quorum, realtime collab, universal two-way sync, agent bulk/subtree/attachment operations — DEFERRED.
- Logs/traces содержат IDs, hashes, revisions, request/run/proposal/decision IDs и sanitized codes, но не raw documents/private queries/evidence text/tokens/bind passwords/provider payloads.

### 13.2. Корреляция и alerts

Сквозной trace: `request_id → run_id? → proposal_id/proposal_sha → decision_id → merge_commit_sha → index run/snapshot_sha`. Дополнительно фиксируются actor stable ID, policy bundle+revisions, generation/profile, source versions и export ID.

Обязательные сигналы: merge result/latency, lock wait/fencing, `recovery_required` age/unresolved decisions, decision integrity mismatch, webhook/CI lag/dead-letter, HEAD/index ancestry drift, stale candidate denials, revocation propagation/subscription closure, source seen/proposed/merged lag, export closure failures, TTFT и full response отдельно. Численные thresholds, кроме revocation ≤30 минут и group refresh ≤15 минут, не выдумываются.

### 13.3. Контрактные и integration проверки

После T00/T01, на existing tooling. Полный machine-readable набор CF-01–CF-30 и semantic/consumer assertions: [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml); enum/state mappings: [projection-mapping.md](contracts/projection-mapping.md). Сейчас это DESIGN_NOT_EXECUTED, не test evidence.

1. Closed schema compatibility, malformed/unknown fields, full SHA, path/Unicode/traversal, path/body equality, `x-contract-invariants`, cursor/truncation и global cross-actor/cross-route idempotency replay matrices.
2. Два Spaces с разными repositories/bundles/revisions/group snapshots/epochs; per-Space search fan-out/cursor context; duplicate approval prefixes и `/` vs `/pricing`; NFC/NFD/`..` roundtrips.
3. Archive inverse/restore/replacement/descendants, outer/inner origin mismatch, `DOC-0001`, stable links/swapped IDs, valid_until expired/future/removed и DocOps queue/event.
4. Agent restricted patch и запреты `editProposalVersion`/whole-document/merge/grants/archive/attachments через direct/deferred/note/automation/channel/OpenAPI/call_tool; connector dry-run/post-cutover proposal/pre-cutover denial; GitLab bot merge attempt отклоняется самим GitLab.
5. History→restore→revert-MR и group review/DocOps queues с exact revisions, longest-prefix assignment, truncation и anti-enumeration.
6. Два independent clients/two proposals, double accept, stale SHA, new commit/rebase, self-approval тремя способами, revoked approver; missing/mismatched note/tag, wrong target/hash/trailer/parent, squash/rebase/FF.
7. Decision accepted recorded/merge_attempted/merged/failed/conflicted/invalid, reject/cancel mappings, merged SHA+proof, failed только после request completion+no-merge, guarded same-decision recovery retry, terminal conflicted/invalid и same-command replay без new attempt.
8. Fault injection каждой строки §7, request accepted+response lost, lock handover, late response, полная DB loss.
9. Preflight wrong SHA/serving/null hashes/rewrite-incremental; separate same-SHA preflight→published IDs; concurrent old/new generation publication с per-Space/profile CAS; duplicate/out-of-order/lost webhook и CI outage.
10. Cross-Space IDOR/composite associations, wrong base/proposal/target recovery, missing approval revision/equivalence/profile linkage и revocation между candidate/payload/review/merge/export/live stream.
11. Import malicious fixtures, repeat/resume, one outstanding proposal, cursor crash points, curated conflict/deletion и live_operational typed read без document/proposal/index/cursor effects.
12. Complete/ready export с decisions+assets+authorization closure, accepted-before-merge, missing/rejected assets, canonical note/tag/body/record hashes и clone→clean restore; mixed import/truncation/range conditionals.
13. Real sandbox GitLab/IdP/PostgreSQL/CI и реальный approved hoster.ai endpoint там, где требуется integration evidence. Mocks допустимы для unit state machines, но не являются integration PASS.

## 14. T00 stop conditions и незакрытые решения

G0/design останавливается, если pinned baseline не позволяет доказать merge-only-GO/no-direct-push, exact-SHA real merge commits с required trailers/parents, protected annotated decision tags и MR note linkage/export, stable identity/group recheck/revocation, ACL/SHA-safe retrieval или conclusive timeout reconciliation. Нужен adapter/другой design через ADR и owner review; инвариант молча не ослабляется.

Отдельно остаются UNKNOWN: repository naming/group layout/provisioning, production corpus, editor, retrieval backend/parameters, models/dimensions, source connector и supported formats, object-store layout, RPO/RTO, retention, idempotency replay retention, latency/freshness/quality/capacity/budget thresholds. Этот пакет не выбирает их.
