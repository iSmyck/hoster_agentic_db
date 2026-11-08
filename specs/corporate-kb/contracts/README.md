# Corporate KB — integration contracts

**Статус:** DESIGN / PROPOSED после T00 DONE и G0 APPROVED. Контракты не являются production approval или implementation/integration PASS и не подтверждают невыполненные возможности Open WebUI, GitLab, CI, IdP, object storage или hoster.ai studio.

Главный authority: [ARCHITECTURE-SPINE.md](../architecture-spine.md), AD-1–AD-16. Требования R01–R18 и I01–I14 из [spec.md](../spec.md) имеют приоритет. Общий integration narrative: [integration.md](../integration.md).

## 1. Правила чтения

- **REQUIREMENT** — обязательный архитектурный инвариант принятых AD/ADR.
- **PROPOSED / DESIGN** — детализация собственных GO/tool/event/schema contracts, подлежащая design review и T01 contract tests.
- **UNKNOWN** — проверяется на pinned baseline в T00 либо требует решения владельца.
- **DEFERRED** — не реализуется в MVP без новых требований и ADR.

T00 закрепил Open WebUI commit/tag, GitLab version/edition, code paths, Git object format и TipTap adapter direction. Upstream routes, session cookie и фактический CSRF mechanism, token types, webhook headers, CI transport, production retrieval parameters, model IDs/dimensions, source connector и object-store layout остаются implementation/config UNKNOWN по соответствующим gates. `/api/kb/v1` и описанные ниже routes относятся только к собственному GO API. Они не выдумывают upstream routes.

## 2. Карта артефактов

### API, tools и events

| Файл | Назначение |
| --- | --- |
| [openapi.yaml](openapi.yaml) | OpenAPI 3.1 собственного GO API `/api/kb/v1`: browser/human, restricted agent, connector, internal CI, webhook, history/review/DocOps/source boundaries; correction-task create/get/resolve/cancel; machine invariants, idempotency, errors, cursor/truncation/limits |
| [agent-tools.yaml](agent-tools.yaml) | Только read/search/propose tools с отдельной restricted body-patch schema; trusted run/actor/per-Space scope и запрет privileged channels |
| [events.yaml](events.yaml) | At-least-once envelopes и payloads для GitLab→GO→CI, per-Space ACL, attachments, revocation, index status, source cursors, DocOps review |
| [projection-mapping.md](projection-mapping.md) | Versioned canonical↔API↔event↔DB enum/state/ID/path mapping |
| [t01-contract-tests.yaml](t01-contract-tests.yaml) | Machine-readable DESIGN_NOT_EXECUTED T01 vectors CF-01–CF-30 и consumer assertions |

### JSON Schema 2020-12

| Schema | Канонический смысл / основной consumer |
| --- | --- |
| [front-matter.schema.json](front-matter.schema.json) | v2: stable UUID/tree, ownership+origin provenance, stable ID links, valid_until, двусторонний archive, immutable attachments; не источник ACL |
| [access-policy.schema.json](access-policy.schema.json) | Versioned Git mapping external groups → Space roles; default private, audited personal exceptions |
| [approval-policy.schema.json](approval-policy.schema.json) | External groups → path-scoped approver rules; один независим approver в MVP |
| [authz-context.schema.json](authz-context.schema.json) | v2: server-issued identity и независимые per-Space repository/policy bundle+revisions/group snapshot/epoch; не bearer credential |
| [proposal-record.schema.json](proposal-record.schema.json) | Append-only ProposalVersion: author/version_author/requester, actor/run, rationale/evidence, exact base/proposal, idempotency |
| [decision-record.schema.json](decision-record.schema.json) | Accept/reject/cancel canonical JSON, actor, policy bundle+revisions, record hash, supersedes |
| [index-snapshot.schema.json](index-snapshot.schema.json) | snapshot/document/content/dependency/closure/generation/profile/preflight semantics |
| [export-manifest.schema.json](export-manifest.schema.json) | Clone refs, documents, decisions note+tag+merge trailers, assets и closure hashes |
| [source-origin.schema.json](source-origin.schema.json) | Immutable source provenance, DOC-* IDs и previous imported base; operational cursors остаются в GO |
| [docops-review-metadata.schema.json](docops-review-metadata.schema.json) | Revision-bound projection canonical valid_until/provenance для review queue/events, без authorization effect |
| [docops-correction-task.schema.json](docops-correction-task.schema.json) | Closed `docops-correction-task-v1`: GO-owned kb_ops operational record, exact revision, trusted actor/policy owner, evidence hash, optional linked MR, idempotency/CAS и `open/in_review/resolved/cancelled`; не canonical content/DecisionRecord |

### Интеграционные протоколы

| Документ | Содержимое |
| --- | --- |
| [gitlab-integration.md](gitlab-integration.md) | Repository=Space, cutover, MR/Decision/merge, crash recovery (spec §7.1/§7.3), webhooks, export refs |
| [identity-integration.md](identity-integration.md) | LDAP/OIDC, JIT, stable ID, group recheck, AuthzContext, grants, revocation |
| [inference-integration.md](inference-integration.md) | Managed model connections, strict/pii_permitted, inventory, no fallback, bounded tools |
| [source-storage-integration.md](source-storage-integration.md) | Import dry-run/commit, ownership modes, cursors, immutable assets, live_operational read-only |
| [docops-correction-api.md](docops-correction-api.md) | Correction-task lifecycle, trusted actor/owner, create/get/resolve/cancel, governed MR/no-MR resolution, idempotency/errors, kb_ops backup/restore/rebuild semantics |

## 3. Общие машинные соглашения

### 3.1. Strictness и совместимость

- Все закрытые canonical/API objects имеют `additionalProperties: false`. Исключения сознательно ограничены version-tolerant `provider_payload` в webhook input, sanitized scalar `Error.details` и generic envelope `payload`, который обязателен к проверке по event-specific closed schema.
- Любое новое поле в closed canonical record требует нового `schema_version` и migration/compatibility decision. Нельзя молча добавлять необязательные поля в `proposal-record-v1` или `decision-record-v1`: это меняет payload/hash и note/tag equality.
- `format: uuid` и `format: date-time` являются assertion formats для contract validation. Время — UTC RFC 3339; текст — UTF-8; enums — lower_snake_case, кроме обязательных Git trailers.
- Limits в схемах — **PROPOSED bounded exchange limits**, не production SLA и не owner-approved capacity. Их уменьшение/увеличение требует compatibility review; unlimited mode не создаётся.
- Версии библиотек для validation не выбраны. Проверка пакета использует локально доступные parsers и не требует установки зависимостей.

### 3.2. IDs, paths и revisions

- `space_id` — stable lowercase slug; один GitLab repository = один Space. `document_id` — opaque UUID; `source_id` отделён от document ID; IDs не переиспользуются.
- Paths нормализуются в NFC, используют `/`, не абсолютны для document paths, не содержат `\`, `..`, control characters или ambiguity. Approval prefixes начинаются с `/` и не создают page-level read ACL. Duplicate rule IDs/normalized prefixes отклоняются; выбирается ровно одно longest-normalized-prefix правило на segment boundary. Lossless absolute↔relative policy mapping и root handling зафиксированы в [projection-mapping.md](projection-mapping.md).
- Git revisions — только полный lowercase SHA. T00 baseline использует SHA-1 (40 hex); schema допускает также 64 hex для versioned future compatibility, но это не разрешение на short/mixed-case SHA или неявную смену object format.
- `base_sha` — reviewed target HEAD; `proposal_sha` — exact source HEAD; `merge_commit_sha` — проверенный merge commit; `snapshot_sha` — exact main snapshot; `document_revision_sha` — commit версии конкретного документа. Blob/content/dependency hashes не заменяют commit revisions.
- Порядок revisions/generations определяется Git ancestry, не сортировкой SHA или event timestamps.

### 3.3. Idempotency и hashes

Для каждой mutation GO вычисляет и сохраняет:

```text
(actor_stable_id_or_verified_service_id,
 normalized_operationId_and_route_template,
 concrete_path_parameters,
 Idempotency-Key,
 payload_hash)
```

`payload_hash` — SHA-256 от UTF-8 JCS (RFC 8785) нормализованного request payload после schema validation, без secrets и без недоверенного actor. Body `idempotency_key`, если присутствует, обязан совпадать с header. До insert/side effect GO выполняет global key-registry lookup по key и сравнивает actor, normalized operation/route, concrete path и payload; composite DB row per actor/route сам по себе недостаточен. Повтор того же tuple возвращает durable result; другой actor/route/payload под тем же key — `IDEMPOTENCY_KEY_REUSED` и ноль writes. Для decision команды `Idempotency-Key == decision_id`. Для webhook/internal CI actor — verified service/event identity; provider-specific mapping UNKNOWN T00.

`DecisionRecord.record_sha256` — PROPOSED SHA-256 от JCS UTF-8 полного record **без поля `record_sha256`**. Полученный hash добавляется в JSON; note и protected annotated tag содержат один и тот же полный JSON. `note_id` создаётся GitLab вне canonical record и связывается через merge trailer/export metadata, поэтому самоссылочного hash цикла нет. Изменение record запрещено: создаётся новый UUID с `supersedes_decision_id`.

Hashes в export manifests вычисляются над явно указанными bytes либо JCS arrays/objects соответствующего manifest section. Raw Git object SHA и дополнительный SHA-256 exported object bytes не смешиваются. `body_sha256` относится к полному MR note body, `record_sha256` — к record без этого поля, а `canonical_json_sha256` — к полному canonical DecisionRecord JSON включая `record_sha256`; note и tag обязаны иметь одинаковый последний hash.

### 3.4. Cursor, truncation, errors

- Cursor — opaque bounded value, связанный с query/scope и полным per-Space набором snapshot/profile/policy bundle+revisions/group snapshot/revocation epoch плюс actor epoch. Он не является правом доступа и инвалидируется при revoke/stale snapshot.
- Каждая страница/read сообщает `limit` и `truncation {truncated, reason, next_cursor}`. Silent truncation запрещён. Multi-Space cursor chain сохраняет весь ordered per-Space набор либо завершается explicit stale error; одно-Space chain не меняет snapshot. `truncated=false ⇔ reason=none + next_cursor=null`, а truncated=true требует non-none reason и next cursor.
- Ошибки используют `code`, `message`, `request_id`, optional sanitized `details`, `retryable`. `NOT_FOUND` применяется по anti-enumeration policy. Timeout merge не означает `failed`; `RECOVERY_REQUIRED` требует Git-derived reconciliation и запрещает blind retry.

## 4. Связи ссылок

`openapi.yaml` ссылается на canonical schemas через relative `$ref`. `agent-tools.yaml` переиспользует request/response components OpenAPI, поэтому tool и human API не расходятся. `events.yaml` переиспользует `GitSha`, errors, evidence и attachment definitions. JSON Schemas переиспользуют evidence/attachment/stable ID definitions через relative JSON Pointers. Новые копии общих типов не создаются, если уже существует канонический `$defs` contract.

## 5. Semantic invariants и T01 vectors

- Cross-field equality, которые JSON Schema 2020-12 не выражает (path/body IDs, preflight SHA, hashes/linkage, longest-prefix, archive replacement, ranges), объявлены machine-readable через `x-contract-invariants` рядом со schema/operation.
- Они обязательны для server-side semantic validation до side effects, а не только documentation. `additionalProperties:false` не заменяет эти проверки.
- Полный synthetic positive/negative/concurrency/crash catalog находится в [t01-contract-tests.yaml](t01-contract-tests.yaml), включая correction-task exact-revision/actor/owner/CAS/idempotency/lifecycle/no-MR/backup negatives; canonical↔projection mappings — в [projection-mapping.md](projection-mapping.md). T00 DONE и G0 APPROVED; текущий статус vectors — DESIGN_NOT_EXECUTED до реального T01 execution.

## 6. Проверка и evidence

Пакет проверяется на:

1. JSON parse каждой `.schema.json`;
2. YAML parse `openapi.yaml`, `agent-tools.yaml`, `events.yaml`, `t01-contract-tests.yaml`;
3. разрешение всех local и cross-file `$ref`/JSON Pointers;
4. regex compile, unique operationIds, tool↔OpenAPI capability mapping и required mutation headers;
5. существование локальных Markdown links;
6. отсутствие secrets, реальных endpoints и утверждений об integration PASS;
7. выполнение [T01 vectors](t01-contract-tests.yaml) после выбора pinned toolchain, включая semantic/consumer assertions, а не только parse.

Эти проверки подтверждают только синтаксическую и ссылочную целостность артефактов. Они не заменяют T00, JSON Schema conformance suite, OpenAPI/tool contract tests, sandbox GitLab/IdP/CI проверки, hoster.ai real endpoint test или owner G0 approval.
