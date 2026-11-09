---
status: final
stepsCompleted:
  - requirements-extraction
  - epic-design
  - story-generation
  - final-validation
inputDocuments:
  - specs/corporate-kb/spec.md
  - specs/corporate-kb/architecture.md
  - specs/corporate-kb/architecture-spine.md
  - specs/corporate-kb/baseline.md
  - specs/corporate-kb/g0-review.md
  - specs/corporate-kb/planning-input.md
  - specs/corporate-kb/traceability.md
  - specs/corporate-kb/components/
  - specs/corporate-kb/adr/
  - specs/corporate-kb/contracts/
  - specs/corporate-kb/database.md
  - specs/corporate-kb/integration.md
  - specs/corporate-kb/operations.md
  - specs/corporate-kb/delivery-estimates.md
  - specs/corporate-kb/repository-provisioning.md
---

# corp_ai_db - Delivery Breakdown

## Overview

Этот документ содержит requirements inventory и approved epic/story breakdown для corp_ai_db. PRD отсутствует; функциональные и нефункциональные требования извлечены из утверждённого `spec.md` и architecture/design package. Отдельный UX contract отсутствует: UX requirements derived from spec/component docs. `content-standard.md` использован только как informational-контекст для DocOps, медиа и уведомлений, а не как источник новых нормативных требований.

Связи R/I/A/CF/AD/ADR/T/E описывают design coverage, а не выполненную реализацию. A01–A36 имеют статус DESIGN, CF-01–CF-30 — DESIGN_NOT_EXECUTED. T00 и G0 завершены/утверждены; deferred gates T04, T11, T13/T16 и production/legal проверки остаются обязательными.

## Requirements Inventory

### Functional Requirements

Связи приведены по `traceability.md`.

#### R01 — Единый интерфейс

Общий каталог, документ и агент в одном интерфейсе; автор и business approver работают без Git/CLI.

**Связи:** AD-2/13/15; ADR-04/07/08/09/16; A01,A20; T00,T02,T07,T08,T14,T18; E00,E02,E04,E07,E08.

#### R02 — Документная модель и WYSIWYG

Stable opaque UUID по `front-matter.schema.json`, дерево, ссылки по ID, versioned attachments и WYSIWYG. Строго один GitLab repository = один Space.

**Связи:** AD-1/4/13/15; ADR-08/09/10/16; A01,A21,A32; T00,T01,T02,T08,T10,T12,T13; E00,E01,E02,E04,E05,E06.

#### R03 — Canonical direct read

Чтение канонического документа целиком или по разделам с bounds, cursor и explicit truncation по exact revision SHA.

**Связи:** AD-1/13; ADR-03/04/08/09; A02,A21; T00,T02,T08,T09,T10,T14; E00,E02,E04,E05,E07.

#### R04 — Поиск только по опубликованному активному корпусу

Exact/semantic retrieval только по eligible activated published `main`; inactive preflight не обслуживает retrieval; scope проверяется до exposure содержимого.

**Связи:** AD-4/9; ADR-03/05/15/16; A03,A21,A35; T00,T01,T09,T10,T14,T19,T20*; E00,E01,E04,E05,E07 + deferred.

#### R05 — Единая identity и Space ACL

Shared stable identity и единая Space ACL для UI/API/tools/files/history/export/search. Business owners не получают GitLab users; business approval задаёт `approval-policy.yaml`, engineering ownership/review — CODEOWNERS.

**Связи:** AD-4/5/6/12/15; ADR-03/04/06/07/09/10/12/15/16; A04,A11,A18,A22,A24,A25,A26,A30,A31,A32,A33,A36; T00,T01,T02,T03,T05,T06,T07,T09,T10,T13,T14,T16,T18,T20*; E00–E08 + deferred.

#### R06 — Запрет публикации агентом и merge только через GO

Agent/connector/LLM не выполняют direct push, merge или auto-merge managed changes. После cutover все business/engineering/source-managed final applies выполняет только GO.

**Связи:** AD-1/2/3/5/6/7; ADR-04/08/11/12/13; A05,A17; T00,T05,T06,T09,T12,T15,T16; E00,E04,E06,E08.

#### R07 — MR и immutable ProposalRecord

Proposal = MR с exact `base_sha`/`proposal_sha`, точным diff и append-only ProposalRecord: `author_stable_id`, `version_author_stable_id`, `requester_stable_id`, `actor_type`, optional `run_id`, `rationale`, `evidence[]`, idempotency metadata.

**Связи:** AD-1/6/13; ADR-04/08/09/11/12/14/15; A05,A22; T00,T03,T05,T06,T07,T09,T10,T12,T15,T16,T18; E00,E02,E04,E05,E06,E08.

#### R08 — Canonical DecisionRecord и независимое согласование

Accept/reject/cancel требуют canonical DecisionRecord по schema в structured MR note и protected annotated tag `kb-decisions/<uuid>` на `proposal_sha`. Approval привязан к exact version и запрещает self-approval author/version-author/requester.

**Связи:** AD-1/6/7/13; ADR-04/08/09/12/13/14; A06,A07,A27,A30,A34,A36; T00,T03,T05,T06,T07,T13; E00,E02,E04,E06.

#### R09 — Git revisions и доказуемая публикация

Durable revisions = Git history. Accepted publication — реальный merge commit без squash/rebase/fast-forward, first parent = `base_sha`, second parent = `proposal_sha`, с Decision trailers. Restore — revert-MR/new commit.

**Связи:** AD-1/3/7/13; ADR-08/09/11/13/14; A08,A10,A27,A28,A34; T00,T04,T05,T07,T13,T18; E00,E03,E04,E06,E08.

#### R10 — Сериализация, idempotency и recovery

Нет silent overwrite: merges сериализуются GO per repository/target; `target HEAD == base_sha` перепроверяется непосредственно перед merge. Retry идемпотентен по `decision_id` и `(repository_id,target_branch,proposal_sha)`; recovery обязан быть conclusive.

**Связи:** AD-6/7; ADR-04/08/09/12/13/14; A06,A07,A08,A09,A28,A29,A34,A36; T00,T03,T04,T05,T06,T07,T13,T18; E00,E02,E03,E04,E06,E08.

#### R11 — Пересобираемый versioned index

Индекс производный, асинхронный, ACL/SHA/ancestry/profile-aware; full/incremental equivalence по dependency closure, single-writer active pointer и rebuild без потери канона.

**Связи:** AD-1/4/9/15; ADR-03/05/06/10/11/15/16; A02,A03,A11,A12,A22,A25,A31,A32,A33,A35; T00,T01,T03,T09,T10,T12,T13,T14,T18,T19,T20*; E00,E01,E02,E04,E05,E06,E07,E08 + deferred.

#### R12 — Безопасный import и controlled cutover

Import dry-run возвращает path→ID/provenance/links/attachments/errors без canonical writes. Controlled bulk допустим только до cutover в unpublished `main`; после cutover все changes — GO/MR/human decision/GO merge.

**Связи:** AD-1/3/10/15; ADR-04/05/06/08/11/16; A13,A23,A31,A35; T00,T01,T10,T12,T15,T16,T17; E00,E01,E05,E06,E08.

#### R13 — Сохранение curated-правок и source contracts

Повторный импорт не затирает curated-правку; `source_managed` не имеет auto-merge; удаления явные; `live_operational` остаётся typed read-only и автоматически не становится wiki.

**Связи:** AD-9/10/13/15; ADR-03/05/06/08/09/11/16; A14; T00,T12,T15,T16; E00,E06,E08.

#### R14 — Полная переносимость и restore

Переносимость = clone + decisions/assets manifests с exact refs, DecisionRecords/MR metadata, immutable external objects/hashes и policy closure. Требуется проверяемый mirror/metadata backup restore.

**Связи:** AD-1/7/11/15; ADR-06/08/14/15/16; A15,A27,A32,A36; T00,T03,T05,T13,T18; E00,E02,E04,E06,E08.

#### R15 — Санкционированный inference

Все AI-вызовы используют согласованные providers, data profiles, проверенные egress и secrets handling; unplanned fallback запрещён.

**Связи:** AD-4/5/11/14; ADR-03/04/06/07/10; A16; T00,T03,T11,T14,T17,T18,T20*; E00,E02,E04,E07,E08 + deferred.

#### R16 — Ограниченный execution capability

Только read/search/propose agent tools. Недоверенные документы не дают полномочий; merge/grants/arbitrary Git/shell/SQL недоступны на любом канале.

**Связи:** AD-4/5/12; ADR-03/04/07/09/10/11/12/13/16; A04,A17,A18,A23,A24,A29; T00,T03,T06,T07,T12,T14,T16; E00,E02,E04,E06,E07,E08.

#### R17 — Повторяемый dedicated deployment

Повторяемый deployment на клиента: repositories=Spaces + config + isolated PostgreSQL/index/objects/secrets/backups, single-writer schemas, без клиентских веток кода; upstream upgrade policy обязателен.

**Связи:** AD-2/4/8/11; ADR-06/07/08/10/15/16; A19,A20,A33; T00,T01,T03,T14,T18,T20*; E00,E01,E02,E07,E08 + deferred.

#### R18 — Regression, evaluation и эксплуатационные доказательства

Regression/evaluation включает deterministic merge/recovery/ACL/schema/export/cutover tests и эксплуатационные метрики, а не только UI smoke или LLM judge.

**Связи:** AD-16 и все AD через evidence; ADR-03–ADR-16 по scope; A28,A33 плюс regression coverage всего acceptance suite; T00,T01,T05,T06,T11,T14,T17,T18,T19,T20*; E00,E01,E04,E07,E08 + deferred.

\* Связи T20 с R04,R05,R11,R15,R17,R18 являются только design-derived. В `spec.md` для T20 нет явной строки Requirements; T19/T20 не входят в E00–E08.

### NonFunctional Requirements

#### I01 — Публикация только через controlled cutover и GO merge

До cutover controlled engineering bulk push допустим только в unpublished `main` при закрытом пользовательском доступе и отсутствии published index. После активации документ изменяется только реальным merge commit в protected `main`, созданным GO по canonical accepted DecisionRecord.

**Связи:** AD-1/3; ADR-08/11/13; A05,A13,A31,A34; T00,T05,T06,T12,T13; E00,E04,E06.

#### I02 — Отсутствие обходных write/merge paths

После cutover все managed builtin/tool/API/import/restore/engineering/source-managed paths идут через GO и MR; direct push и direct human/service merge закрыты для всех non-privileged managed identities. Routine/self-service admin break-glass отсутствует. Привилегированный GitLab Owner bypass — out-of-band integrity incident, обнаруживаемый reconciliation и помещаемый в affected-target quarantine, а не approved managed path или абсолютное физическое merge-only-GO для admins. Cutover: write freeze → `HEAD == cutover_sha` → protected tag/MR-only rules → inactive preflight → activation; auto-merge отсутствует.

**Связи:** AD-2/3/5; ADR-04/07/08/11/16; A04,A05,A13,A17,A31; T00,T03,T05,T06,T12,T15,T16; E00,E02,E04,E06,E08.

#### I03 — Trusted principals

Author/version-author/requester берутся из trusted execution context и stable external identity. LLM не задаёт `actor_id`, grants, tenant, run или policy; GitLab bot/service identity не заменяет principals ProposalRecord.

**Связи:** AD-5/6/12; ADR-03/04/09/10/12; A05,A18,A24,A26,A30; T00,T03,T05,T06,T07,T09,T14; E00,E02,E04,E07.

#### I04 — Физическая граница merge credentials

Agent создаёт только разрешённые ветки и MR, но не accept/reject/cancel/merge/grants даже для author/admin chat user. После cutover GO merge service identity — единственная managed identity с merge permission; bot/connector/CI tokens merge не имеют. Привилегированный GitLab Owner может технически обойти rules вне GO; такой bypass квалифицируется как incident с reconciliation/quarantine, а не как managed permission.

**Связи:** AD-2/5/6; ADR-04/07/11/12/13; A04,A17,A18,A34; T00,T03,T05,T06,T09,T12,T16; E00,E02,E04,E06,E08.

#### I05 — Exact-SHA apply без трансформации

Merge применяет exact `base_sha` и `proposal_sha` без повторной LLM-генерации, automatic conflict merge, squash, rebase или fast-forward. Новый commit/rebase создаёт ProposalVersion и инвалидирует approval. Проверяются parents и Decision trailers.

**Связи:** AD-1/6/7/13; ADR-04/08/09/12/13/14; A06,A08,A27,A34; T00,T04,T05,T07; E00,E03,E04.

#### I06 — Отказ без записи при stale/revoked/mismatch состоянии

Stale base/proposal SHA, target race, policy bundle/revision mismatch, self-approval, потеря group/path role или revocation до merge/export, `HEAD != cutover_sha` приводят к отказу и нулю новых writes в `main` для отклонённой операции.

**Связи:** AD-3/6/7/12; ADR-04/09/10/11/12/13; A06,A08,A29,A30,A31,A34,A36; T00,T03,T05,T06,T07,T12,T13; E00,E02,E03,E04,E06.

#### I07 — Decision integrity и durable recovery barrier

Accept/reject/cancel DecisionRecord — один JSON с `record_sha256` в MR note и protected annotated tag на `proposal_sha`; mismatch note/tag/trailer/parent делает decision invalid. Перед external merge GO атомарно фиксирует `merge_attempted` и durable per-target `recovery_required`. Timeout не означает merged или failed. Только Git-derived conclusive reconciliation снимает barrier; недоказуемый outcome остаётся quarantined. Распределённая ACID между GitLab и PostgreSQL не требуется и не имитируется.

**Связи:** AD-1/7/8; ADR-12/13/14/15; A07,A27,A28,A34; T00,T05,T06,T07,T13,T18; E00,E04,E06,E08.

#### I08 — Pending/rejected/preflight не попадают в search

Pending/rejected proposals и ветки исключены из published search corpus. Activated index строится только из eligible published `main`; cutover preflight остаётся inactive и `serving_allowed=false`.

**Связи:** AD-3/9; ADR-03/05/08/11/16; A03,A22,A31,A35; T00,T10,T12,T14; E00,E05,E06,E07.

#### I09 — Единый ACL/history/export perimeter

Один repository = один Space = один ACL/history/export perimeter; `access` во front matter не создаёт ACL. Tree/titles/snippets/chunks/files/history/export/tools авторизуются по versioned policy до payload и до отправки LLM; разные ACL требуют разных repositories.

**Связи:** AD-4/11/12/15; ADR-03/04/06/07/09/10/16; A04,A11,A22,A25,A32,A36; T00,T01,T02,T03,T07,T09,T10,T12,T13,T14,T16,T18; E00–E08.

#### I10 — Пересобираемые projections и single writers

`kb_index` пересобирается из Git + immutable assets, Git-derived `kb_ops` state — из MR/notes/tags/merge commits, `kb_authz` — из Git policy + IdP. GO-owned correction tasks — отдельные operational records с append-only events, restricted evidence и idempotency registry: они не Git-derived и восстанавливаются из durable `kb_ops` backup с последующей MR reconciliation, а не фабрикуются из Git. Только owning components пишут соответствующие schemas; indexed copy не редактируется как вторая истина; unknown recovery не очищается rebuild.

**Связи:** AD-1/7/8/9/11; ADR-05/06/08/13/14/15; A12,A15,A28,A33; T00,T01,T05,T10,T13,T18; E00,E01,E04,E05,E06,E08.

#### I11 — Monotonic index publication

Late job старой ancestry generation или index profile не возвращает старый snapshot в active search; SHA lexicographic ordering запрещено. Только CI/index writer продвигает pointer после полного validated run; incremental эквивалентен full по dependency closure; HEAD/index reconciliation регулярен.

**Связи:** AD-7/8/9/16; ADR-03/05/06/13/15; A02,A03,A12,A35; T00,T01,T10,T12,T13,T14,T19; E00,E01,E05,E06,E07 + deferred.

#### I12 — Одинаковые правила на всех каналах

Access policy и execution capabilities не зависят от регистрации/канала инструмента: direct/deferred/note chat/automation/channel/OpenAPI/call_tool. Для sensitive operations обязателен один `policy_bundle_id` и согласованные full access/approval policy revision SHA.

**Связи:** AD-4/5/6/12; ADR-03/04/10/12; A04,A17,A18,A36; T00,T03,T05,T06,T09,T13,T14; E00,E02,E04,E06,E07.

#### I13 — Versioned attachments с тем же периметром безопасности

Attachment revisions имеют тот же Space ACL, immutable object/version/hash и входят в assets manifest/export/backup. Их удаление учитывает Git history, mirrors, object versions и retention. Cross-Space history/export isolation обязателен.

**Связи:** AD-9/11/15; ADR-03/05/06/08/16; A15,A22,A32; T00,T10,T12,T13,T15,T16,T17,T18; E00,E05,E06,E08.

#### I14 — Явные пользовательские состояния

UI различает `draft / in_review / published / indexed / archived / conflicted`; `recovery_required`, quarantine и inactive preflight не маскируются под published/indexed.

**Связи:** AD-3/9/13; ADR-05/08/09/11; A07,A28,A31,A35; T00,T04,T05,T07,T08,T10,T12,T18; E00,E03,E04,E05,E06,E08.

#### Дополнительные security/privacy constraints

1. **Zero unauthorized disclosures** в согласованном adversarial suite для tree/search/chunks/files/history/export/tools; deterministic negative tests обязательны независимо от LLM judge — A04,A11,A22,A32, AD-16.
2. **Default private**; серверная авторизация выполняется до browser/model payload, а SQL/index filter сам по себе не заменяет финальную авторизацию — AD-4, I09.
3. **Anti-enumeration:** `NOT_FOUND` применяется там, где denial раскрыл бы существование protected object; ошибки не содержат private content — integration §4.3.
4. **Revocation:** group refresh ≤15 минут, revocation SLO ≤30 минут; merge/export/private page — при ближайшем sensitive recheck; live subscriptions закрываются — ADR-10, A25.
5. **Fail closed:** provider/IdP outage не продлевает cached allow бессрочно; stale group/policy snapshots запрещают sensitive operations.
6. **Browser security:** authenticated upstream session и CSRF/Origin controls обязательны для human decision path. Stock cookie/approval behavior не считается достаточным — ADR-12, G0-D4/D5.
7. **Prompt injection:** документы, rationale, evidence и tool results — недоверенные данные; они не изменяют actor, groups, tenant, scope, tools, provider, pointer или merge credentials — A18.
8. **Secrets:** только deployment secret mechanism; не допускаются в Git, product tables, logs, traces, manifests, model payloads или обычном export.
9. **Data profiles:** `strict` по умолчанию; каждый PII hit получает human disposition. `pii_permitted` требует legal basis и собственный согласованный hoster.ai/client inference без внешнего PII egress — AD-14.
10. **Intake security:** traversal, absolute/ambiguous paths, symlinks, executable HTML/MDX, secrets, oversized/decompression-bomb inputs и invalid UTF-8 отклоняются до corpus/preview — A23.
11. **Admin boundary:** GitLab instance/project Owners могут обойти GO. G0-D3 требует restricted privileged accounts, audit, out-of-band reconciliation и explicit break-glass runbook; абсолютный merge-only-GO для admins не заявляется.
12. **Telemetry privacy:** raw documents/chunks/queries/rationale/evidence/provider payloads, tokens, passwords, signed URLs и PII snippets запрещены в обычных logs/metrics/traces.

#### Дополнительные reliability/quality constraints

1. Merge не ждёт indexing; CI failure не откатывает canonical merge — R09/R11, AD-5.
2. `failed` допустим только после `request_state=completed + no_merge_proven=true + reconciliation evidence`; timeout остаётся unknown/quarantined.
3. Guarded retry возможен только из conclusive `failed`: новый `attempt_id`, тот же `decision_id`, exact base/proposal и fresh preconditions. `conflicted` и `invalid` terminal/non-retryable.
4. Полная потеря `kb_ops` начинается с external global bootstrap merge freeze; отсутствие DB row не доказывает отсутствие external merge call.
5. Barrier снимается только после target-wide reconciliation **всех** unresolved accepts; terminal label или supersedes сам по себе barrier не очищает.
6. Events обрабатываются at-least-once с dedupe, bounded retry, dead-letter и periodic HEAD/source reconciliation; webhook payload не является proof active revision.
7. Source cursors `seen/proposed/merged` продвигаются только после durable observation, durable MR+ProposalRecord и verified Git merge соответственно; extraction/LLM/indexing failure не даёт false merged.
8. Profile changes используют shadow build и controlled pointer switch; destructive live rebuild запрещён.
9. Restore проверяется на clean isolated instance с refs/decisions/assets/policies/grants closure и negative controls; наличие dump/files не является PASS.
10. Retrieval quality оценивается отдельно по exact/semantic recall, factual support, citation correctness и abstention на expert golden set; deterministic safety не смешивается с LLM score — AD-16, A14/A16 по scope evaluation.
11. Mocked GitLab/IdP/DB/hoster.ai не засчитывается как integration PASS; отсутствующая обязательная проверка остаётся BLOCKED.

#### Performance, capacity, freshness и cost constraints

1. Уже зафиксированы только **group refresh ≤15 минут** и **revocation ≤30 минут**. Другие SLA не выдумываются.
2. До release владелец задаёт corpus/profile/concurrency, p95/p99, merge→index freshness, queue lag, quality thresholds, RPO/RTO, retention и budgets.
3. TTFT и full response измеряются отдельно; также Git read/merge latency и CI lag — cold/warm, с corpus SHA, config и concurrency.
4. Online app и CI workers имеют отдельные concurrency/resource budgets; требуются backpressure и bounded queues.
5. ANN/HNSW/IVFFlat оцениваются по recall **после ACL filters**; нельзя компенсировать плохой recall отправкой дополнительных закрытых candidates модели.
6. OpenSearch добавляется только после измеренной необходимости и отдельного ADR; broker также не обязателен без измеренной потребности.
7. Cost включает inference, embeddings, extraction, OCR/reranking, storage, review, GitLab и operations, а не только token price.
8. Cache/fast path, если появится, должен быть keyed по client/tenant + ACL + SHA + policy; cross-client cache запрещён. T20 не получает нормативных R-назначений автоматически.

#### Operations/evidence constraints

1. Release candidate фиксирует corpus SHA, code/config/model/tool-schema versions, dataset и sanitized results.
2. Обязательны runbooks для startup, cutover, merge recovery/quarantine, source sync, export, backup, restore, upgrade и rollback; текущий `operations.md` — `design_not_executed`.
3. RPO/RTO, retention, idempotency replay retention, backup cadence, maintenance windows и alert thresholds — owner decisions.
4. Active recovery barriers, unresolved quarantine, active retry/DLQ и incomplete restore/export closure нельзя удалять по generic TTL.
5. Upgrade требует seam registry, rollback, SBOM/license review, branding/notices preservation и regression evidence.
6. Production migration, destructive cleanup, deploy/push, paid external calls и enabling egress требуют отдельной owner authorization.

### Additional Requirements

Ниже — дополнительные обязательные design constraints и baseline decisions. Новые нормативные ID не вводятся.

#### Infrastructure и deployment

1. **Pinned baseline:** Open WebUI `v0.13.0` / `c38885a1a737da4968f157092f304f3b5481d0bf`; GitLab CE `19.5.3-ce.0`; PostgreSQL `18.6` + pgvector `0.8.7`; GitLab Runner `19.5.3`; Python `3.12.13`; Node `22.23.4`; Git object format SHA-1 — G0-D1/D2, baseline §1.
2. **Одна reusable code line:** клиент получает config/adapters, не client code branch. Managed KB включается feature flag; personal Notes и ordinary chats не мигрируются и не меняются — AD-2/11, A19/A20.
3. **GO — отдельный модульный монолит** с ports-and-adapters и единственным canonical write/merge coordination. Разделение сервисов дальше — только по измеренным bottlenecks.
4. **Изолированный client perimeter:** repositories, PostgreSQL/index, object storage, secrets, backups, config и egress независимы; shared canonical store/credentials/cache между клиентами запрещены.
5. **Environments:** local/unit, T00 sandbox, integration/fault sandbox, corpus preflight/cutover staging, restore/upgrade rehearsal, dedicated client и second client имеют разные разрешения и изоляцию.
6. **GitLab CE profile:** `push_access_level=0`, `merge_access_level=40`, только GO Maintainer, unprotect Administrator-level, protected `kb-decisions/*`; per-user protected branch grants CE не используются.
7. **Credential separation:** proposal/read и merge identities GO разделены; agent/connector/CI/index/retrieval получают независимые least-privilege credentials. Merge credential недоступен UI/browser/agent/connector/CI.
8. **Repository provisioning:** namespace `kb-<client>/kb-space-<space_slug>` — утверждённый design G0-D13; stable binding по `repository id + space_id`, не по mutable path. Фактические namespaces/corpus mapping/schedule остаются owner inputs.
9. **Per-Space registry:** `space_id`, `gitlab_project_id`, repository path, state, policy bundle, GO identity, index profile, cutover SHA и audit metadata; registry не заменяет Git canonical history.
10. **Cold offline startup:** container/package/model/OCR/extraction/reranker assets готовятся заранее с SBOM/hashes; любой unapproved download/update/fallback блокирует readiness.
11. **Branding/license:** Open WebUI branding/notices сохраняются; white-label/commercial distribution только после owner/legal clearance — G0-D10.
12. **Frontend baseline debt:** Vitest и direct 6 GiB Vite build приняты для T01, но svelte-check, ESLint и upstream build-script failures отслеживаются явно и не считаются healthy baseline — G0-D9.

#### Integrations и внешние capabilities

1. Переиспользуются upstream Open WebUI auth/users/chat/model connections/grants/native tools/retrieval; auth/chat/RAG не переписываются, собственный Git hosting не строится.
2. **Identity/AuthZ adapter обязателен:** stock LDAP/OIDC JIT недостаточен из-за email/provider-alias linking, отсутствия полной nested closure и stale empty groups. Требуются stable `(issuer,sub)` или `(directory,objectGUID/entryUUID)`, duplicate/ambiguous rejection, empty-group revocation, epoch-matched snapshots и fail-closed AuthzContext — G0-D4.
3. **LDAP обязателен в MVP:** G0-D14; OpenLDAP/LDAPS/StartTLS synthetic runtime checks 8/8 отмечены завершёнными. Production AD, live subscription closure и измеренный revocation SLO остаются follow-up.
4. **Deny-by-default execution adapter обязателен** для native и legacy paths, deferred `call_tool`, browser/direct tools, OpenAPI, MCP, automations, channels и subagents; exposure filtering в `get_tools` недостаточен — G0-D5, ADR-04.
5. **hoster.ai:** используется managed OpenAI-compatible/Open WebUI connection. Реальные endpoints/model IDs/credentials/egress и production quality thresholds не предоставлены; T11 BLOCKED до их появления, mock не PASS — G0-D11.
6. **Retrieval:** pgvector+FTS — validated candidate после 22/22 synthetic gates, не final production selection. Production embedding model/dimensions/chunking/reranker/quality/latency остаются owner/config decisions.
7. Native upstream hybrid при metadata filters имеет generic full-collection BM25 fallback; managed `kb_index` обязан использовать Git revision/snapshot/profile/dependency metadata, а не mutable Knowledge/Notes projections.
8. **Events:** GitLab webhooks + GO + CI достаточны как design; отдельный broker не обязателен. Production webhooks требуют reachable allowlisted endpoints и secret validation; local-URL relaxation только sandbox.
9. **Первый connector:** SharePoint/Bitrix24/Kayako выбирается владельцем позже вместе с exact objects/auth/edition/API/rate limits; остальные connectors не считаются готовыми.
10. **Object storage:** immutable/versioned objects обязательны, но LocalStack cross-bucket ACL failed, production engine untested; повторная проверка T13/T16, без ACL/export/restore PASS — G0-D16.
11. Docling сначала проверяется как существующая upstream integration; второй extraction pipeline добавляется только при документированной необходимости.

#### Data, canonical model и projections

1. **Канон:** Markdown + closed front matter в GitLab; full commit SHA = revision; MR/ProposalRecord, DecisionRecord note+tag, CutoverRecord и versioned policies находятся в Git/GitLab.
2. **Front-matter-v2:** stable opaque UUID, title/parent, ownership mode, required origin где применимо, stable-ID `links[]`, `valid_until`, archive pairing и immutable attachments. `access`, arbitrary status/owner/commit-time и `live_operational` как canonical document mode запрещены.
3. `migrated` и `source_managed` требуют `origin`; `origin.ownership_mode == ownership_mode`. Source IDs вида `DOC-0001` не подвергаются silent lowercase normalization.
4. **Stable links:** body links и front matter links образуют один stable-ID graph; resolved projection обязан сохранять тот же target UUID в same Space/snapshot.
5. **Archive invariant:** `archived=true` iff присутствует `archive`; restore — reviewed revision без archive. Replacement — другой active document в same Space; descendants обрабатываются явно, без неявного cascade.
6. **Structure validation:** duplicate IDs, cycles, orphans, invalid paths и ambiguous links обрабатываются как validation errors; rename/move сохраняет UUID и deep links.
7. **Paths:** repository-relative NFC для documents; policy absolute↔relative mapping lossless: `/` ↔ empty prefix, `/pricing` ↔ `pricing`; `..`, ambiguity и неправильные separators запрещены.
8. **Ownership modes:**
   - `migrated` — старый источник больше не writer;
   - `source_managed` — local edits запрещены GO, updates только MR+human decision+GO merge;
   - `curated` — three-way previous imported base/current curated/incoming без overwrite;
   - `live_operational` — typed bounded read-only со `snapshot_time`, без document/MR/index/cursor effects.
9. **Source deletion:** tombstone/obsolete review, а не silent delete; один source object имеет не более одного outstanding proposal.
10. **Attachment revisions:** `{object_id,version,sha256,size,media_type,source_ref}`, immutable/versioned; mutable current URL без hash запрещён.
11. **Media classes:** decorative исключаются; illustrative сохраняются как asset+caption; substantive получают явно помеченное auto description со ссылкой на original; critical/handwritten индексируются только после требуемой human transcription/verification.
12. **Index snapshot:** различаются `snapshot_sha`, `document_revision_sha`, blob/content hash, dependency hash, Git ancestry `main_generation` и независимый `index_profile_version`.
13. **Eligibility:** исключаются pending/rejected branches, `inbox`, templates, service files, archived/deleted и unverified critical media.
14. **Incremental publication:** требуется independent full-run equivalence на том же SHA, complete closure, `missing_inputs=[]`, ready exact+semantic hashes и совпадающие perimeter/generation/profile/policy.
15. **DB ownership:** upstream → Open WebUI; managed grants/`kb_authz` → Identity/AuthZ; `kb_ops` → GO; `kb_index`/pointer → CI/index workers; retrieval read-only. Cross-schema writes и cross-schema FK запрещены; связи только logical IDs через versioned contracts.
16. **Transactions:** ограничены одной owning schema; external GitLab/IdP/CI/provider calls выполняются вне DB transaction; distributed ACID не имитируется.
17. **Rebuild:** `kb_authz` из Git policy+IdP, Git-derived `kb_ops` из MR/notes/tags/history/source registry, `kb_index` из Git+immutable assets+approved config. Correction tasks/events/evidence/idempotency records — non-Git-derived GO-owned operational state: обязательны durable `kb_ops` backup/restore и последующая linked-MR reconciliation; Git-only rebuild не воссоздаёт и не удаляет их. Active AuthzContext и active pointer не восстанавливаются как действующая истина из непроверенного backup.
18. **Export:** единый `git_clone_with_manifests` содержит explicit refs, documents/decisions/assets/policies/closure. Accepted до merge не получает fabricated merge proof; rejected/cancelled имеют verified MR closure; missing/rejected assets делают package incomplete.
19. **Backup:** Git mirror all refs + GitLab MR/note/audit metadata + objects + config + отдельная secrets policy. Correction-task current projections, append-only events, restricted evidence и idempotency records имеют отдельный durable non-Git-derived `kb_ops` backup/restore с hashes/event-sequence checks и linked-MR reconciliation; Git-only rebuild их не воссоздаёт, а restore/API не создаёт второй canonical write path. Full Space export не является полным platform backup: private chats, users/sessions/models и secrets требуют отдельных procedures.

#### Import, migrations, cutover и upgrades

1. **Dry-run:** deterministic path→ID, provenance, tree/links/anchors, attachments, original/extracted hashes, losses/errors/security/PII/media gates и `canonical_writes=false`; не создаются branch/MR/main commit/active index/merged cursor.
2. **Controlled pre-cutover bulk:** только unpublished `main`, user access закрыт, published index отсутствует, source owner/data barrier завершены; отдельное migration/import authorization обязательно.
3. **Validation:** expert sign-off и CutoverRecord связывают Space/repository, exact `cutover_sha/main_sha`, evidence, sign-off stable ID и UTC timestamp. Operations design дополнительно предусматривает двух независимых human reviewers import report/representative diff.
4. **Cutover sequence:** freeze first → exact HEAD → drift stop → protected validation/cutover tag и merge-only-GO rules → negative direct-push/settle proof → separate inactive full preflight request/run/snapshot → validation.
5. **Published pair:** после successful preflight создаются отдельные published request/run/snapshot с новыми IDs, но тем же SHA, dependency closure, policy triple и exact/semantic hashes; полная validation повторяется.
6. **Activation:** единственный writer per `(space_id,profile_id)` across all generations выполняет fence/current-pointer/latest-ancestry/run CAS; active pointer наблюдается до Space/user activation. Обратный порядок запрещён.
7. **HEAD drift:** требует новый CutoverRecord/sign-off/preflight. Replay возможен только для same Space+SHA при сохранённом freeze и неизменном HEAD.
8. **После protection/activation:** исправления только reviewed/revert MR; history rewrite и возврат к bulk bypass запрещены.
9. **External migrator:** runtime workers с `ENABLE_DB_MIGRATIONS=False` и non-DDL roles; один authorized migrator выполняет upgrade и проверяет expected Alembic head `e42c8f710a36` до traffic — G0-D6.
10. Migration требует pre/post data-copy checks, duplicate identity checks, legacy ACL→access_grant diff, lock/duration record, sanitized errors и rollback assessment. Production migrations по static audit не разрешаются.
11. **Owner migrations:** upstream, `kb_authz`, `kb_ops`, `kb_index` выполняются независимо своими owning components; upstream migrations не копируются в продуктовые schemas.
12. **Rollback:** application code/config — pinned compatible artifact под freeze; content — новый revert-MR; DB — только owning component по проверенной backward/forward procedure; index/model — validated compatible snapshot или новый full build.
13. **Upgrade:** отдельная isolated rehearsal с owner migrations, cold offline startup, contracts, startup reconciliation, no-bypass/ACL/recovery/export checks, seam/SBOM/license diff.

#### Monitoring, alerting и observability

1. **Сквозная корреляция:** `request_id → run_id? → proposal_id/proposal_sha → decision_id → merge_commit_sha → index run/snapshot_sha`; дополнительно actor stable ID, policy revisions, generation/profile, source versions и export ID.
2. **Merge correctness:** result codes, merge count per decision/proposal/target, parent/trailer/note/tag mismatch, Git read/merge latency. Duplicate conclusive merge или mismatch — immediate integrity alert.
3. **Recovery:** lock wait, owner/fencing changes, stale-owner denials, `recovery_required` count/age, quarantine. Наличие `recovery_required` — immediate operational alert; auto-clear запрещён.
4. **Decision integrity:** note/tag failures, hash/target/linkage errors, invalid/supersedes counts. `DECISION_INVALID` блокирует affected target.
5. **Identity/revocation:** group snapshot age, stale/denied contexts, grant drift, sensitive recheck failures, time to deny/subscription close. >15 минут refresh и >30 минут revocation — requirement alerts.
6. **Index/retrieval:** HEAD lag, queue/run state, exact+semantic readiness, active snapshot age, stale candidates, closure mismatches, late jobs, pointer conflicts. No active pointer для activated Space — readiness alert.
7. **Events/CI:** authenticity/replay rejects, dedupe, retry/DLQ, CI outage, job duration, missed HEAD reconciliation.
8. **Source sync:** seen/proposed/merged lag, outstanding count/age, conflicts/tombstones, duplicate attempts. Более одного outstanding или auto-merge attempt — immediate correctness alert.
9. **Export/backup:** per-batch authorization failures, closure/missing count, mirror freshness, hash failures, backup age, restore drill. Missing closure/hash/unauthorized batch запрещает complete claim.
10. **Inference:** TTFT/full response, retry/cancel/malformed args, route inventory, fallback attempts, cold/warm cost. Unapproved route/fallback/secret/PII egress — immediate security alert.
11. **Browser/UX:** canonical read failure/latency, tree/search/read/proposal errors, preview reliability, truncation/retry rates. Unreliable preview merge attempt — merge blocker.
12. **DB/schema:** denied cross-writes, non-owner migrations, role drift, read-only violations. Успешная non-owner/cross-schema write — security/integrity incident.
13. **Offline/supply chain/telemetry:** missing assets, SBOM mismatch, cold-start downloads, branding/seam drift и redaction canaries; confirmed secret/private disclosure — immediate security incident.

#### API compatibility и versioned contracts

1. Собственный логический prefix — `/api/kb/v1`; это не утверждённые upstream routes. OpenAPI/tool/event/schema contracts остаются PROPOSED/DESIGN до реализации и T01 tests.
2. Closed canonical/API objects используют `additionalProperties:false`. Новое поле closed canonical record требует нового `schema_version` и migration/compatibility decision; нельзя молча менять ProposalRecord/DecisionRecord hash semantics.
3. Версионированные контракты включают `document-front-matter-v2`, `authz-context-v2`, `agent-tools-v2`, `export-manifest-v2`, `index-snapshot-v1`, `docops-review-metadata-v1`, `docops-correction-task-v1` и canonical↔projection mapping. Correction task — GO-owned `kb_ops` operational record, не canonical content/ProposalRecord/DecisionRecord; lifecycle/backup/rebuild semantics определены только [новым contract](../../specs/corporate-kb/contracts/docops-correction-api.md).
4. `x-contract-invariants` обязателен для path/body equality, preflight SHA, hashes/linkage, longest-prefix, archive replacement и ranges; JSON Schema alone недостаточна.
5. **IDs/revisions:** stable lowercase `space_id`, opaque UUID `document_id`, UUID `decision_id`, отдельный `source_id`; IDs не переиспользуются. Revisions — полный lowercase SHA; ancestry, не lexicographic order.
6. **Время/текст:** UTC RFC 3339, UTF-8, enum values lower_snake_case, UI labels на русском; Git trailers сохраняют заданный регистр.
7. **Idempotency:** каждая mutation требует `Idempotency-Key`; global key registry связывает verified actor/service + normalized operation/route + concrete path + payload hash. Другой actor/route/path/payload под тем же key → `IDEMPOTENCY_KEY_REUSED`, ноль writes.
8. Decision требует `Idempotency-Key == decision_id == body key == header`; повторяющиеся path/body IDs обязаны совпадать до side effect.
9. **Errors:** `{code,message,request_id,details?,retryable}`; details sanitized. Поддерживаются STALE_BASE, PROPOSAL_VERSION_MISMATCH, PATCH_AMBIGUOUS, POLICY_REVISION_MISMATCH, APPROVER_CONFLICT, DECISION_INVALID, RECOVERY_REQUIRED, AUTHZ/GROUP stale, INDEX_NOT_READY, STALE_INDEX_CANDIDATE, DEPENDENCY_CLOSURE_MISMATCH, SECURITY_REJECTED/PII_REVIEW_REQUIRED, LIMIT_EXCEEDED и др.
10. **Cursor/truncation:** cursor связан с query/scope и полным ordered per-Space snapshot/profile/policy/group/revocation/actor-epoch набором. `truncated=false ⇔ reason=none + next_cursor=null`; true требует non-none reason и next cursor. Silent truncation запрещено.
11. **AuthzContext-v2:** каждый Space сам содержит repository/bundle/access+approval revisions/group snapshot/revocation epoch; top-level shared policy/groups для нескольких Spaces запрещены. Borrowed binding или потерянный cursor descriptor → explicit stale error.
12. **Agent-tools-v2:** curated single-page body create и `AgentAnchoredPatchChange` с required body section. Agent не получает whole-document/front-matter replacement, `editProposalVersion`, attachments/archive/origin/access или privileged operations; GO независимо отклоняет forbidden diff.
13. Human whole-document replacement/edit/review/apply — отдельные browser+CSRF operations; human apply не экспортируется как LLM tool.
14. Schema numeric limits — PROPOSED exchange bounds, не production SLA/capacity; unlimited mode запрещён.
15. CF-01–CF-30 и projection mappings подготовлены, но не выполнены; syntax/YAML/JSON checks не заменяют semantic, consumer, sandbox и real integration tests.

#### Non-goals, DEFERRED и stop conditions

**Не входят в MVP без новых требований/ADR:**

- общая multi-tenant БД;
- arbitrary page-level ACL внутри repository;
- realtime collaborative editing/CRDT;
- agent/connector/LLM auto-merge;
- multiple approvers/quorum;
- arbitrary shell/Python/SQL/filesystem/Git;
- agent bulk/subtree/attachment operations и сложная переработка таблиц;
- GraphRAG/people graph;
- новый inference gateway;
- universal two-way sync и все connectors сразу;
- второй Git hosting;
- automatic rebrand/white-label;
- routine/self-service admin break-glass product capability (emergency out-of-band privileged procedure по G0-D3 обязательна и приводит к incident/quarantine);
- privacy hard purge/filtered history export;
- GitLab-outage stale reads;
- OpenSearch без измеренной необходимости.

**Stop-триггеры пересмотра Git-native канона:** обязательное realtime collaboration либо обязательные page-level read ACL с прямым доступом людей к Git. Это требует отдельного ADR и переоценки, а не скрытой database-first прослойки.

#### Границы extraction и отсутствующие входные артефакты

1. **Starter template отсутствует.** В workspace не найден отдельный starter template или его file reference. Имеющиеся `architecture-spine.md`, `planning-input.md` и design package не следует переименовывать в starter template.
2. **PRD отсутствует.** Отдельный PRD/product brief не найден. `spec.md` v1.3 содержит продуктовые цели, роли, R/I, acceptance и backlog, но не объявлен PRD.
3. **Отдельный UX contract отсутствует.** Не найдены `DESIGN.md`, `EXPERIENCE.md` или самостоятельный UX contract. UX-требования распределены по `spec.md` T02/T04/T07/T08, `components/open-webui-fork.md`, ADR-09, ADR-12, integration и G0-D8/D15.
4. **Отдельного notification UX contract также нет.** Доступны только перечисленные queue/event/status требования; каналы и оформление дополнительных уведомлений не заданы.
5. **Доказательные ограничения:** A01–A36 и CF-01–CF-30 не выполнялись; browser editor evidence отсутствует; production AD/live revocation SLO, production object-store ACL, реальные hoster.ai inputs, production quality/performance thresholds и legal clearance остаются открытыми.
6. **Существующие E00–E08 и T00–T20 сохранены как источники декомпозиции.** Ниже зафиксирован approved epic/story breakdown; новые E IDs и commitments не создаются. Крупные работы разделены на single-dev stories с суффиксами T03a/T03b, T04a/T04b, T05a/T05b, T07/T07b, T10a/T10b, T12a/T12b, T13a/T13b и T18a/T18b; T19/T20 остаются deferred без новых epic/story IDs.

### UX Design Requirements

Каждый пункт содержит проверяемый scope. Это не утверждение, что проверка уже выполнена.

#### UX-DR1 — Единый managed experience

Бизнес-пользователь и approver проходят каталог → документ → редактирование → агент → diff → решение → merge без Git/CLI или второго business application.

**Проверка:** A01 и G1 end-to-end с двумя независимыми пользователями; R01, T07/T08.

#### UX-DR2 — Feature flag и сохранение существующего UX

Managed KB opt-in не меняет personal Notes, ordinary chats и per-user chat privacy; Notes не становятся каноном managed corpus.

**Проверка:** feature off/on regression, A20; private Notes → managed import только через MR.

#### UX-DR3 — Spaces/tree/breadcrumbs/deep links

Навигатор показывает Spaces, дерево из Git, parent/child, breadcrumbs и stable-ID deep links; rename/move сохраняет UUID и ссылку.

**Проверка:** A01/A21, вложенные страницы, same basename, Cyrillic paths и rename внутри repository=Space.

#### UX-DR4 — Авторизованное дерево без disclosure

Tree/titles/parent relationships фильтруются сервером до response; нет загрузки полного корпуса без authorization/bounds и нет cached title/content после revoke.

**Проверка:** A04/A11/A32, cross-Space IDOR и anti-enumeration `NOT_FOUND`.

#### UX-DR5 — Direct document read

Whole/section read показывает exact revision, path/heading context, section anchors, bounds, cursor и explicit `truncation=true|false`; repeated headings адресуются occurrence/section.

**Проверка:** A02/A21, длинные страницы, повторяющиеся headings, next cursor и отсутствие silent text loss.

#### UX-DR6 — Search, citations и historical read

Exact/semantic search работает только в active published snapshots; ответ содержит citations с document/revision/section. Stale candidate не подменяется historical content; explicit historical read отдельно маркируется и авторизуется.

**Проверка:** A03/A22, preflight/pending/rejected exclusion, stale rejection, explicit no-answer/abstention.

#### UX-DR7 — Выбранный TipTap adapter

WYSIWYG direction — TipTap adapter с canonical serializer, front-matter boundary, immutable attachment metadata и full source diff; raw canonical Markdown не заменяется Notes/Turndown projection. WYSIWYG editing сохраняется; realtime collaborative editing/CRDT исключён из MVP. Concurrent authors получают conflict detection, exact/fresh revisions, полный diff и новую ProposalVersion вместо shared realtime state или automatic conflict merge.

**Проверка:** round-trip front matter/body/table alignment/attachment refs/Cyrillic и source diff, conflict/fresh-revision/new-ProposalVersion flow. **Статус:** G0-D8 APPROVED, реализация и T04 gate впереди; текущий TipTap path имел normalization/loss, PASS не заявлен.

#### UX-DR8 — IME и composition

Русский ввод и IME/composition не должны терять или переупорядочивать текст, canonical constructs и attachment metadata; unsaved buffer не выдаётся за durable draft.

**Проверка:** browser IME/composition, кириллица, вставка/редактирование, save/restart. **Статус:** G0-D15 deferred to T04, browser checks не выполнялись.

#### UX-DR9 — Accessibility

Tree, editor, navigation и review actions доступны с keyboard и screen reader; focus/labels/actions не раскрывают недоступное содержимое.

**Проверка:** keyboard/accessibility smoke для read/edit/review/accept/reject/cancel. **Статус:** T04/T07 gate, не PASS.

#### UX-DR10 — Cyrillic, Unicode и exact codes

Кириллические пути, Unicode/NFC variants, exact source codes, stable links и repeated headings не создают ambiguity; policy paths проходят lossless absolute↔relative mapping.

**Проверка:** A21, CF-27/CF-28, NFC/NFD/trailing separator, `DOC-0001` без lowercase rewrite.

#### UX-DR11 — Durable draft и unsaved navigation

Autosave создаёт/обновляет пользовательскую draft branch через GO со статусом `draft` и не меняет `main`; unsaved navigation guard предупреждает о несохранённом buffer.

**Проверка:** T04 restart recovery, draft attribution, buffer не отображается как сохранённый draft.

#### UX-DR12 — Concurrent editing без last-write-wins

Два редактора получают явный конфликт/«страница изменилась» с просмотром разницы; silent overwrite и automatic conflict merge запрещены.

**Проверка:** A08/T04 для editor conflict, fresh revision, full diff и новой ProposalVersion; A09 проверяется отдельно в E04.2/E04.3 для concurrent accepts, а не закрывается editor story.

#### UX-DR13 — History и restore

Business history показывает авторизованные exact revisions с ancestry/cursor и attribution; restore выбирает exact revision и создаёт revert-MR/new commit без history rewrite.

**Проверка:** A10 Full/direct в E03.1 для restart/history/revert-MR и Supporting в E04.2 для merge-recovery ancestry/principals; no silent substitution другой revision или history rewrite.

#### UX-DR14 — Archive и восстановление структуры

Archive — reviewed MR с date/reason/replacement; restore создаёт `archived=false` без `archive`. Потомки явно архивируются в том же MR или получают repaired parent/link.

**Проверка:** CF-03, archive/replacement/descendants, новый canonical snapshot удаляет архивное из index.

#### UX-DR15 — Рабочий контекст агента

Sidebar chat имеет scope selector page/subtree/Space/allowed Spaces; selection содержит page ID+SHA, явные full/partial context limits и citations.

**Проверка:** T08/T09, scope не расширяет AuthzContext, длинный контекст возвращает explicit bounds/truncation.

#### UX-DR16 — Ограниченные agent proposals

Первый slice поддерживает curated single-page body create и anchored body patch. Unsupported bulk/subtree/attachment/whole-document/front-matter operations отклоняются сервером с безопасной ошибкой.

**Проверка:** A05/A17/A21, forbidden diff через UI/OpenAPI/call_tool даёт ноль writes.

#### UX-DR17 — Полный review «было/стало»

Review показывает текст и supported formatting, exact `base_sha`/`proposal_sha`, affected files, rationale/evidence/provenance и author/version-author/requester/run.

**Проверка:** T07/A01/A07, business approver без GitLab user видит тот же exact diff, который применяет GO.

#### UX-DR18 — Видимость machine-significant changes

Diff отдельно раскрывает front matter, ownership/origin, `valid_until`, tree/structure moves, stable-ID links, archive/replacement и scope-значимые атрибуты.

**Проверка:** swapped target UUID, outer/inner origin mismatch, hidden archive/front-matter change невозможно пропустить незамеченным.

#### UX-DR19 — Attachments в read/edit/review

UI показывает additions/removals/revisions и immutable `{object_id,version,sha256,size,media_type,source_ref}`; attachment links наследуют Space ACL и не используют mutable current URL.

**Проверка:** A22/I13, immutable version/hash, cross-Space denial, review точно соответствует merge payload.

#### UX-DR20 — Media warnings и provenance

Auto descriptions помечаются как автоматические и ссылаются на оригинал страницы/слайда; critical/handwritten media без human verification не попадают в index/answer.

**Проверка:** T17/A22, media class/verification labels, citation ведёт на original, warning виден пользователю.

#### UX-DR21 — Достоверность preview как merge gate

Недостоверный diff/preview, скрытое metadata/media изменение или невозможность показать supported formatting блокирует merge из платформы.

**Проверка:** ADR-09/T07, отсутствие merge при incomplete preview; UX не создаёт видимость контроля.

#### UX-DR22 — XSS и active content

WYSIWYG/preview sanitation защищает от XSS, executable HTML/MDX и hidden text; XSS-risk rendering блокирует preview/merge, malicious imports отклоняются до corpus/preview.

**Проверка:** A23, XSS/MDX/traversal/symlink/secrets/oversize fixtures. **Статус:** browser XSS gate T04/T07 не выполнялся.

#### UX-DR23 — Review actions и version invalidation

Accept/reject/cancel/comment/edit привязаны к exact `proposal_sha`; edit/rebase/new commit создаёт ProposalVersion и сбрасывает approval. Author/version-author/requester не может self-approve.

**Проверка:** A06/A30, stale accept получает version mismatch, версия редактора требует нового independent approval.

#### UX-DR24 — Pending/group review queues

Pending list и group-assigned queues содержат exact base/proposal, bounded pagination и longest-normalized-prefix assignment без union с parent prefix; reload сохраняет работу.

**Проверка:** A07/A26/CF-10, `/` против `/pricing`, mover меняет grants и queue, GitLab user не требуется.

#### UX-DR25 — Идемпотентные действия пользователя

Double click accept/reject и reload не создают новое решение/merge attempt; browser retry использует тот же `Idempotency-Key` и exact payload.

**Проверка:** A07, replay по `decision_id`, изменённый payload требует новой операции, а не reuse key.

#### UX-DR26 — Явная lifecycle модель

UI различает `draft`, `in_review`, `published`, `indexed`, `archived`, `conflicted`; `published` появляется только после verified merge, `indexed` позже по active snapshot.

**Проверка:** I14, Git/MR-derived states отдельно от index projection; optimistic UI не является canonical outcome.

#### UX-DR27 — Recovery, quarantine, timeout и preflight

`recovery_required`/quarantine не маскируются под успех/отсутствие merge; inactive preflight и `INDEX_NOT_READY` явно отличаются от published/indexed. Timeout не предлагает blind retry или новый decision key.

**Проверка:** A27/A28/A31/A35, human-readable recovery state и запрет новых merges target.

#### UX-DR28 — Человекопонятные конфликты

`STALE_BASE` отображается как «Документ изменился», показывает разницу и предлагает новую работу от fresh revision; `PROPOSAL_VERSION_MISMATCH` обновляет review без повтора старого accept.

**Проверка:** A08/T07, неинженер завершает сценарий без Git-терминологии.

#### UX-DR29 — Единая модель ошибок и retry

Ошибки содержат code, message, request_id и retryable; `RECOVERY_REQUIRED` не предлагает новый merge workaround, `UPSTREAM_UNAVAILABLE` не показывает optimistic merged, `LIMIT_EXCEEDED` сопровождается bounds/cursor.

**Проверка:** integration §4.3–4.4, anti-enumeration, safe sanitized details и поведение retry по каждому коду.

#### UX-DR30 — DocOps notifications и очередь актуальности

`valid_until` создаёт revision-bound `scheduled/due/in_review/resolved/removed` projection и authorized review queue/event; expiry не даёт access и не архивирует автоматически. Кнопка/канал «нашёл ошибку» создаёт только `docops-correction-task-v1` с отдельным `open/in_review/resolved/cancelled` lifecycle, exact revision, stable actor, policy owner, evidence hash и idempotency; исправление идёт через MR/human decision/GO merge. Task не является canonical content или DecisionRecord.

**Проверка:** CF-06/CF-10/CF-20 и [correction contract](../../specs/corporate-kb/contracts/docops-correction-api.md), future/expired/removed dates, exact document revision, deleted date → `review_required=false,valid_until=null`, create/get/resolve/cancel negatives и no-MR evidence resolution.

#### UX-DR31 — Source/import/sync feedback

Dry-run показывает losses/errors/security/PII/media blockers; source UI выводит no-op/outstanding/conflict/tombstone, seen/proposed/merged lag и stale/source ACL/owner feedback.

**Проверка:** A13/A14/A16, unsupported format/extraction loss не выглядит success, source deletion создаёт review, а не silent deletion.

#### UX-DR32 — Revocation во время live UX

Revocation инвалидирует contexts/cursors, закрывает stream/subscription и прекращает новые payloads; уже доставленный текст не объявляется reversible.

**Проверка:** A11/A25, revoke между candidate/payload и во время streaming; пользователь получает safe denial без protected content.

#### UX-DR33 — UX observability и performance evidence

Tree/read latency, truncation, draft/proposal result, review SHA mismatch/conflict, preview reliability, UI retry/idempotency и TTFT/full response наблюдаются без raw private content.

**Проверка:** холодный/тёплый measurements с corpus SHA/config/concurrency; численные UX/performance thresholds назначает владелец.

#### UX-DR34 — Реальная UX acceptance, а не UI PASS по наличию экрана

Неинженер проходит pending queue → read/edit → diff/rationale/evidence → accept/reject/cancel → history/restore; UI mock не закрывает G1/G2. Browser/IME/accessibility/XSS/full managed preview остаются отдельным T04 gate.

**Проверка:** A01/A06–A10/A22/A23 и G1/G2 real evidence; текущий статус browser checks — deferred, не выполнено.

**По уведомлениям:** в источниках определены in-app queues, group review queues, DocOps events, index/source/recovery statuses и revocation/subscription behavior. Требований к email/push-каналам, их шаблонам или доставке нет; выводить их не следует.

### FR Coverage Map

R01: E02 Managed documents & access — единый интерфейс каталога и пользовательских сценариев
R02: E02 Managed documents & access + E03 Save & history — документная модель, stable IDs, tree, WYSIWYG и сохранение canonical content
R03: E02 Managed documents & access — canonical direct read по exact revision
R04: E05 Published knowledge pipeline — exact/semantic retrieval только по активному published корпусу
R05: E02 Managed documents & access — stable identity и Space ACL
R06: E04 Governed agent workflow — agent/connector/LLM не публикуют напрямую; apply только через GO
R07: E04 Governed agent workflow — MR proposal и append-only ProposalRecord
R08: E04 Governed agent workflow — canonical DecisionRecord и независимое согласование
R09: E03 Save & history + E04 Governed agent workflow — Git revisions, restore, доказуемая публикация и exact merge evidence
R10: E04 Governed agent workflow — сериализация, idempotency и recovery
R11: E05 Published knowledge pipeline — пересобираемый versioned index
R12: E06 Migration & portability — безопасный import и controlled cutover
R13: E06 Migration & portability + E08 Repeatable client delivery — curated-правки и source contracts при import и external sync
R14: E06 Migration & portability — clone/manifests, backup и restore
R15: E07 Internal pilot acceptance — санкционированный inference и data profiles
R16: E04 Governed agent workflow — ограниченный execution capability
R17: E08 Repeatable client delivery — повторяемый dedicated deployment
R18: E01 Contract sandbox & defect prevention + E07 Internal pilot acceptance + E08 Repeatable client delivery — regression, evaluation и эксплуатационные доказательства

Cross-cutting R05, R16 и R18 дополнительно обязательны во всех связанных эпиках и stories, независимо от primary owners в этой multi-primary карте.

## Approved Delivery Structure

## Epic 0: Foundation audit

Утверждённый baseline Open WebUI + GitLab + PostgreSQL, ADR-03–ADR-16/design capabilities и owner G0 review. Завершён в T00.

**FRs covered:** R18 (baseline evidence и owner approval).

## Epic 1: Contract sandbox & defect prevention

QA получает готовый воспроизводимый two-Space sandbox и executable validation reports для текущих документов, policies, proposals, decisions и index snapshots. Sandbox даёт usable deterministic defect evidence до feature work и остаётся тонким QA adapter над существующими contracts и CI, а не будущим technical framework.

**FRs covered:** R18.

## Epic 2: Managed documents & access

Stable IDs, дерево документов из Git, canonical direct read и единая Space ACL с identity/AuthZ adapter.

**FRs covered:** R01,R02,R03,R05. Published exact/semantic retrieval R04 принадлежит E05 и не закрывается E02.

## Epic 3: Save & history

Draft/save-to-branch, Git revisions, конфликты, история и restore через revert-MR без перезаписи истории.

**FRs covered:** R02,R09,R10.

## Epic 4: Governed agent workflow

MR proposal → полный review → canonical DecisionRecord → human decision → GO merge с ограниченными agent capabilities и recovery.

**FRs covered:** R06,R07,R08,R09,R10,R16.

## Epic 5: Published knowledge pipeline

CI index из published `main`, ancestry/SHA/ACL guards, scoped exact/semantic retrieval и пересобираемые projections.

**FRs covered:** R04,R11.

## Epic 6: Migration & portability

Dry-run и controlled unpublished bulk, exact-SHA cutover/preflight/activation, post-cutover MR-only imports, clone+decisions/assets manifests, mirror/metadata backup и restore.

**FRs covered:** R12,R13,R14.

## Epic 7: Internal pilot acceptance

Реальный корпус продаж, санкционированный inference, evaluation, hardening и pilot runbook.

**FRs covered:** R15,R18.

## Epic 8: Repeatable client delivery

Один выбранный connector, external updates, второй isolated deployment и эксплуатационные runbooks.

**FRs covered:** R13,R17,R18.

### Dependencies

E00 завершён. E01 → E02 → E03 → E04. E05 начинается после E02/E03. Отдельная E06.1/T12a dry-run/admission работа может выполняться после T03/T04 параллельно T05/T10 без canonical writes; полный T12/T12b cutover merge lifecycle требует T03,T04,T05 и использует односторонний preflight/published artifact из E05.2/T10, поэтому full T12 не выполняется параллельно T05. E06.3 complete export следует за E04.2/E06.2, а E06.4 backup/rebuild/restore — за E06.3/E06.2 и использует существующий E04.7 correction contract. E07 следует за E04–E06 и завершается на G2. E08 следует за G2 и ведёт к G3. Полный T18/G3 в E08.5 явно зависит от E08.2/T16 connector; necessary pilot/T18a не закрывают full T18 без T16. T19/T20 не являются зависимостями.

Cross-cutting R05, R16 и R18 дополнительно обязательны во всех связанных эпиках и stories.

## Component boundaries and consolidation rationale

- **E02/E03/E04 — Open WebUI, разные пользовательские capabilities.** Эти эпики используют общие Open WebUI seams, но не объединяются в один крупный UI layer: E02 отвечает за authorized navigation/direct read и identity/policy context, E03 — за durable draft/save/history и lossless editor adaptation, E04 — за proposal/review/decision/merge. Разделение read, save и merge соответствует самостоятельным пользовательским результатам и сохраняет единый canonical Git/GO contract.
- **E05/E06 — общий CI/index contract, односторонний artifact boundary.** E05 владеет index engine, validated inactive preflight и published/pointer lifecycle. E06 владеет import, migration и cutover/activation и только потребляет versioned preflight/index artifact из E05 после freeze/protection. E05 не зависит от E06 и не активирует Space; E06 не создаёт второй index/preflight engine, поэтому circular dependency отсутствует.
- **E07.3/E08.4/E08.5 — pilot hardening против repeatable client delivery.** E07.3 ограничивается эксплуатационным hardening и evidence внутреннего пилота для G2. E08.4 повторяет config-only dedicated deployment для второго клиента, а E08.5 завершает backup/restore/upgrade и полный G3 с уже выбранным connector из E08.2. Общие runbooks и artifacts переиспользуются, но deployment и acceptance работа не дублируется.

## Epic 0: Foundation audit

Утверждённый baseline Open WebUI + GitLab + PostgreSQL, ADR-03–ADR-16/design capabilities и owner G0 review. Завершён в T00.

### Story 0.1 (T00): Baseline audit and owner G0 approval

As a product owner,
I want a verified upstream baseline and an approved ADR/design package,
So that implementation starts from proven technical and security constraints.

Requirements: R18; I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I11,I12,I13,I14 (audit coverage); UX-DR2, UX-DR34; A20,A24,A34; A01–A36 mapping-only, not product acceptance.
Acceptance ownership: Full/direct — не назначены; Supporting — A20,A24,A34; A01–A36 только audit mapping, не product acceptance.

**Acceptance Criteria:**

**Given** normative R/I requirements and the approved architecture package,
**When** the upstream seams and synthetic GitLab, CI, identity, database and retrieval capabilities are audited,
**Then** `baseline.md`, the capability matrix and sanitized evidence are recorded with pinned versions and explicit adapter gaps.
**And** all owner decisions G0-D1–G0-D17 are recorded as APPROVED in `g0-review.md`, and `tasks.md` reports **T00 DONE / G0 APPROVED**.

**Status:** DONE

**Dependencies:** none.

**Evidence:** `specs/corporate-kb/baseline.md`, `specs/corporate-kb/evidence/t00/`, `specs/corporate-kb/g0-review.md`.

**Rollback/upgrade impact:** no product code or production data was changed; no production migration was performed.

<!-- End story repeat -->

## Epic 1: Contract sandbox & defect prevention

QA получает готовый воспроизводимый two-Space sandbox и executable validation reports для текущих документов, policies, proposals, decisions и index snapshots. Sandbox даёт usable deterministic defect evidence до feature work и остаётся тонким QA adapter над существующими contracts и CI, а не будущим technical framework.

### Story 1.1 (T01): Reproducible two-Space sandbox and executable defect evidence

As a QA engineer validating business outcomes,
I want a ready-to-run reproducible two-Space sandbox with executable validation reports for current documents, policies, proposals, decisions and index snapshots,
So that I can reproduce defects and obtain usable deterministic evidence before feature work, rather than merely prepare a framework for future scenarios.

Requirements: R18; I08,I09,I10,I11,I12; UX-DR10, UX-DR29, UX-DR34; A21,A33; CF-01–CF-30.
Acceptance ownership: Full/direct — A21,A33 только в contract-harness scope; Supporting — остальные применимые A01–A20,A22–A32,A34–A36 через CF-30 design coverage, без автоматического VERIFIED.

**Acceptance Criteria:**

**Given** G0 is approved, the current contracts and synthetic two-Space fixtures are available, and feature work has not yet started,
**When** QA launches the sandbox using its documented reproducible command,
**Then** it executes validation of current documents, access/approval policies, ProposalRecords, DecisionRecords and index snapshots and produces executable validation reports with exact versions, environment, commands, expected/actual results and raw SHA-256.
**And** every failure provides usable deterministic defect evidence with a minimal reproduction fixture, stable IDs/SHAs, sanitized mismatch details and rerun instructions, while passed, failed, BLOCKED and unexecuted checks remain explicitly distinct.

**Given** G0 is approved and the pinned upstream/toolchain is available,
**When** the team provisions only the two synthetic repository-per-Space fixtures and contract runners needed by the delivery stories,
**Then** front matter, ProposalRecord, DecisionRecord, index snapshot, AuthzContext and policy schemas verify deterministic serialization, full-SHA and hash semantics against the approved fixtures.
**And** the harness remains a thin QA adapter over existing contracts and CI rather than a new runtime service, canonical store or general-purpose testing platform.

**Given** the prepared CF-01–CF-30 vectors and user-value acceptance scenarios,
**When** contract, semantic and consumer checks execute,
**Then** invalid IDs, revisions, policy bundles, stale contexts, malformed payloads and forbidden capabilities produce explicit rejection without writes, while the applicable tree/read, draft/save, proposal/review and restore scenarios have reproducible positive fixtures.
**And** every surfaced API/tool error uses the unified `{code,message,request_id,retryable}` shape with sanitized optional details, and `LIMIT_EXCEEDED` includes the effective bounds plus a valid continuation cursor whenever more authorized results exist.

**Given** truncation, cursor and retry vectors,
**When** a bounded page or operation is replayed,
**Then** `truncated=false` is equivalent to `reason=none` and `next_cursor=null`, `truncated=true` has a non-none reason and next cursor, and identical retries preserve their operation identity without duplicate side effects.
**And** doubles used for local state-machine checks are labelled as unit evidence and never reported as real GitLab, IdP, PostgreSQL, CI or hoster.ai integration acceptance.

**Given** a completed harness run or an incompatible contract change,
**When** evidence and upgrade impact are reviewed,
**Then** every executed check records command, environment, result and raw SHA-256; machine output stays in `_bmad-output/test-artifacts/t01`, while sanitized evidence is stored in `specs/corporate-kb/evidence/t01/`.
**And** incompatible contract changes require an explicit `schema_version`, migration and rollback decision instead of silently changing canonical or hash semantics, and prepared but unexecuted vectors remain DESIGN_NOT_EXECUTED.

**Dependencies:** E00 complete.

**Evidence:** Planned evidence only, not executed tests: `contracts/projection-mapping.md`, `contracts/t01-contract-tests.yaml`, minimal two-Space fixtures, focused CI results and sanitized T01 evidence.

**Rollback/upgrade impact:** fixtures are disposable; no production corpus or migration is created, and removal of the harness does not change product runtime behavior.

<!-- End story repeat -->

## Epic 2: Managed documents & access

Stable IDs, дерево документов из Git, canonical direct read и единая Space ACL с identity/AuthZ adapter.

### Story 2.1 (T02): Git-backed document tree and canonical direct read

As a business reader or author,
I want to navigate a Git-backed document tree and read exact document revisions,
So that I can use stable links and sections without depending on a mutable database copy.

Requirements: R01,R02,R03; I08,I09,I11,I12,I13,I14; UX-DR1, UX-DR3, UX-DR4, UX-DR5, UX-DR10, UX-DR14, UX-DR19, UX-DR26; A01,A02,A21,A22,A32; CF-03, CF-05, CF-10, CF-27, CF-28.
Acceptance ownership: Full/direct — A01,A32; Supporting — A02,A21,A22. R05/A04 и full negative ACL acceptance не принадлежат этой story.

**Acceptance Criteria:**

**Given** two repository-per-Space fixtures with Markdown/front matter documents,
**When** the user opens a Space tree,
**Then** the server returns parent/child relationships, stable opaque document IDs, breadcrumbs and stable-ID deep links from Git metadata within the explicit synthetic read scope supplied by the E01 harness, preserving UUID after rename/move, without loading an unbounded corpus into the browser.
**And** full Identity/AuthZ policy enforcement, unauthorized title/path/content denial, cross-Space IDOR and anti-enumeration acceptance are not closed by this story; they belong to E02.2/E02.3 and E04.3. Exact-revision whole/section direct read with bounds, cursor and explicit truncation remains in scope.

**Given** an exact canonical document revision,
**When** the user reads the whole document or a section,
**Then** the response includes the exact revision SHA, path/heading context, section anchors and occurrence for repeated headings, explicit bounds, cursor and `truncated=true|false` with no silent text loss.
**And** stable-ID links and rename/move provenance resolve to the same Space/snapshot, while duplicate IDs, cycles, orphans, swapped targets, invalid paths and ambiguous links produce validation errors and no publication/index.

**Given** canonical attachments and archive metadata in a direct read,
**When** the UI renders them,
**Then** every attachment exposes the full immutable `{object_id,version,sha256,size,media_type,source_ref}` tuple under the same Space ACL, never a mutable unhashed current URL.
**And** `archived=true` is accepted only with a complete `archive` object, a non-null `replacement_document_id` resolves to another active document in the same Space, descendants are explicit rather than implicitly cascaded, and a restored canonical revision has `archived=false` with no `archive` object.

**Given** Cyrillic and compatibility fixtures for documents, policies and source provenance,
**When** paths and identifiers are validated or projected,
**Then** document paths are repository-relative NFC, NFC/NFD collisions, duplicate/trailing separators, backslashes, absolute paths and `..` cannot create ambiguous mappings, and source ID `DOC-0001` retains its exact case.
**And** policy path mapping is lossless for absolute↔relative forms, including `/` ↔ empty prefix and `/pricing` ↔ `pricing`; `/pricing/` and other ambiguous separator variants cannot create a second rule.

**Dependencies:** E01.1 contract harness and two-Space fixtures.

**Evidence:** Planned evidence only, not executed tests: `front-matter.schema.json`, Git tree/read fixtures, section/cursor cases, full attachment tuples, archive invariants, Unicode/path vectors and structural cross-Space fixture checks; full negative ACL evidence принадлежит E02.2/E02.3 и E04.3.

**Rollback/upgrade impact:** no canonical write path is introduced; invalid fixtures remain unpublished and are excluded from the index.

<!-- End story repeat -->

### Story 2.2 (T03a): Stable identity core and nested group snapshots

As a business user and identity platform engineer,
I want one stable upstream LDAP/OIDC identity with complete group snapshots,
So that managed capabilities can identify the same person securely without email aliases or GitLab accounts for business owners.

Requirements: R05,R16; I02,I03,I04,I09,I10,I12; UX-DR2, UX-DR4; A04,A18,A24,A26,A33; CF-30.
Acceptance ownership: Full/direct — A24,A26; Supporting — A04,A18,A33.

**Acceptance Criteria:**

**Given** the pinned upstream authentication seams and a read-only encrypted LDAP or configured OIDC connection,
**When** a user authenticates and is provisioned through JIT,
**Then** the adapter keys identity by issuer-scoped `sub`, AD `objectGUID` or OpenLDAP `entryUUID`, preserves that identity across login/email renames and creates no GitLab user for a business owner.
**And** empty or invalid passwords are rejected before an LDAP bind, duplicate/ambiguous/cross-issuer identities fail closed, and email/login is never an identity fallback.

**Given** direct and nested group fixtures with joiner, mover and leaver events,
**When** group synchronization and JIT reconciliation run,
**Then** nested membership is resolved completely and emitted as ordered, epoch-matched identity/group snapshots with explicit empty-group results rather than stale membership reuse.
**And** an older sync result cannot overwrite a newer snapshot, and the identity adapter supplies no actor, group, tenant, run or policy override that a model or document can control.

**Given** existing personal Notes, ordinary chats and separately audited personal grants,
**When** the managed identity adapter is enabled or rolled back,
**Then** their upstream behavior and privacy remain unchanged, and personal grants are not silently converted into managed group grants.
**And** LDAP remains required for the MVP, while production AD checks are reported separately from synthetic OpenLDAP/OIDC results.

**Dependencies:** E02.1 canonical document/read model and its E01.1 harness.

**Evidence:** Planned evidence only, not executed tests: Full/direct A24,A26; supporting A04,A18,A33; real LDAP/OIDC sandbox results, stable-ID rename and duplicate/ambiguous identity cases, nested-group closure, empty snapshots and snapshot-ordering results. Existing T00 synthetic probes remain baseline evidence, not completion of this story.

**Rollback/upgrade impact:** rollback disables the managed identity configuration without falling back to stock email/provider-alias linking or changing personal Notes/ordinary chats. This story authorizes no production migration, credentials or deployment.

<!-- End story repeat -->

### Story 2.3 (T03b): Per-Space policy enforcement and revocation

As a platform security administrator and business approver,
I want versioned per-Space access/approval policy enforced consistently and revoked promptly,
So that every UI, tool, queue and sensitive operation uses the same current permissions.

Requirements: R01,R05,R16; I01,I02,I03,I04,I06,I08,I09,I10,I11,I12,I13,I14; UX-DR1, UX-DR4, UX-DR10, UX-DR15, UX-DR23, UX-DR24, UX-DR29, UX-DR32; A04,A11,A18,A22,A25,A26,A30,A31,A32,A33,A36; CF-01, CF-02, CF-09, CF-28.
Acceptance ownership: Full/direct — A04,A11,A18,A25,A26,A32,A33,A36; Supporting — A22,A30,A31.

**Acceptance Criteria:**

**Given** two repositories mapped to two Spaces with independent versioned access and approval policies,
**When** the adapter issues an `authz-context-v2` from the E02.2 identity/group snapshots,
**Then** each Space contains its own repository binding, policy bundle, full access/approval revision SHAs, group snapshot and revocation epoch, with no shared top-level policy or group binding.
**And** path-scoped approval selects exactly one longest-normalized-prefix rule without unioning parent-prefix groups, mixed policy revisions or borrowed bindings are rejected, `access` in front matter has no authorization effect, and CODEOWNERS remains engineering-only.

**Given** absolute and relative policy paths with Cyrillic NFC/NFD and separator variants,
**When** policies are validated and mapped,
**Then** `/` ↔ empty prefix and `/pricing` ↔ `pricing` round-trip losslessly, NFC is canonical where required, and NFD duplicates, `/pricing/`, repeated/backslash separators and `..` are rejected as invalid or ambiguous without activating the new bundle.
**And** `/` and `/pricing` approver groups remain disjoint, group-assigned pending queues follow only the selected prefix, and mover/leaver changes update queue eligibility without requiring a GitLab user.

**Given** an authenticated user accessing UI, API, tools, files, history, search or export,
**When** the server evaluates a managed capability,
**Then** only the Identity/AuthZ adapter writes managed upstream grants and `kb_authz`, all other schema writers are denied, and authorization is applied before any title, snippet, chunk, file or history payload is exposed.
**And** human accept/reject/cancel/edit/apply operations require an authenticated browser session plus CSRF/Origin validation, are never exported as agent tools, and cannot be invoked by a model-supplied actor, group, tenant or run identity.

**Given** background synchronization, a live subscription, cursor, export or approval operation,
**When** group membership, a path role, policy revision or revocation epoch changes,
**Then** refresh occurs within 15 minutes, empty or missing group claims revoke managed group-derived grants, affected contexts and cursors become stale, subscriptions close, and new payloads and sensitive operations stop.
**And** provider/IdP outage fails closed rather than extending cached allow indefinitely, revocation evidence demonstrates the 30-minute SLO for background paths and denial at the next sensitive recheck, and already delivered content is not claimed to be retractable.

**Given** denied, stale or bounded requests,
**When** an error reaches UI or a tool,
**Then** it uses `{code,message,request_id,retryable}` with sanitized details and safe anti-enumeration behavior, and no denial reveals protected content or object existence.
**And** a stale policy/group/revocation cursor cannot borrow another Space binding or continue after revocation.

**Dependencies:** E02.2 stable identity/group snapshots and E02.1 canonical reads; production AD/live revocation checks require the corresponding real integration environment.

**Evidence:** Planned evidence only, not executed tests: A04,A11,A18,A22,A25,A26,A30,A31,A32,A33,A36; per-Space AuthzContext and policy-path fixtures, longest-prefix queues, CSRF/all-channel negatives, DB role denials, empty-claim/mover/leaver cases and measured refresh/revocation results. Existing T00 synthetic probes remain baseline evidence, not completion of this story.

**Rollback/upgrade impact:** rollback disables managed policy enforcement configuration without reopening cached or stock-alias access. Any owned schema change requires the component-owned external migrator and isolated upgrade rehearsal; this story authorizes no production migration, credentials or deployment.

<!-- End story repeat -->

## Epic 3: Save & history

Draft/save-to-branch, Git revisions, конфликты, история и restore через revert-MR без перезаписи истории.

### Story 3.1 (T04a): Durable drafts, guarded navigation and cursor-based Git history

As a business author,
I want autosaved branch-based drafts, visible conflicts and restorable Git history,
So that my work survives restarts and concurrent edits without silently overwriting canonical content.

Requirements: R02,R09,R10; I05,I06,I14; UX-DR11, UX-DR12, UX-DR13, UX-DR26, UX-DR28, UX-DR29, UX-DR33; A08,A10; CF-10, CF-20.
Acceptance ownership: Full/direct — A08,A10; Supporting — не назначены. Concurrent accepts/A09 принадлежат E04.2 с supporting enforcement в E04.3.

**Acceptance Criteria:**

**Given** an authorized author editing from the current target revision,
**When** a manual save or autosave is requested,
**Then** GO verifies the fresh `base_sha`, creates or updates the attributed user draft branch and commit through an idempotent operation, and leaves `main` unchanged with an explicit `draft` state.
**And** after a browser or service restart the durable branch draft is recovered with its author and exact revision, while an unsaved browser buffer is never presented as a durable draft.

**Given** an unsaved browser buffer or an autosave still in flight,
**When** the user attempts to close, reload or navigate away from the editor,
**Then** an unsaved navigation guard warns before the buffer can be lost and allows the user to stay until save or explicit discard completes.
**And** the guard distinguishes the transient buffer from the last durable draft SHA, and a draft/proposal result is observable by `request_id` without logging the document body.

**Given** two editors whose proposals start from the same base,
**When** one target revision advances before the other save,
**Then** the second save receives a human-readable `STALE_BASE` conflict with a view of the difference and must start new work from the fresh revision.
**And** no last-write-wins update, automatic conflict merge, silent text loss or unintended attachment/front-matter replacement occurs, including for Cyrillic content and immutable attachment revisions.

**Given** an authorized user viewing document history,
**When** the user pages, compares or restores an exact historical revision,
**Then** history and diffs come from Git with correct attribution and ancestry, bounded history pages expose an explicit truncation reason and next cursor, and the cursor binds the ordered per-Space history snapshot, scope, policy/group/revocation and actor epochs.
**And** restore selects the exact displayed revision and creates a reviewed revert-MR with a new commit rather than rewriting history or committing directly to `main`; stale cursor, ambiguous revision, unauthorized historical object or cross-Space reference is rejected without exposure or canonical writes.

**Dependencies:** E02.3 per-Space policy/revocation and E02.1 canonical document model.

**Evidence:** Planned evidence only, not executed tests: A08,A10; branch/commit attribution, idempotent autosave/restart, unsaved navigation guard, stale-base editor conflict, bounded history cursor/truncation and exact-revision revert-MR ancestry with environment and commands. Concurrent accepts/A09 evidence принадлежит E04.2 с supporting enforcement в E04.3.

**Rollback/upgrade impact:** rollback disables the managed draft feature while retaining Git branches and history; published content is corrected only through a new revert-MR, never history rewrite. Schema upgrades use the component-owned external migration procedure after isolated rehearsal; no production corpus or migration is created by this planning story.

<!-- End story repeat -->

### Story 3.2 (T04b): Lossless TipTap adapter and browser editor gate

As a business author,
I want the selected TipTap editor to preserve every supported canonical construct through a successful edit round-trip,
So that WYSIWYG editing is safe for canonical Markdown, machine-significant metadata and accessible Russian input.

Requirements: R01,R02,R09; I01,I02,I03,I05,I06,I09,I14; UX-DR7, UX-DR8, UX-DR9, UX-DR10, UX-DR19, UX-DR21, UX-DR22, UX-DR34; A01,A08,A23; CF-03, CF-27.
Acceptance ownership: Full/direct — не назначены; Supporting — A01,A08,A23. Сохраняется WYSIWYG editing; realtime collaboration/CRDT не добавляется в MVP.

**Acceptance Criteria:**

**Given** the owner-selected TipTap adapter and the complete canonical Markdown/front-matter fixture set,
**When** content performs parse → edit → serialize → parse round-trips through source diff and save,
**Then** every required fixture completes a successful lossless round-trip preserving the front-matter boundary, stable document IDs/links, table alignment, Cyrillic text, ownership/origin, `valid_until`, archive metadata, full immutable attachment tuples and all machine-significant changes.
**And** the resulting canonical source diff contains only user-intended changes, raw canonical Markdown remains recoverable for full review, and any normalization or loss of a required construct fails this acceptance criterion rather than being reclassified as a successful block or alternative outcome.

**Given** the successful canonical round-trip and a full source diff,
**When** the author edits and previews content,
**Then** the editor exposes all supported formatting and machine-significant metadata needed for trustworthy review, and no hidden front-matter, stable-link, archive or attachment change is omitted.
**And** an incomplete or unreliable preview prevents apply/merge until the exact proposal is faithfully represented, without weakening the mandatory successful round-trip criterion above.

**Given** the browser/IME/accessibility/XSS checks deferred from T00 by G0-D15,
**When** the T04 browser gate is executed on the pinned frontend,
**Then** Russian IME/composition preserves ordering and text, keyboard and screen-reader paths expose usable labels/focus/actions, and executable HTML/MDX, XSS and hidden active content are rejected before browser exposure, preview or save.
**And** these real browser checks are explicit completion criteria; WYSIWYG editing is retained, while realtime collaboration/CRDT remains out of MVP. Concurrent authors receive conflict detection, exact/fresh revisions, full source-difference review and a new ProposalVersion instead of shared realtime state or automatic conflict merge; prior headless TipTap normalization-loss or unexecuted browser checks are not marked PASS.

**Dependencies:** E03.1 durable draft/save/history path and its E02 prerequisites.

**Evidence:** Planned evidence only, not executed tests: Supporting A01,A08,A23; successful TipTap canonical round-trip and intended-only full source-diff fixtures, complete metadata/attachment preview, conflict detection with exact/fresh revisions and new ProposalVersion, and real browser IME, accessibility and XSS results with environment and commands. Realtime collaboration/CRDT is not a T04 acceptance item. The deferred browser gate remains incomplete until those results exist.

**Rollback/upgrade impact:** rollback disables the managed editor while retaining durable Git drafts and history; it does not substitute Notes/Turndown as canonical storage or declare a lossy adapter acceptable. Frontend upgrades use the seam registry and browser regression after isolated rehearsal; no production corpus or migration is created by this planning story.

<!-- End story repeat -->

### Story 3.3 (Tech-debt): Pytest baseline and harness unit tests

As a maintainer,
I want a pytest baseline and unit tests for the contract harnesses,
So that harness logic is verified independently of the contracts it validates.

Requirements: R18; I10; A01; CF-01.
Acceptance ownership: Full/direct — A01.

**Acceptance Criteria:**

**Given** the existing harnesses under `_bmad-output/test-artifacts/`,
**When** `uv run pytest -q` runs,
**Then** unit tests cover the reporter/sanitize utilities and the core validators for T02, T03a, T03b, T04a and T04b.
**And** tests pass and can be run in CI without external infrastructure.

**Dependencies:** E03.1, E03.2 harnesses.

**Evidence:** `pyproject.toml`, `uv.lock`, `tests/test_*_validators.py`, `tests/test_reporters.py`, 28 passed baseline.

<!-- End story repeat -->

## Epic 4: Governed agent workflow

MR proposal → полный review → canonical DecisionRecord → human decision → GO merge с ограниченными agent capabilities и recovery.

### Story 4.1 (T05a): Exact ProposalRecord and ProposalVersion lifecycle

As a business author,
I want every human or agent-assisted change captured as an immutable exact-SHA ProposalVersion,
So that the reviewed diff, metadata, rationale and evidence are precisely identified before any decision or merge.

Requirements: R02,R06,R07,R09,R10; I01,I02,I03,I04,I05,I06,I08,I09,I12; UX-DR14, UX-DR17, UX-DR18, UX-DR19, UX-DR23, UX-DR25, UX-DR28, UX-DR29; A05,A08,A22,A30; CF-03, CF-09, CF-19, CF-20.
Acceptance ownership: Full/direct — A05; Supporting — A08,A22,A30. Concurrent-merge acceptance/A09 отсутствует в этой story.

**Acceptance Criteria:**

**Given** an authorized create/edit request with an exact current base,
**When** GO creates a branch and MR for a whole-page edit or unambiguous partial patch,
**Then** it records exact `base_sha` and `proposal_sha`, the precise diff, rationale/evidence and an append-only ProposalRecord for that ProposalVersion with trusted author, version-author, requester, actor type, optional run and idempotency/payload metadata.
**And** an ambiguous patch, mismatched path/body identity or reused idempotency key with a different payload creates zero writes, while an identical replay returns the existing version and a defined no-op creates no empty publication.

**Given** an existing reviewed proposal,
**When** a new commit, edit or rebase changes its source HEAD,
**Then** GO creates a new ProposalVersion and ProposalRecord with a new `proposal_sha` and version author, invalidates prior approval, and rejects commands against the old SHA with `PROPOSAL_VERSION_MISMATCH`.
**And** every ProposalVersion preserves the exact affected files, front matter and stable-link changes plus full immutable `{object_id,version,sha256,size,media_type,source_ref}` attachment tuples for additions, removals and revisions.

**Given** an authorized archive or archive-restore request,
**When** GO creates its reviewed MR and ProposalRecord,
**Then** archive records the archive date and reason, an optional replacement that is another active document in the same Space, and explicit descendant handling in the same MR or through repaired parent/links without an implicit cascade.
**And** archive produces `archived=true` with a complete `archive` object, while restore produces `archived=false` with no `archive` object; self/other-Space/archived replacement targets and hidden descendant effects create zero canonical writes.

**Given** stale base, ambiguous patch, malformed evidence or bounded proposal input,
**When** validation rejects the request,
**Then** the result uses `{code,message,request_id,retryable}` with sanitized details, and `LIMIT_EXCEEDED` includes effective bounds and a continuation cursor where more authorized input exists.
**And** no error creates a branch, MR, ProposalRecord, grant, cursor advance or `main` write.

**Dependencies:** E03.2 lossless editor adapter and E03.1 durable drafts/history.

**Evidence:** Planned evidence only, not executed tests: A05 Full/direct; supporting A08,A22,A30; exact ProposalRecord/ProposalVersion fixtures, idempotency and path/body negatives, full attachment tuples, archive reason/replacement/descendants and restore invariant, and stale/ambiguous error cases. Concurrent-merge/A09 evidence отсутствует и принадлежит E04.2/E04.3. Existing T00 GitLab probes are capability evidence, not this product workflow's acceptance.

**Rollback/upgrade impact:** rollback freezes new proposal operations without enabling direct writes; existing MRs and append-only records remain intact, and accepted content corrections use reviewed revert-MRs. `kb_ops` changes belong only to GO through the external migrator after upgrade rehearsal.

<!-- End story repeat -->

### Story 4.2 (T05b): Canonical DecisionRecord, exact merge and conclusive recovery

As an independent business approver,
I want accept/reject/cancel decisions and GO merge outcomes bound to the exact reviewed ProposalVersion,
So that publication applies only what was approved and remains conclusive after retries, timeouts or crashes.

Requirements: R06,R07,R08,R09,R10; I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14; UX-DR23, UX-DR25, UX-DR26, UX-DR27, UX-DR28, UX-DR29, UX-DR33; A06,A07,A08,A09,A10,A27,A28,A29,A30,A34,A36; CF-09, CF-15, CF-17, CF-18, CF-20, CF-21, CF-23.
Acceptance ownership: Full/direct — A06,A07,A08,A09,A27,A28,A29,A30,A34,A36; Supporting — A10 для merge-recovery ancestry/principals. A09 и A28 имеют primary home в exact merge/per-target serialization/crash recovery этой story; A10 Full/direct history/revert ownership остаётся в E03.1.

**Acceptance Criteria:**

**Given** a human accept, reject or cancel command whose header, body and `decision_id` idempotency key match,
**When** GO records the decision,
**Then** one canonical DecisionRecord JSON and `record_sha256` are written identically to an append-only structured MR note and protected annotated `kb-decisions/<decision_id>` tag targeting the exact `proposal_sha`.
**And** reject/cancel durably close the MR without a merge attempt, an identical decision replay returns the same record, correction uses a new decision with `supersedes_decision_id`, and a missing/mismatched note, tag, target or hash is `DECISION_INVALID`, never a valid approval.

**Given** an independent approver and the ProposalRecord principals,
**When** any decision command is authorized,
**Then** an approver who is the original author, requester or current version editor is denied independently of the UI, and fresh group/path role plus matching policy bundle/access/approval revisions are mandatory.
**And** self-approval, stale SHA, policy mismatch or revocation produces the unified error shape and zero new `main` writes.

**Given** a valid accepted decision and fresh preconditions,
**When** GO applies the proposal,
**Then** it rechecks source and target SHAs immediately before the external call and creates only a real merge commit with first parent `base_sha`, second parent `proposal_sha`, and `Decision-ID`, `Decision-Note-ID`, `Decision-Hash` and `Approved-by` trailers.
**And** `main` remains unchanged before verified merge, squash/rebase/fast-forward and on-apply LLM regeneration are forbidden, and any parent/trailer/note/tag mismatch prevents a `merged` result.

**Given** two accepted decisions for different exact proposals targeting the same `(repository_id,target_branch)`,
**When** their applies become concurrent,
**Then** per-target serialization and the final `HEAD == base_sha` recheck permit at most one verified apply; the loser receives conflict/`STALE_BASE` with zero new `main` writes, and replay/reconciliation cannot create a second apply (A09).

**Given** a crash after GitLab merge but before projection, or a retry, lost response or other crash around the external merge call,
**When** GO reconciles the operation,
**Then** `merge_attempted` and durable per-target `recovery_required` are persisted before the first real merge attempt, and Git ancestry, notes, tags and trailers determine the recovered result without a duplicate merge (A28).
**And** identical `decision_id` or `(repository_id,target_branch,proposal_sha)` replay creates zero new attempts, timeout alone never becomes `failed` or merged, and only completed-request plus proven-no-merge evidence permits a conclusive failed outcome. Merge recovery preserves Git ancestry and trusted principals without history rewrite or silent revision substitution (Supporting A10); Full/direct restart/history/revert-MR acceptance remains in E03.1.

**Given** a conclusive failed, conflicted, invalid or unknown outcome,
**When** the UI or client considers retry,
**Then** only conclusive `failed` permits a guarded same-decision retry with a new attempt, exact base/proposal and fresh preconditions; conflicted and invalid are terminal, and unknown remains quarantined without blind retry or a replacement decision key.
**And** decision/merge correlation and recovery state are observable without raw private content, while the UI never presents timeout, `recovery_required` or quarantine as published success.

**Dependencies:** E04.1 immutable ProposalRecord/ProposalVersion lifecycle.

**Evidence:** Planned evidence only, not executed tests: Full/direct A06,A07,A08,A09,A27,A28,A29,A30,A34,A36; Supporting A10 merge-recovery ancestry/principals; canonical note+tag hashes, accept/reject/cancel replay, self-approval matrix, real GitLab parents/trailers, concurrent-accept/per-target serialization, crash-after-GitLab-merge-before-projection recovery without history rewrite, crash/reconciliation tuples and guarded-retry/terminal/unknown outcomes. Full/direct A10 restart/history/revert-MR evidence remains in E03.1. Existing T00 GitLab probes are capability evidence, not product acceptance.

**Rollback/upgrade impact:** rollback freezes new decisions/merges without enabling direct human or service merge; canonical decisions and unknown barriers remain intact and are never cleared as part of rollback. `kb_ops` changes belong only to GO through the external migrator after recovery/upgrade rehearsal.

<!-- End story repeat -->

### Story 4.3 (T06): Merge-only-GO enforcement, fencing and quarantine

As a platform security owner,
I want every write and merge path constrained by GitLab and GO with durable target recovery,
So that no actor, channel, race or crash can bypass independent approval or publish an uncertain outcome.

Requirements: R05,R06,R07,R08,R10,R16; I01,I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14; UX-DR16, UX-DR23, UX-DR25, UX-DR27, UX-DR29, UX-DR32; A04,A05,A09,A17,A18,A28,A29,A34,A36; CF-07, CF-18, CF-21, CF-23.
Acceptance ownership: Full/direct — A04,A05,A17,A18,A29,A34; Supporting — A09,A28,A36. Primary A09/A28 acceptance находится в E04.2; здесь проверяются adversarial fencing/quarantine.

**Acceptance Criteria:**

**Given** a protected post-cutover `main` and separated proposal, merge, connector and CI credentials,
**When** any non-privileged business, engineering, bot, connector, CI or source-managed identity attempts direct push, direct merge or auto-merge,
**Then** GitLab and GO independently deny every managed path, and only the GO merge service identity can create a managed verified merge after a canonical human decision.
**And** CI cannot push even a derived `INDEX.md`; routine/self-service admin break-glass product capability is absent. If a privileged GitLab Owner bypasses this boundary out of band, reconciliation detects the unexpected target history, does not label it a GO merge, raises an integrity incident and quarantines the affected target until conclusive reconciliation and reviewed remediation complete. Restricted privileged accounts, audit and the explicit G0-D3 emergency break-glass/incident runbook are mandatory governance controls.

**Given** direct, deferred, note-attached, ordinary, native or temporary chats, channels, automations, external OpenAPI and `call_tool`,
**When** an actor requests accept/reject/cancel/merge/grants, arbitrary Git, shell/terminal, generic SQL/filesystem, Tool Creation or an unaudited custom tool,
**Then** deny-by-default server enforcement rejects the capability even when the chat user is an admin, and no human execution context or merge credential is exposed as a tool.
**And** private Notes can enter managed knowledge only through MR, and deterministic connector/source-managed updates still require human review and GO merge.

**Given** two accepts or proposals targeting the same `(repository_id,target_branch)`,
**When** their merge operations race or a target HEAD changes between precondition checking and apply,
**Then** the per-target lock and fencing token serialize the critical section, GO rechecks `HEAD == base_sha`, at most one verified apply succeeds, and the loser receives conflict/stale-base with zero new `main` writes.
**And** a stale lock owner cannot record a result or clear a barrier, and the lock is never held during review or inference.

**Given** a crash, timeout, lost response or lock handover before, during or after the external merge call,
**When** the target is reconciled,
**Then** every unresolved accept on that target blocks all new merges through durable `recovery_required` and quarantine flags until target-wide Git-derived reconciliation proves each outcome and request completion.
**And** crash-after-merge-before-projection recovers the existing commit without duplication, unknown or invalid-with-unknown never auto-clears by timeout, terminal label, supersedes or generic TTL, and a second MR remains denied while evidence is inconclusive.

**Given** stale base/proposal SHAs, a policy bundle/revision mismatch, self-approval or group/path revocation before merge,
**When** GO performs its final sensitive recheck,
**Then** it rejects the operation with zero new `main` writes and preserves any required recovery barrier.
**And** only a conclusive `failed` state may receive a guarded same-decision retry with a new attempt and fresh preconditions; `conflicted` and `invalid` are terminal and non-retryable, and blind retry with a new decision or idempotency key is forbidden.

**Dependencies:** E04.2 canonical decisions, exact merge and conclusive recovery.

**Evidence:** Planned evidence only, not executed tests: Full/direct A04,A05,A17,A18,A29,A34; supporting A09,A28,A36; real GitLab direct-write/merge matrix for every non-privileged actor and channel, privileged-Owner unexpected-history detection/incident/quarantine evidence, prompt-injection cases, target-race/lock-handover/fencing faults, crash-after-call recovery, full tuple assertions and trusted server-code privilege inventory. Mocks may test local state machines only and cannot close GitLab enforcement checks.

**Rollback/upgrade impact:** rollback preserves protected rules, freezes affected targets and revokes exposed credentials without opening a direct-merge fallback. Recovery state and unresolved quarantine survive application rollback and schema rebuild; any `kb_ops` migration is owner-only, externally executed and rehearsed, with no production action authorized here.

<!-- End story repeat -->

### Story 4.4 (T07): Exact business review and independent decisions

As a business approver without a GitLab account,
I want a complete exact-diff review and safe accept/reject/cancel/edit actions in the platform,
So that I can make an informed independent decision without Git, CLI or hidden machine-significant changes.

Requirements: R01,R05,R06,R07,R08,R09,R10; I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I12,I13,I14; UX-DR1, UX-DR9, UX-DR14, UX-DR17, UX-DR18, UX-DR19, UX-DR20, UX-DR21, UX-DR22, UX-DR23, UX-DR24, UX-DR25, UX-DR26, UX-DR27, UX-DR28, UX-DR29; A01,A06,A07,A22,A23,A26,A27,A30,A36; CF-03, CF-10, CF-20, CF-21.
Acceptance ownership: Full/direct — A06,A07,A22,A23,A27,A30; Supporting — A01,A26,A36.

**Acceptance Criteria:**

**Given** a pending proposal and an authorized group-assigned review queue,
**When** the approver opens it in the platform,
**Then** the UI presents exact `base_sha`/`proposal_sha`, affected files and structure, before/after content and supported formatting, rationale/evidence/provenance, and author, version-author, requester and optional run attribution.
**And** the diff separately exposes front matter, ownership/origin equality, `valid_until`, tree moves, stable-ID link target changes, archive date/reason/replacement/descendant effects, media warnings and attachment additions/removals/revisions with the full immutable `{object_id,version,sha256,size,media_type,source_ref}` tuple, including swapped UUID or hidden metadata fixtures.

**Given** an authenticated browser session with a current path-scoped approval role,
**When** the approver accepts, rejects, cancels, comments or edits the exact ProposalVersion,
**Then** CSRF/Origin-protected commands produce the corresponding durable GO/MR state and accept/reject/cancel produce canonical DecisionRecord note+tag evidence without offering direct human merge.
**And** edit creates a new ProposalVersion and version author and invalidates old approval, stale commands return a version mismatch, and server-side self-approval denial covers author, requester and version editor even if the UI is bypassed.

**Given** a proposal containing active content or an incomplete diff/preview,
**When** the platform cannot faithfully render any content, metadata, structure, link or attachment change,
**Then** it marks preview unreliable and blocks apply/merge until the exact proposal can be reviewed completely.
**And** XSS, executable HTML/MDX and hidden text are rejected before browser exposure, no partial preview is treated as approval, and keyboard/screen-reader users receive equivalent diff, focus, labels and action feedback without protected-content leakage.

**Given** double clicks, reloads, concurrent commands or a stale review page,
**When** the browser retries a decision or the proposal changes,
**Then** the same `decision_id` and exact payload return the existing outcome without a duplicate note, tag or merge attempt, while changed payloads and old SHAs are rejected safely.
**And** pending queues retain bounded pagination and longest-prefix group assignment across reload, policy mismatch, lost path role or revocation blocks apply with zero `main` writes, and all errors use `{code,message,request_id,retryable}`; `LIMIT_EXCEEDED` returns effective bounds and a valid next cursor when more authorized items exist.

**Given** a verified merge, timeout, recovery barrier or concurrent edit,
**When** the UI displays review lifecycle and operation status,
**Then** it distinguishes `draft`, `in_review`, `published`, `archived`, `conflicted`, `recovery_required` and quarantine using canonical Git/MR/GO evidence.
**And** timeout never appears as success or proven absence of merge, `published` waits for verified GO merge, and this review story requires no retrieval index, active pointer or cutover preflight from E05/E06; indexed and non-serving preflight states are owned by their pipeline/cutover views rather than inferred by review.
**And** `STALE_BASE` appears as «Документ изменился» with the difference and a path to new work from the fresh revision, while `PROPOSAL_VERSION_MISMATCH` refreshes the review without replaying an old accept.

**Dependencies:** E04.2 canonical ProposalRecord/DecisionRecord and merge proof only; no index, retrieval, preflight or cutover story is a prerequisite.

**Evidence:** Planned evidence only, not executed tests: A01,A06,A07,A22,A23,A26,A27,A30,A36; two-user business review without GitLab, full machine-significant diff and attachment-tuple fixtures, archive diff fixtures, unreadable-preview merge denial, self-approval matrix, browser CSRF/XSS/accessibility checks, decision replay, readable conflict views and lifecycle/recovery views. Existing design and headless editor evidence are not UI acceptance.

**Rollback/upgrade impact:** rollback disables managed review mutations and leaves a read-only, explicitly unavailable review state rather than sending business users to direct GitLab merge. Existing MRs, decisions and barriers remain canonical or rebuildable from exact revisions; frontend/seam upgrades require browser regression and rollback records, with no client-specific branch or production resource created by this story.

<!-- End story repeat -->

### Story 4.5 (T08): Scoped working context and canonical direct-read agent tools

As a business user working with the agent,
I want page, subtree and Space-scoped navigation and bounded canonical direct reads in the same interface,
So that the agent receives only authorized, exact and explicitly bounded context with trustworthy citations.

Requirements: R01,R02,R03,R05,R16; I06,I08,I09,I11,I12,I13,I14; UX-DR1, UX-DR2, UX-DR3, UX-DR4, UX-DR5, UX-DR10, UX-DR15, UX-DR19, UX-DR29, UX-DR32, UX-DR33; A01,A02,A21,A22,A25,A32; CF-01, CF-09, CF-19, CF-28.
Acceptance ownership: Full/direct — A01; Supporting — A02,A21,A22,A25,A32.

**Acceptance Criteria:**

**Given** the managed navigator, editor and sidebar chat with a server-issued AuthzContext,
**When** the user selects a page, subtree, Space or allowed Spaces,
**Then** the effective tool scope is the intersection of that selection and current server permissions, the selection carries stable page ID plus exact SHA and visible full/partial context limits, and model arguments can only narrow it.
**And** the user can move through tree, editor, agent, diff and review without CLI or another business application, while personal chat privacy and ordinary chat behavior remain unchanged.

**Given** typed `list_documents` and `read_document` calls,
**When** the agent lists or reads a whole canonical document or section,
**Then** results are bounded and authorized before model/browser payload, all content is read directly through GO at an exact revision rather than through an index candidate, and citations include Space, stable document ID, full revision and section/range.
**And** repeated headings remain unambiguous, long reads return explicit bounds and cursor with `truncated=false` equivalent to no reason and no next cursor, and no silent text loss occurs; search and stale-index handling are outside this canonical direct-read story.

**Given** links and immutable attachment references in an authorized document,
**When** the agent requests linked canonical documents or files,
**Then** every title, link target, history item and attachment is reauthorized before exposure and the full immutable `{object_id,version,sha256,size,media_type,source_ref}` tuple is preserved.
**And** cross-Space, unauthorized historical or attachment requests return safe anti-enumeration errors with no payload, and a citation or signed delivery reference never becomes an ACL bypass.

**Given** direct-read pagination or a long-running canonical read/stream,
**When** a document snapshot, policy/group/revocation or actor epoch binding changes or disappears,
**Then** the cursor becomes explicitly stale, no binding is borrowed from another Space, further payloads stop and live subscriptions close on revocation.
**And** GitLab-outage stale mode remains disabled, any explicitly requested historical canonical read is separately marked and authorized, and a new current canonical read returns a distinct exact revision rather than an index fallback.

**Given** malformed, oversized or explicitly bounded direct-read arguments,
**When** the tool returns an error,
**Then** it uses `{code,message,request_id,retryable}` with sanitized details, and `LIMIT_EXCEEDED` includes effective bounds and a valid continuation cursor when additional authorized canonical content exists.
**And** model-supplied actor, tenant, group, policy or run fields cannot replace the trusted execution context.

**Dependencies:** E04.4 review experience plus E02.1 canonical reads and E02.3 per-Space authorization.

**Evidence:** Planned evidence only, not executed tests: A01,A02,A21,A22,A25,A32; page/subtree/Space scope matrices, exact-SHA canonical direct reads, repeated-heading/cursor/truncation vectors, full attachment tuples, direct-read cursor binding and revocation-during-stream checks on the real application pipeline.

**Rollback/upgrade impact:** rollback disables agent context/tool exposure while preserving authorized direct UI reads and personal chats; it does not enable index retrieval or broader cached grants. Tool/schema changes remain versioned and backward-compatibility checked, with no direct database access, client code branch or production corpus introduced.

<!-- End story repeat -->

### Story 4.6 (T09): Restricted single-page agent proposal tools

As a business user requesting agent assistance,
I want the agent to create only reviewable single-page body proposals from trusted context,
So that automation can help author content without gaining publication, privilege or arbitrary execution capabilities.

Requirements: R03,R05,R06,R07,R10,R16; I01,I02,I03,I04,I06,I08,I09,I11,I12; UX-DR15, UX-DR16, UX-DR17, UX-DR23, UX-DR25, UX-DR29, UX-DR32, UX-DR33; A02,A04,A05,A17,A18,A21,A30; CF-07, CF-09, CF-19, CF-20.
Acceptance ownership: Full/direct — A02,A21; Supporting — A04,A05,A17,A18,A30.

**Acceptance Criteria:**

**Given** a trusted server-created run with requester, actor type, AuthzContext and optional `run_id`,
**When** the agent proposes a curated new page or edits an existing page,
**Then** the only supported mutations are single-page body create and `AgentAnchoredPatchChange` with a required body section, exact `base_sha`, rationale/evidence and matching idempotency metadata.
**And** GO creates the branch, MR and ProposalRecord with trusted principals and source revisions, `main` remains unchanged, a read-only user cannot propose, and an identical retry returns the existing proposal without another branch or MR.

**Given** a request for bulk or subtree changes, attachments, whole-document replacement, front matter, links, origin, `valid_until`, archive or `access`,
**When** it arrives through a native/direct/deferred/note/temporary chat, automation, channel, OpenAPI or `call_tool`,
**Then** both the execution adapter and GO reject it with zero canonical writes, including attempts to call human `editProposalVersion`, accept/reject/cancel/merge, grants or source-managed auto-merge.
**And** arbitrary Git, shell/terminal, Python, SQL, filesystem and Tool Creation remain unavailable at tool, service and GitLab credential layers rather than merely absent from the model schema.

**Given** malicious document text, rationale, evidence or tool output instructing the model to ignore approval or change identity and policy,
**When** the agent plans or invokes tools,
**Then** that content is treated only as untrusted data and cannot alter actor, requester, run, groups, tenant, Space, scope, tools, provider, policy, active pointer or merge credentials.
**And** prompt-injection tests across every registration/channel produce no forbidden proposal diff, disclosure or publication, while ordinary authorized single-page proposals still succeed.

**Given** malformed or oversized arguments, unknown fields, a missing patch section, ambiguous anchors, mismatched path/body IDs or a reused key with another payload,
**When** the proposal command is validated,
**Then** typed validation returns a sanitized error before side effects and creates no branch, MR, cursor or grant change.
**And** stale base or `PATCH_AMBIGUOUS` requires a new proposal from fresh HEAD, apply never invokes the LLM to regenerate content, and timeout never triggers a blind mutation with a new idempotency key.

**Given** an agent-created proposal awaiting review,
**When** the run ends, access is revoked or a human later edits the version,
**Then** the agent retains no standing merge, approval or grant capability, live payloads stop on revocation, and any new ProposalVersion requires fresh independent review.
**And** model/tool logs preserve request/run/proposal correlation and exact SHAs while redacting prompts, document bodies, evidence text, private queries, provider payloads and secrets.

**Dependencies:** E04.3 all-channel enforcement and E04.5 scoped canonical direct-read context.

**Evidence:** Planned evidence only, not executed tests: Full/direct A02,A21; supporting A04,A05,A17,A18,A30; end-to-end canonical-read/propose trace, allowed body create/anchored patch positives, every forbidden-diff and channel negative, trusted-principal/run correlation, prompt-injection suite, stale/ambiguous/idempotency cases and sanitized tool logs. No agent auto-merge or mocked GitLab result is acceptable as integration proof.

**Rollback/upgrade impact:** rollback disables proposal tools and revokes proposal-only agent credentials while retaining read-only canonical access where still authorized; existing branches/MRs require human review and no direct-write fallback is enabled. `agent-tools-v2` changes require contract compatibility and all-channel regression evidence, not a new privileged route.

<!-- End story repeat -->

### Story 4.7 (T07b): DocOps review projections, correction tasks and UX telemetry

As a business approver and knowledge operations owner,
I want revision-bound DocOps queues, actionable error-correction tasks and sanitized UX evidence,
So that published content remains current and review UX failures stay visible without changing canonical content outside the governed MR flow.

Requirements: R01,R05,R06,R07,R08,R09,R10; I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I12,I13,I14; UX-DR30, UX-DR33; A01,A07,A22,A26,A27,A36; CF-06, CF-10, CF-20.
Acceptance ownership: Full/direct — не назначены; Supporting — A01,A07,A22,A26,A27,A36. Correction-task scope ограничен только новым `docops-correction-task-v1` contract; новые A IDs не создаются.

**Acceptance Criteria:**

**Given** `valid_until` on an exact published document revision and an authorized DocOps queue,
**When** the date is future or due, a correction MR opens or resolves, or a reviewed revision removes the date,
**Then** the revision-bound projection transitions explicitly through `scheduled`, `due`, `in_review`, `resolved` and `removed` as applicable, emits only authorized queue/events, and removal yields `review_required=false,valid_until=null` without automatic archive or new access.

**Given** an authorized user reports an error on an exact document revision,
**When** the «нашёл ошибку» action creates a correction request,
**Then** GO creates a `docops-correction-task-v1` through the contracted create endpoint with server-derived requester and policy-derived owner, exact `document_revision_sha`, `evidence_sha256` and optional `linked_mr`; initial state is `open`, or `in_review` when a valid linked MR is already durable. Identical replay returns the same task, and key reuse with another actor, route, concrete path or payload creates zero writes.
**And** get/resolve/cancel enforce per-Space authorization, monotonic `task_version` and the `open/in_review/resolved/cancelled` state machine. A content correction becomes `resolved` only after the normal ProposalRecord/MR/human-decision/GO-merge evidence; no-MR resolution requires reason and evidence hash. Neither the task nor expiry directly edits, publishes or archives canonical content; queue visibility and events remain authorized without exposing another Space's metadata. Correction-task scope exists only through [the correction schema](../../specs/corporate-kb/contracts/docops-correction-task.schema.json) and [API contract](../../specs/corporate-kb/contracts/docops-correction-api.md), with no second task store, canonical status or DecisionRecord.

**Given** tree/read, truncation, draft/proposal and review activity,
**When** UX telemetry is emitted,
**Then** sanitized metrics and correlation cover tree/read latency and failures, explicit truncation, draft and proposal results, review `base_sha`/`proposal_sha` mismatch/conflict, preview reliability and UI retry/idempotency outcomes without raw private content.
**And** unreliable preview and repeated SHA mismatch are visible merge blockers, not merely debug log messages.

**Dependencies:** E04.4 review UI core and its E04.2 canonical proposal/decision/merge prerequisites; `docops-correction-task-v1` schema/API/OpenAPI contract is the only correction-task contract; no index, retrieval, preflight, cutover or later story is a prerequisite.

**Evidence:** Planned evidence only, not executed tests: Supporting A01,A07,A22,A26,A27,A36; exact-revision DocOps projection and `scheduled/due/in_review/resolved/removed` transitions, authorized queue/events, removed-date invariant, `docops-correction-task-v1` create/get/resolve/cancel lifecycle, exact revision/stable actor/policy owner/evidence hash/task-version/idempotency negatives, optional linked-MR governed outcome, no-MR reason+evidence resolution, kb_ops backup/restore/reconciliation and sanitized UX observability with correlation and no raw private content. Existing design and headless editor evidence are not UI acceptance.

**Rollback/upgrade impact:** rollback disables new DocOps task mutations and projection processing while preserving exact canonical `valid_until` revisions, rebuildable queue metadata and durable GO-owned correction-task current projections, append-only events, evidence payloads and idempotency records in `kb_ops`; existing correction MRs and decisions remain governed by E04.4. Git/MR rebuild alone cannot recreate correction tasks or their evidence and must not fabricate or silently discard them. Telemetry rollback never weakens privacy controls or changes lifecycle truth, and frontend/seam upgrades require browser regression and rollback records with no client-specific branch or production resource created by this story.

<!-- End story repeat -->

## Epic 5: Published knowledge pipeline

CI index из published `main`, ancestry/SHA/ACL guards, scoped exact/semantic retrieval и пересобираемые projections.

### Story 5.1 (T10a): Exact-SHA CI index build and validated preflight artifact

As a retrieval platform engineer,
I want deterministic full and incremental index artifacts built from exact canonical revisions,
So that retrieval and cutover can consume one validated, rebuildable projection without a second index engine.

Requirements: R02,R04,R11,R18; I01,I02,I08,I09,I10,I11,I12,I14; UX-DR6, UX-DR14, UX-DR19, UX-DR20, UX-DR26, UX-DR27, UX-DR31, UX-DR33; A03,A12,A22,A31,A35; CF-11, CF-22, CF-24, CF-27.
Acceptance ownership: Full/direct — A12,A22,A35; Supporting — A03,A31.

**Acceptance Criteria:**

**Given** an authenticated GitLab event or periodic HEAD reconciliation for an activated Space,
**When** GO requests indexing,
**Then** CI resolves and reads the exact verified published `main` SHA through a read-only credential, treats webhook payloads only as hints, and builds an inactive run for the immutable Space/repository/SHA/profile input.
**And** only eligible canonical content enters the projection; pending/rejected branches, `inbox`, templates, service files, archived/deleted pages and unverified critical/handwritten media are excluded.

**Given** a versioned cutover preflight request containing an exact frozen `cutover_sha`,
**When** CI builds the requested artifact,
**Then** it produces a full inactive preflight request/run/snapshot with `snapshot_sha=cutover_sha` and `serving_allowed=false`, records validation evidence and never activates the artifact, enables user access or serves retrieval.
**And** this story owns the preflight/index artifact contract only; an external cutover coordinator may consume it without becoming a dependency of the CI/index engine.

**Given** documents with stable links, shared inputs, policy dependencies and immutable attachment revisions,
**When** CI plans a full or incremental build,
**Then** `index-snapshot-v1` records snapshot and document revision SHAs separately, content/dependency hashes, Git ancestry `main_generation`, independent `index_profile_version` and the per-Space policy triple without lexicographic SHA ordering.
**And** an incremental run becomes ready only with complete dependency closure, empty `missing_inputs`, matching perimeter/generation/profile/policy and nonempty evidence of an independently validated full run and snapshot on the same `main_sha`; requested, failed, empty or mismatched prerequisites force closure expansion/full rebuild and no ready claim.

**Given** a completed full or equivalent incremental build,
**When** build validation runs,
**Then** both exact and semantic projections have non-null ready hashes, stable section/citation metadata, immutable attachment/media verification and negative ACL results before any publication request.
**And** validation records tree/read coverage, explicit truncation behavior and dependency/closure metrics without raw private content; partial or failed artifacts never serve.

**Given** lost, duplicate or out-of-order webhooks, CI outage, provider failure or complete `kb_index` loss,
**When** retry, dead-letter, reconciliation or rebuild executes,
**Then** bounded idempotent processing and periodic HEAD/ancestry reconciliation detect missing runs without changing canonical Git history, and a full rebuild from Git plus immutable assets creates a newly validated inactive artifact.
**And** CI has no direct Git write or merge capability for documents or `INDEX.md`, canonical merges are not rolled back by indexing failures, and only the later publication lifecycle can make a validated non-preflight artifact active.

**Dependencies:** E03.1 exact revision/save behavior and E02.3 per-Space authorization; no migration/cutover story is a dependency.

**Evidence:** Planned evidence only, not executed tests: A03,A12,A22,A31,A35; real GitLab/PostgreSQL/CI exact-SHA builds, full/incremental equivalence and dependency cases, validated inactive preflight artifact, late-job/webhook/CI-failure injection, ACL/archive/pending/media exclusions and clean full rebuild. T00's 22/22 synthetic retrieval gates remain baseline candidate evidence, not product acceptance or production model approval.

**Rollback/upgrade impact:** failed builds remain inactive and never rewind canonical Git or activate a preflight/partial artifact. Profile changes use shadow builds without destructive live rebuild, and `kb_index` schema changes use only the owning external migrator with no production migration authorized by this story.

<!-- End story repeat -->

### Story 5.2 (T10b): Published retrieval, search cursors and monotonic publication lifecycle

As a business reader and retrieval platform engineer,
I want exact and semantic search served only from a validated active snapshot of published `main`,
So that answers and citations never expose pending, stale, revoked or unverified content and late jobs cannot roll back knowledge.

Requirements: R03,R04,R05,R11,R16,R18; I01,I02,I06,I08,I09,I10,I11,I12,I13,I14; UX-DR4, UX-DR6, UX-DR10, UX-DR15, UX-DR19, UX-DR20, UX-DR26, UX-DR27, UX-DR29, UX-DR31, UX-DR32, UX-DR33; A02,A03,A11,A21,A22,A25,A31,A32,A35; CF-01, CF-11, CF-12, CF-13, CF-19, CF-24.
Acceptance ownership: Full/direct — A02,A03,A11,A21,A22,A25,A32,A35; Supporting — A31.

**Acceptance Criteria:**

**Given** a conclusive validated inactive preflight artifact from E05.1,
**When** the published lifecycle is requested,
**Then** a separate published request/run/snapshot receives new IDs but retains the same exact SHA, dependency closure, policy triple and exact/semantic hashes, and repeats full validation as non-preflight before becoming eligible for the active pointer.
**And** the preflight always retains `serving_allowed=false`, never answers search and is never itself activated; this lifecycle publishes index state only and does not activate the Space or user access.

**Given** concurrent old and new generation or profile publishers for one `(space_id,profile_id)`,
**When** the single CI/index writer publishes a validated run,
**Then** one fence/CAS register across all generations checks expected current pointer/fence, latest Git ancestry and exact ready run/snapshot in one transaction, and a stale owner updates zero pointer rows.
**And** a late successful job is marked superseded and never rolls back active search, only a published non-preflight descriptor can become active, and GO, UI, retrieval, connectors and webhook payloads cannot write the pointer.

**Given** typed `search_documents` requests over one or more allowed Spaces,
**When** exact or semantic retrieval executes,
**Then** search performs per-Space fan-out only over active published snapshots, intersects requested scope with fresh server permissions, reauthorizes every candidate and payload, and returns citations with Space, stable document ID, full revision and section/range.
**And** pending/rejected/inactive snapshots, archive/delete, unverified media and cross-Space mismatches return no title, snippet, chunk or file, while canonical current/historical direct reads remain separate exact-SHA GO operations.

**Given** multi-Space search pagination, a stale candidate or a changed index profile,
**When** a cursor is created or continued,
**Then** it binds the query/scope and complete ordered per-Space snapshot, index profile, policy/group/revocation and actor-epoch set; any replaced, missing or stale binding stops further payloads with an explicit stale error.
**And** a stale index candidate is rejected rather than replaced silently with historical content, revocation does not wait for reindex and closes live streams/subscriptions, and no cursor borrows another Space binding.

**Given** an activated Space without a validated active snapshot, an inactive preflight, a bounded result page or an upstream retrieval failure,
**When** UI or agent tools receive the outcome,
**Then** they distinguish `published` from later `indexed`, expose inactive preflight and `INDEX_NOT_READY` explicitly, and return unified `{code,message,request_id,retryable}` errors without optimistic success.
**And** `LIMIT_EXCEEDED` includes effective bounds and a valid next cursor whenever more authorized results exist, truncation is never silent, and retrieval remains read-only with no stale GitLab-outage mode.

**Dependencies:** E05.1 validated index/preflight artifacts and its E02.3 authorization context.

**Evidence:** Planned evidence only, not executed tests: A02,A03,A11,A21,A22,A25,A31,A32,A35; preflight/published pair, concurrent pointer CAS/fencing, exact/semantic per-Space retrieval and citations, stale/profile/cursor rejection, ACL/revocation/archive/pending exclusions, `LIMIT_EXCEEDED` continuation and real read-only retrieval results. T00 synthetic gates are not product acceptance.

**Rollback/upgrade impact:** rollback switches only to a previously validated compatible published snapshot or leaves retrieval unavailable; it never rewinds canonical Git, activates a preflight/partial build or enables user access. Profile changes use shadow builds and controlled pointer CAS, and `kb_index` schema changes use only the owning external migrator.

<!-- End story repeat -->

## Epic 6: Migration & portability

Dry-run и controlled unpublished bulk, exact-SHA cutover/preflight/activation, post-cutover MR-only imports, clone+decisions/assets manifests, mirror/metadata backup и restore.

### Story 6.1 (T12a): Deterministic dry-run import and admission gates

As a source owner or engineering import operator,
I want a reproducible dry-run manifest with explicit provenance, losses and security/data/media blockers,
So that no source content reaches canonical Git, preview or indexing before its exact mapping and admission evidence are approved.

Requirements: R02,R12,R13,R15,R16,R18; I01,I02,I03,I08,I09,I12,I13,I14; UX-DR10, UX-DR19, UX-DR20, UX-DR22, UX-DR30, UX-DR31, UX-DR34; A13,A16,A22,A23; CF-04, CF-05, CF-06, CF-08, CF-14, CF-19, CF-26, CF-28.
Acceptance ownership: Full/direct — A13,A23; Supporting — A16,A22.

**Acceptance Criteria:**

**Given** an immutable synthetic source snapshot, versioned mapping configuration and an agreed repository=Space perimeter,
**When** dry-run analyzes nested documents,
**Then** it deterministically returns path→stable-ID mapping, tree, provenance, source versions/hashes, relative links/anchors, attachment manifests, ownership mapping, original/extracted hashes and explicit losses/errors with `canonical_writes=false`.
**And** the same source/config replay reproduces the manifest, changed inputs create a new manifest rather than mutating old evidence, and no branch, MR, `main` commit, active index entry or `merged` source cursor is created.

**Given** source files with owners, selected `strict` or `pii_permitted` data profile and media metadata,
**When** intake, security, PII and media gates execute before corpus or preview admission,
**Then** a stable source owner and completed data barrier are mandatory, every PII hit has a human disposition, and critical/handwritten media lacks admission until required human transcription/verification exists.
**And** traversal, absolute/ambiguous paths, symlinks, executable HTML/MDX, `.git`/`.env`/secret-like content, invalid UTF-8, oversized/decompression-bomb inputs and mutable/unhashed attachments are rejected, unresolved blockers stay quarantined, and `pii_permitted` never uses external PII egress or an unplanned extraction/OCR fallback.

**Given** Cyrillic paths, source IDs, policy mappings, attachments and `valid_until` in the dry-run input,
**When** the manifest is validated,
**Then** repository-relative document paths use NFC, NFC/NFD/trailing-separator ambiguity is rejected, source ID `DOC-0001` is preserved exactly, policy absolute↔relative mappings remain lossless, and every attachment has the full immutable `{object_id,version,sha256,size,media_type,source_ref}` tuple.
**And** `valid_until` remains bound to the exact proposed document revision with no authorization or automatic-archive effect, and dry-run reports the future DocOps scheduled/due review inputs without creating a queue event or canonical metadata write.

**Given** a dry-run containing errors, unsupported ownership mappings or incomplete blockers,
**When** an operator requests handoff to controlled import,
**Then** the manifest is not marked validated, the handoff is denied with `{code,message,request_id,retryable}`, and no unpublished bulk write is authorized by the dry-run itself.
**And** only a validated manifest with resolved blockers, approved repository perimeter and separate import authorization can become an input to cutover/activation.

**Dependencies:** E02.3 authorization and E03.1 exact revisions; no CI/index, T05 merge lifecycle or cutover completion is required for this separate T12a dry-run work, which may run in parallel with T05/T10 and never authorizes full T12/T12b or canonical writes.

**Evidence:** Planned evidence only, not executed tests: A13,A16,A22,A23; deterministic dry-run/hash manifests, exact source IDs and Unicode/path vectors, full attachment tuples, DocOps review inputs, malicious/security/PII/media negatives and zero-write assertions. Only synthetic or separately authorized sanitized inputs are admissible.

**Rollback/upgrade impact:** dry-run outputs remain noncanonical and disposable with their evidence retained; rollback cannot create or clean a corpus. Import/config changes remain reusable core configuration, not client code branches, and no production migration, corpus, credential or external call is authorized here.

<!-- End story repeat -->

### Story 6.2 (T12b): Controlled cutover and activation using the E05 preflight artifact

As an engineering migration operator,
I want an exact signed corpus snapshot activated through freeze, protection, non-serving preflight and published pointer checks,
So that only the approved revision becomes accessible and every later change follows GO/MR review.

Requirements: R04,R05,R06,R09,R11,R12,R13,R18; I01,I02,I06,I08,I09,I10,I11,I12,I13,I14; UX-DR26, UX-DR27, UX-DR29, UX-DR31, UX-DR33, UX-DR34; A13,A31,A35,A36; CF-08, CF-11, CF-12, CF-13, CF-22, CF-24.
Acceptance ownership: Full/direct — A13,A31,A35; Supporting — A36.

**Acceptance Criteria:**

**Given** a validated E06.1 dry-run with resolved blockers and separate import authorization,
**When** controlled pre-cutover bulk is permitted,
**Then** engineering writes only to unpublished `main` while user access and published index are absent, different ACLs remain in different repositories, and expert validation plus CutoverRecord bind evidence, sign-off stable identity, UTC timestamp and exact `cutover_sha`.
**And** no per-page MR exception is claimed after cutover, production corpus is not inferred or created by this story, and an unpublished bulk package cannot self-activate users, search or source cursors.

**Given** an expert-signed CutoverRecord and an inactive Space,
**When** cutover executes,
**Then** write freeze is enabled first, GO requires `HEAD == cutover_sha`, protected validation/cutover tags and MR-only/merge-only-GO rules are established with negative direct-push/settle proof, and only then the coordinator requests the E05.1 full inactive preflight artifact on that exact SHA.
**And** the coordinator verifies `snapshot_sha=cutover_sha`, conclusive validation and `serving_allowed=false`; it does not build a second index, treat preflight as published or enable retrieval/user access.

**Given** a conclusive non-serving preflight artifact,
**When** publication and activation are coordinated,
**Then** E05.2 creates and fully validates the separate published request/run/snapshot with new IDs but the same SHA/closure/policy/hashes, and its single writer performs per-Space/profile fence/CAS pointer publication.
**And** GO observes the validated published pointer before activating Space/user access, the pointer-to-activation order is never reversed, and preflight remains inactive and non-serving throughout.

**Given** HEAD drift after sign-off/freeze, a freeze/protection failure, incomplete preflight/published validation or interrupted cutover,
**When** the coordinator detects the condition,
**Then** activation stops with no user access, replay is allowed only for the same Space+SHA while freeze and HEAD remain unchanged, and drift requires a new CutoverRecord/sign-off/preflight.
**And** inactive preflight, `INDEX_NOT_READY`, `published` and later `indexed` states remain explicit with `{code,message,request_id,retryable}` errors, and a requested/failed/empty artifact is never an activation prerequisite.

**Given** a protected or activated Space,
**When** repeated imports, engineering fixes or source updates occur,
**Then** every change uses GO/MR/human DecisionRecord/GO merge without history rewrite, direct push, auto-merge or a return to bulk bypass.
**And** idempotent resume creates no duplicate tags, requests, runs, pointers or activations, and curated changes are not overwritten.

**Dependencies:** E06.1 validated dry-run, E04.2/T05 GO/MR DecisionRecord merge lifecycle, and E05.2/T10 published lifecycle consuming E05.1 preflight/index artifacts; together with E02/E03 this makes full T12/T12b dependent on T03,T04,T05 and the T10 artifact. This is a one-way E05 → E06 artifact dependency with no E05 dependency on cutover and no parallel full-T12/T05 claim.

**Evidence:** Planned evidence only, not executed tests: Full/direct A13,A31,A35; supporting A36; unpublished-only bulk authorization, exact CutoverRecord/sign-off, freeze/HEAD-drift/protection-settle tests, consumed inactive preflight artifact, separate published pair, pointer-before-activation and post-cutover MR/no-bypass/replay results. Only synthetic or separately authorized sanitized inputs are admissible.

**Rollback/upgrade impact:** before activation, rollback leaves the Space inactive and frozen with sanitized failure evidence; after protection, content fixes require reviewed MR, and after activation they require revert-MR with no history rewrite or destructive corpus cleanup. No production migration, corpus, credential or external call is authorized here.

<!-- End story repeat -->

### Story 6.3 (T13a): Complete portable export with exact refs and closure

As a portability operator,
I want a complete authorized Git clone with decisions/assets manifests, exact refs and verified dependency closure,
So that documents, proposals, decisions, policies and immutable assets are portable without fabricated evidence, hidden omissions or secrets.

Requirements: R02,R05,R09,R10,R14,R18; I05,I06,I07,I09,I10,I11,I12,I13,I14; UX-DR4, UX-DR10, UX-DR13, UX-DR19, UX-DR26, UX-DR27, UX-DR29, UX-DR30, UX-DR32, UX-DR33; A11,A15,A25,A27,A28,A32,A36; CF-06, CF-14, CF-15, CF-16, CF-17, CF-22, CF-25.
Acceptance ownership: Full/direct — A11,A25,A27,A32,A36; Supporting — A15,A28. Primary crash-recovery/A28 acceptance принадлежит E04.2.

**Acceptance Criteria:**

**Given** fresh permission to a Space and its entire history,
**When** an export is created,
**Then** `export-manifest-v2` accompanies a Git clone with explicit full object SHAs and refs, peeled annotated-tag targets and raw object hashes, document IDs/tree/links/origin/revisions/content hashes, required `valid_until`, policy bundle/revisions and explicit grants mapping.
**And** each export batch is freshly authorized with policy/revocation recheck, cross-Space history and client data are denied, and secrets, private chats and unapproved payloads are excluded rather than redacted into an allegedly complete ordinary export.

**Given** accepted, rejected and cancelled proposals in different recorded, in-flight, failed, conflicted, invalid and merged states,
**When** the decisions manifest is generated,
**Then** it preserves canonical DecisionRecord JSON/hash, MR note IDs, protected `kb-decisions/<uuid>` tags, supersedes links, explicit outcomes, real attempts and recovery evidence without replacing note+tag anchors.
**And** accepted-before-merge and rejected/cancelled records have no fabricated merge or synthetic attempt, only verified merged outcomes include ancestry/parents/trailers/note+tag proof, and mismatch or unknown outcome remains explicit instead of being normalized to success.

**Given** immutable attachment/source objects and their versioned bindings,
**When** the assets manifest and closure are validated,
**Then** every entry contains object/version/storage reference, SHA-256, size, media type, source reference and status, and complete/ready requires decisions, assets and authorization closure with empty `missing[]`.
**And** a missing, rejected, mutable or hash-mismatched object receives no fabricated hash, blocks any complete claim and identifies the affected dependency without exposing another Space or credential.

**Dependencies:** E04.2 GO/MR DecisionRecord lifecycle and E06.2 controlled cutover/activation with its E02/E03/E05 prerequisites.

**Evidence:** Planned evidence only, not executed tests: Full/direct A11,A25,A27,A32,A36; supporting A15,A28; clone+decisions+assets manifests with exact refs, explicit decision outcomes/recovery, per-batch authorization negatives, complete/ready closure, missing/rejected/hash-mismatched asset controls and real object-store ACL results. Existing LocalStack cross-bucket ACL failure remains a blocker for any affected PASS claim.

**Rollback/upgrade impact:** an incomplete or partially failed export remains explicitly non-ready and cannot be presented as portable closure; rollback does not hide missing objects, normalize unknown outcomes, write canonical Git or include secrets. Export format changes remain versioned and compatibility-checked, with no production export or external call authorized by this planning artifact.

<!-- End story repeat -->

### Story 6.4 (T13b): Mirror/metadata backup, rebuild and conservative clean restore

As a recovery operator,
I want mirror/metadata backups to rebuild managed projections on a clean isolated instance,
So that restore is proven by exact canonical, decision, asset and authorization closure with conservative recovery and negative controls rather than by dump existence.

Requirements: R02,R05,R09,R10,R11,R14,R18; I05,I06,I07,I09,I10,I11,I12,I13,I14; UX-DR4, UX-DR6, UX-DR10, UX-DR13, UX-DR19, UX-DR26, UX-DR27, UX-DR29, UX-DR30, UX-DR32, UX-DR33; A11,A15,A25,A27,A28,A32,A36; CF-06, CF-14, CF-15, CF-16, CF-17, CF-22, CF-25.
Acceptance ownership: Full/direct — A15,A32; Supporting — A11,A25,A27,A28,A36.

**Acceptance Criteria:**

**Given** the required backup perimeter,
**When** mirror and metadata backup runs,
**Then** it captures all Git refs and objects, protected decision/cutover tags, GitLab MR/note/audit metadata, immutable objects and nonsecret config under a separately controlled secrets backup/recovery policy.
**And** backup freshness, hashes and closure are observable, credentials never appear in manifests or logs, and a Space export is not represented as a complete platform backup for users, sessions, private chats, models or secrets.

**Given** GO-owned `docops-correction-task-v1` operational state from the existing E04.7 contract,
**When** the separate non-Git-derived correction backup runs,
**Then** it durably captures correction-task current projections, append-only events, restricted evidence and idempotency records with Space/repository perimeter, hashes and event-sequence metadata independently of the Git mirror/metadata package.
**And** this backup and its restore/reconciliation APIs never edit canonical content or create a second canonical write path; any content correction still requires the normal MR/human DecisionRecord/GO merge lifecycle.

**Given** a clean isolated restore target with no inherited active grants, pointer or operational rows,
**When** restore and rebuild execute,
**Then** `kb_authz` is rebuilt from exact Git policy plus fresh IdP data, Git-derived `kb_ops` projections are rebuilt under an external global bootstrap merge freeze from MRs/notes/tags/history/source registry with conservative per-target barriers, and `kb_index` is fully rebuilt from Git plus immutable assets and approved config.
**And** correction tasks are restored separately from their durable non-Git-derived backup, hashes/event sequences/perimeter are validated, and linked-MR reconciliation reconciles each task to the restored MR/DecisionRecord/GO merge evidence without fabricating, deleting, resolving or cancelling tasks; Git-only rebuild does not recreate or discard this lifecycle and no restore path writes canonical content directly.
**And** only conclusive reconciliation and fresh authorization reopen individual targets, a new validated index pointer precedes activation, and restored documents, links, attachments, policies, decisions, parents, trailers, notes, tags and hashes match the source package.

**Given** corrupted refs/decision anchors, missing assets or grants, a revoked export actor and cross-Space/client fixtures,
**When** negative restore controls run,
**Then** the package remains incomplete or the affected target quarantined, unknown merge outcomes are never cleared by an empty database, terminal label or restored pointer, and no unauthorized payload or cross-client binding is exposed.
**And** file/dump existence alone is not a restore PASS, and unavailable real object-store, IdP, GitLab or PostgreSQL checks remain BLOCKED rather than being replaced by mocks.

**Dependencies:** E06.3 complete export with exact refs/closure and E06.2 controlled cutover/activation; the existing E04.7 `docops-correction-task-v1` schema/API and durable non-Git-derived `kb_ops` correction backup/reconciliation contract are mandatory for correction restore. Correction content changes retain the E04.1/E04.2/E04.4 governed MR path and no second canonical write path.

**Evidence:** Planned evidence only, not executed tests: Full/direct A15,A32; supporting A11,A25,A27,A28,A36; mirror/all-refs and GitLab MR/note/audit metadata backup hashes; separate durable correction-task current/events/evidence/idempotency backup and restore, hash/event-sequence/perimeter checks and linked-MR reconciliation without fabrication/deletion/resolve/cancel or a second canonical write path; clean dedicated-instance restore, `kb_authz`/Git-derived `kb_ops`/`kb_index` rebuild evidence, conservative barriers, negative closure matrix and real object-store/IdP/GitLab/PostgreSQL results. Existing LocalStack cross-bucket ACL failure remains a blocker for any affected PASS claim.

**Rollback/upgrade impact:** restore remains isolated until all closure and safety checks pass; rollback never overwrites a live canonical repository, deletes unresolved barriers or enables direct merge. Correction-task operational state is preserved only through its separate durable backup and linked-MR reconciliation, never reconstructed or discarded through Git-only rebuild, and rollback does not open a canonical write path outside MR/human decision/GO merge. Secrets recovery follows its separate owner-approved procedure, and schema restoration/migration is performed only by each owning external migrator after compatible rehearsal, with no production restore authorized by this planning artifact.

<!-- End story repeat -->

## Epic 7: Internal pilot acceptance

Реальный корпус продаж, санкционированный inference, evaluation, hardening и pilot runbook.

### Story 7.1 (T11): Approved hoster.ai studio inference lifecycle

As a pilot user and AI platform operator,
I want all chat, tool and auxiliary inference to run through approved hoster.ai studio connections,
So that streaming and automation remain reliable, observable and inside the authorized data perimeter without hidden provider fallback.

Requirements: R15,R16,R18; I03,I04,I09,I12,I13; UX-DR15, UX-DR16, UX-DR20, UX-DR29, UX-DR31, UX-DR32, UX-DR33; A16,A18,A20; CF-30.
Acceptance ownership: Full/direct — A16; Supporting — A18,A20.

**Acceptance Criteria:**

**Given** an owner-approved hoster.ai studio endpoint, model inventory, credentials and egress policy,
**When** managed model connections are configured,
**Then** chat/answer, task/title/summarization, extraction, embeddings, reranking and OCR/vision routes each record approved connection/model/version, data profile, capabilities and required dimensions/index-profile linkage where applicable.
**And** every auxiliary route follows the same `strict` or `pii_permitted` perimeter, cold-start assets are inventoried, and absent real endpoint/configuration/credentials leaves the affected integration BLOCKED rather than passing with mocks or guessed model IDs.

**Given** the real approved streaming endpoint and bounded agent tools,
**When** sequential and parallel tool calls arrive as streamed partial arguments,
**Then** Open WebUI preserves trusted request/run correlation and citations, assembles arguments without executing partial content, and dispatches only after typed schema and current authorization validation.
**And** malformed JSON, unknown fields, unsupported operations, oversized payloads and prompt-injection instructions produce sanitized failures without shell/SQL/arbitrary execution, unauthorized model payload, merge or privilege expansion.

**Given** timeout, disconnect, 4xx/5xx, cancellation and retry scenarios on the real endpoint,
**When** a request fails or is cancelled,
**Then** bounded retry and cancellation behavior is observable, a mutation retry preserves the same idempotency identity and exact payload, and no duplicate proposal or merge results.
**And** no timeout or provider error silently selects another provider, model or perimeter; only an explicitly inventoried, owner-approved route in the same data profile could be selected by configuration, and otherwise the result is sanitized `UPSTREAM_UNAVAILABLE` or BLOCKED.

**Given** sensitive source content and provider credentials,
**When** inference, embedding, extraction or evaluation calls execute,
**Then** egress is limited to approved endpoints, `pii_permitted` content stays within the agreed hoster.ai/client perimeter, revocation closes live streams and stops new payloads, and offline startup uses only preapproved assets.
**And** prompts, raw documents/chunks/queries/rationale/evidence, provider payloads, tokens, signed URLs, bind secrets and PII snippets are absent from ordinary logs, traces, metrics and evidence.

**Given** cold and warm runs with a fixed corpus SHA, code/config/model/tool-schema versions and declared concurrency,
**When** lifecycle measurements are collected,
**Then** TTFT and full-response latency are reported separately with retry/cancel/malformed-call rates, route inventory and any fallback attempts, and inference, embedding, extraction, OCR/reranking and related resource costs are attributable to the run.
**And** measurements include configuration and failures rather than only token price or successful averages, and no unapproved latency, quality or budget threshold is invented as a result.

**Dependencies:** E04.6 bounded tools and trusted execution context; real hoster.ai inputs and separate approval for external/paid calls are mandatory for integration completion.

**Evidence:** Planned evidence only, not executed tests: Full/direct A16; supporting A18,A20; real endpoint streaming, sequential/parallel tools, malformed arguments, retries/cancel/timeouts/disconnects, revocation-during-stream, full provider inventory/no-fallback and egress/secrets checks, cold offline asset validation, and sanitized TTFT/full-response/cost records. If no approved endpoint exists, T11 evidence must say BLOCKED and no integration PASS is claimed.

**Rollback/upgrade impact:** rollback disables the affected managed model connection while preserving authorized canonical reads and never enabling an unplanned external provider. Credentials are rotated only through deployment secret procedures; model/dimension changes create a new validated index profile rather than mutating a live one, and no production endpoint, secret or paid call is created by this story.

<!-- End story repeat -->

### Story 7.2 (T14): Reproducible quality, safety and operational evaluation

As a product owner and independent QA evaluator,
I want an expert golden dataset and reproducible quality, safety and operational measurements against the actual application pipeline,
So that pilot acceptance is based on separate, reviewable evidence rather than unsupported model scores or UI smoke.

Requirements: R01,R03,R04,R05,R11,R15,R18; I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I11,I12,I13,I14 в явно выбранном regression scope; UX-DR2, UX-DR5, UX-DR6, UX-DR10, UX-DR15, UX-DR20, UX-DR29, UX-DR31, UX-DR33, UX-DR34; A03,A18,A20,A21 и применимые A01–A36 regression scope; CF-30.
Acceptance ownership: Full/direct — A03,A18,A20,A21; Supporting — применимые A01–A36 в выбранном regression scope без автоматического VERIFIED.

**Acceptance Criteria:**

**Given** an owner-reviewed expert Russian golden set, including representative sales questions and synthetic/sanitized negative cases,
**When** the evaluation adapter runs against the deployed application pipeline,
**Then** each case records corpus snapshot SHA, code/config/model/tool-schema versions, dataset version, scope and expected evidence, with approved/local grader configuration and the same data barrier as production-bound content.
**And** real client documents, secrets or unredacted personal data are not embedded in the repository, dataset, prompts or reports, and mocked application/hoster results are not accepted as real evaluation evidence.

**Given** direct-read, exact/semantic retrieval and answer-generation cases,
**When** quality is measured,
**Then** exact and semantic recall, factual support, citation correctness and abstention/no-answer behavior are reported separately for page/section reads, long/repeated-heading content and stale/private/conflict cases.
**And** citation revision and section are checked against canonical evidence, unsupported answers and silent stale substitution fail visibly, owner-approved quality thresholds are recorded before release claims, and an LLM judge is never the sole arbiter.

**Given** the deterministic adversarial and regression suites,
**When** merge/push boundaries, ACL isolation, prompt injection, schema ownership, concurrency and crash/recovery scenarios execute,
**Then** their results remain separate from probabilistic quality scores and require zero unauthorized disclosures in the agreed suite, no direct/auto-merge bypass and conclusive recovery behavior.
**And** personal Notes and ordinary chats pass feature-off/on privacy regression, failures are reproducible with explicit environment/commands, and missing real GitLab, IdP, PostgreSQL, CI or hoster checks remain BLOCKED.

**Given** fixed cold/warm workloads and declared corpus/profile/concurrency,
**When** operational measurements run,
**Then** the report separates TTFT/full response, Git read and merge latency, merge→index freshness and CI queue lag, and records retrieval/patch/conflict/restore outcomes plus inference, embeddings, extraction, storage, review, GitLab and operations cost drivers.
**And** online and CI resource contention, retries/dead-letter and failed runs are visible, and no p95/p99, freshness, capacity, RPO/RTO or budget target is claimed without an owner decision.

**Given** the full managed UX running on the actual application pipeline,
**When** observability evidence is evaluated,
**Then** sanitized reports separately cover tree/read latency and errors, explicit truncation and cursor continuation, durable draft and proposal outcomes, review `base_sha`/`proposal_sha` mismatch and conflict rates, preview reliability, and UI retry/idempotency behavior with request/run/proposal correlation.
**And** the report contains no raw document/chunk/query/rationale/evidence or provider payload, unreliable preview and SHA mismatch remain visible blockers, and UX acceptance is not inferred from the mere presence of metrics or screens.

**Given** a completed evaluation run,
**When** CI gates and reviewers inspect it,
**Then** machine output is retained in `_bmad-output/test-artifacts/t14`, sanitized review evidence is stored in `specs/corporate-kb/evidence/t14`, and failures link to reproducible cases, exact versions and result codes without raw private payloads.
**And** deterministic safety gates and required real integrations must pass independently before acceptance, quality regressions cannot be hidden by aggregate averages, and this story does not mark G2 or owner approval complete on their behalf.

**Dependencies:** E01.1 contract harness, E04.6 agent tools, E05.2 indexing/retrieval and E07.1 real approved inference.

**Evidence:** Planned evidence only, not executed tests: A03,A18,A20,A21 plus the applicable deterministic A01–A36 regression scope; expert golden dataset/rubrics, actual-pipeline quality and abstention reports, deterministic safety/concurrency/crash results, cold/warm operational/cost measurements, CI reproducibility and independent review. Existing design catalogs and T00 synthetic probes do not count as T14 execution.

**Rollback/upgrade impact:** rollback blocks the affected release/evaluation gate rather than weakening thresholds, deleting failing cases or substituting a mock. Dataset/config changes remain versioned and sanitized, model/index changes follow shadow validation, and no production corpus, external grader or paid evaluation call is authorized by this story.

<!-- End story repeat -->

### Story 7.3 (T18 necessary pilot part): Pilot hardening, protected deployment and operational acceptance

As a pilot operations owner,
I want a hardened protected pilot deployment with rehearsed runbooks and recovery evidence,
So that the internal pilot can be considered for G2 only after its operational, security and business acceptance is demonstrated.

Requirements: R01,R05,R14,R15,R17,R18; I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I11,I12,I13,I14 по operational-hardening scope; UX-DR1, UX-DR2, UX-DR9, UX-DR13, UX-DR23, UX-DR24, UX-DR25, UX-DR26, UX-DR27, UX-DR29, UX-DR30, UX-DR33, UX-DR34; A01,A06,A07,A08,A09,A10,A15,A20,A22,A23,A28,A33; CF-30.
Acceptance ownership: Full/direct — не назначены; Supporting — A01,A06,A07,A08,A09,A10,A15,A20,A22,A23,A28,A33. A19/second-client acceptance отсутствует и принадлежит только E08.4/E08.5.

**Acceptance Criteria:**

**Given** applicable P0 safety gates, a clean owner-authorized pilot environment and reusable pinned core artifacts,
**When** the protected pilot deployment is assembled,
**Then** repositories=Spaces, configuration/adapters, PostgreSQL/index/object storage, secrets, backups and egress are isolated, runtime workers have migrations disabled and non-DDL roles, and only owning external migrators perform rehearsed schema upgrades before traffic.
**And** proposal/merge, connector, CI/index and retrieval credentials remain separated, default egress is closed except approved routes, no client code branch is introduced, and no production resource or corpus is created without its separate authorization.

**Given** the operations design and actual pilot configuration,
**When** startup, cutover, merge recovery/quarantine, export, backup, restore, upgrade and rollback runbooks are rehearsed,
**Then** each records exact versions/refs, commands, sanitized outputs, failure handling, residual BLOCKED items and an independently reviewed result rather than citing `operations.md` as execution proof.
**And** alerts cover merge/lock/fencing/recovery age, decision mismatch, CI/HEAD drift, revocation, export closure and TTFT/full response without raw private content or secrets, and unresolved quarantine or incomplete closure prevents READY.

**Given** the pilot clone/manifests and mirror/metadata backup perimeter,
**When** a clean isolated backup/restore drill runs before G2,
**Then** decisions/assets/authorization closure is validated, `kb_authz` is freshly rebuilt, `kb_ops` starts under global merge freeze with conservative target barriers, and `kb_index` receives a new full validated pointer before activation.
**And** missing assets, cross-schema writes, unknown merge outcomes and unauthorized cross-Space/client reads fail the drill, owner-approved pilot RPO/RTO and retention values are recorded rather than guessed, and unknown targets remain closed after rebuild.

**Given** the protected deployment and adversarial operational fixtures,
**When** security and regression checks run,
**Then** direct push/merge/auto-merge by every non-privileged business, engineering, bot, connector, CI and source-managed identity remains denied, only each owning component writes its schema, no runtime DDL or cross-client resource access succeeds, and secret/log redaction canaries disclose nothing.
**And** personal Notes and ordinary chats preserve their behavior, offline/cold startup performs no unapproved download or provider fallback, branding/notices remain intact, and privileged GitLab Owner bypass is treated as an out-of-band integrity incident detected by reconciliation, immediately quarantined and handled through the G0-D3 emergency runbook rather than described as absolute technical prevention or a normal managed path.

**Given** the agreed pilot corpus, real approved hoster.ai inference, evaluation results and two independent non-engineering business users,
**When** pre-G2 acceptance is performed,
**Then** they complete the full **pending queue → read/edit → diff/rationale/evidence → accept/reject/cancel → history/restore** scenario without Git/CLI, exercising accept, reject and cancel on exact proposal fixtures and verifying the resulting canonical decisions, history cursor and reviewed revert-MR.
**And** controlled cutover and published retrieval are evidenced, full export and restore closure pass, all required P0 deterministic and real integration checks are green or explicitly BLOCKED, and a UI mock or partial path is not counted as acceptance.
**And** G2 is recorded only by the owner after reviewing this evidence, and completion of this necessary pilot part does not mark full T18 or the second-client/G3 repeatable-delivery scope complete.

**Dependencies:** E06.4 portability/restore, applicable P0 safety gates, and E07.1/E07.2 real pilot inference/evaluation evidence; protected deployment and pilot corpus require separate owner authorization.

**Evidence:** Planned evidence only, not executed tests: necessary internal-pilot scope supporting A01,A06,A07,A08,A09,A10,A15,A20,A22,A23,A28,A33 and G2; protected deployment inventory, external-migrator and DB-denial results, executed runbooks including privileged-Owner incident detection/quarantine/remediation, alerting/redaction checks, clean backup/restore drill, offline/cold-start and personal Notes/chat regressions, business acceptance and explicit owner gate record. No second-client/A19 completion claim is made; full T18 remains open for repeatable client delivery and G3.

**Rollback/upgrade impact:** rollback uses a pinned compatible application/configuration artifact under freeze, reviewed revert-MR for content, validated compatible index snapshot and owner-specific rehearsed database procedure; unknown recovery barriers are preserved. No destructive cleanup, production deploy/migration, hard purge, break-glass or client-specific code fork is introduced.

<!-- End story repeat -->

## Epic 8: Repeatable client delivery

Один выбранный connector, external updates, второй isolated deployment и эксплуатационные runbooks.

### Story 8.1 (T15): Safe source registry, three-way updates and durable cursors

As a knowledge operations owner,
I want external source versions converted into at most one reviewable proposal with truthful sync cursors,
So that repeated updates preserve curated knowledge and no deterministic sync can publish or delete content automatically.

Requirements: R06,R07,R08,R09,R10,R12,R13,R16,R18; I01,I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14; UX-DR18, UX-DR23, UX-DR25, UX-DR29, UX-DR30, UX-DR31, UX-DR33; A14,A17,A32; CF-04, CF-08, CF-19, CF-20, CF-25, CF-26.
Acceptance ownership: Full/direct — A14; Supporting — A17,A32.

**Acceptance Criteria:**

**Given** a versioned source binding with stable source/object IDs, immutable version/hash, owner and target repository=Space,
**When** a source observation is processed,
**Then** GO durably records `seen` only after sufficient observed metadata, `proposed` only after the durable MR plus ProposalRecord, and `merged` only after verified Git merge and source-mapping reconciliation.
**And** MR creation, rejection, conflict, timeout, extraction/indexing failure or a lost response never fabricates a later cursor state, and crash replay reconstructs each transition from durable source and Git evidence.

**Given** concurrent workers and several incoming versions for one source object,
**When** proposals are coordinated,
**Then** the same hash/version is a no-op or returns the existing proposal, at most one outstanding proposal exists, and newer observations update only `seen` until the current proposal reaches a terminal outcome.
**And** retry/resume uses the same source/version/operation idempotency identity, the latest seen version is handled from a fresh base after termination, and no second MR, duplicate proposal or false merged transition is created.

**Given** `migrated`, `source_managed`, `curated` and `live_operational` bindings,
**When** local edits or source updates arrive,
**Then** migrated ignores the old source as a writer, GO denies local edits to source-managed content, and every source-managed update requires GO/MR/human DecisionRecord/GO merge with no auto-merge even for a deterministic trusted diff.
**And** live operational remains a typed bounded read-only result with `snapshot_time`, creates no wiki page, MR, index entry or seen/proposed/merged cursor, and never presents stale data as current.

**Given** the previous imported base, current curated Git revision and incoming immutable source version,
**When** a curated update is prepared,
**Then** independent source and human changes in different paragraphs are preserved in the reviewable proposal, while same-paragraph or semantic conflicts are explicit with evidence and require human resolution.
**And** whole-file overwrite, automatic conflict merge and loss of curated front matter/links are forbidden, and unchanged content produces a no-op rather than an empty publication.

**Given** a source deletion, stale source ACL/owner status or an inaccessible object,
**When** synchronization runs,
**Then** deletion creates a tombstone/obsolete review with source provenance instead of silently deleting the document, attachments or index entry, and the owner chooses retain/archive/delete through the normal reviewed MR path.
**And** insufficient source authorization or missing owner feedback is visible and fail-closed, `merged` does not advance until the chosen outcome is verifiably applied, and retention of Git history, mirrors and object versions is preserved.

**Dependencies:** E06.2 import/cutover, E04.2 proposal/decision/merge evidence and E05.2 indexing/reconciliation, matching the existing T15 dependency set.

**Evidence:** Planned evidence only, not executed tests: Full/direct A14; supporting A17,A32; source registry and cursor transition cases, same-hash/no-op, concurrent one-outstanding tests, three-way curated positives and same-paragraph negatives, source-managed human-decision enforcement, live-operational zero-write assertions, tombstones and crash-before/after-MR/merge/cursor evidence. No deterministic auto-merge is accepted as a shortcut.

**Rollback/upgrade impact:** rollback disables new source observations/proposals while leaving existing MRs for human review and preserving conservative cursor state; it never marks proposed as merged or deletes source-managed content. Connector/config upgrades retain source IDs and provenance, require replay/crash regression, and introduce no client branch, production source or direct canonical write path.

<!-- End story repeat -->

### Story 8.2 (T16): One owner-selected real source connector

As a client source operator,
I want one explicitly selected SharePoint, Bitrix24 or Kayako connector to synchronize authorized source objects through reviewable GO proposals,
So that real updates, revocations, deletions, retries and assets are handled safely without implying support for unimplemented connectors.

Requirements: R05,R06,R12,R13,R14,R15,R16,R18; I01,I02,I03,I04,I06,I07,I09,I10,I11,I12,I13,I14; UX-DR19, UX-DR20, UX-DR25, UX-DR29, UX-DR31, UX-DR32, UX-DR33; A14,A16,A23,A25,A32; CF-08, CF-14, CF-26, CF-30.
Acceptance ownership: Full/direct — A14; Supporting — A16,A23,A25,A32.

**Acceptance Criteria:**

**Given** an owner selection of exactly one SharePoint, Bitrix24 or Kayako source and its exact objects, edition, API, authentication and sandbox,
**When** connector feasibility is validated,
**Then** list/changes/fetch/version/attachments/deletions/access-hints behavior, rate limits and least-privilege scopes are recorded against the real selected API with bounded backoff and sanitized errors.
**And** missing owner selection, sandbox, edition/API details or credentials leaves the story BLOCKED, mocks do not count as integration PASS, and the other two connectors are not described as ready.

**Given** synthetic or separately authorized sanitized objects in the real source sandbox,
**When** a new or changed object is synchronized,
**Then** the connector preserves stable remote ID, immutable version/hash, source owner and provenance, maps only to the explicitly configured repository=Space, and sends a proposal-only request to GO.
**And** the resulting MR/ProposalRecord and source lag are visible, human DecisionRecord and final GO merge remain mandatory, and connector identity has no pre-cutover bulk, direct push, merge, auto-merge, grants, export or index-pointer capability.

**Given** revoked source credentials or access, changed source ACL hints and revoked platform group membership,
**When** subsequent reads, payloads or proposals are attempted,
**Then** further source and platform access fails closed, access hints are treated only as hints rather than copied grants, affected subscriptions stop and no other-Space binding or browser/agent credential substitution succeeds.
**And** existing canonical history remains intact, sensitive export/merge rechecks deny revoked actors, and errors use anti-enumeration behavior without exposing protected source metadata.

**Given** deletion markers, transient API failures, retries and worker crashes,
**When** the connector resumes synchronization,
**Then** deletion produces the E08.1 tombstone/obsolete review rather than silent canonical deletion, bounded retry preserves operation identity, and at most one outstanding proposal survives duplicate webhooks/polling and concurrent workers.
**And** timeout, extraction failure or indexing completion does not advance `merged`, crash points restore seen/proposed/merged from durable evidence, and poison objects reach an observable dead-letter without repeated unbounded calls.

**Given** source attachments and large originals,
**When** assets are fetched and bound to proposal revisions,
**Then** each object is immutable/versioned with verified SHA-256, size, media type and source reference, uses scoped object credentials, and enters the assets manifest and dependency closure under the same Space ACL.
**And** mutable current URLs, missing/mismatched objects and failed production object-store ACL checks block affected complete/index claims, and source secrets, raw payloads, signed URLs and access tokens never enter documents, MR evidence, model arguments, logs or reports.

**Dependencies:** E08.1 safe update protocol and E02.3 authorization, plus the owner-selected source and real sandbox required by T16.

**Evidence:** Planned evidence only, not executed tests: A14 and applicable A16/A23/A25/A32; real selected-source sandbox update/revoke/delete/retry/attachment cases, exact edition/API/auth/rate-limit inventory, proposal-only GitLab/GO negatives, provenance/lag/cursor/crash results, immutable asset/hash/ACL checks and sanitized evidence. No real client secret or unapproved client document is stored in the workspace.

**Rollback/upgrade impact:** rollback revokes connector credentials and disables the binding without enabling direct writes or deleting canonical knowledge; outstanding proposals remain reviewable and unknown cursor states remain conservative. Source/API upgrades require contract, deletion/replay and asset-ACL regression in sandbox, with no universal sync layer or additional connector implied.

<!-- End story repeat -->

### Story 8.3 (T17 conditional): Evidence-gated extraction, media and OCR quality

As a content quality owner,
I want format-specific golden, loss and media/OCR evidence before enabling an extraction route,
So that originals remain recoverable and extraction or model assistance never becomes an unreviewed source of published facts.

Requirements: R02,R04,R12,R13,R15,R18; I01,I02,I03,I08,I09,I12,I13; UX-DR19, UX-DR20, UX-DR22, UX-DR29, UX-DR31, UX-DR33; A16,A22,A23; CF-05, CF-14, CF-30.
Acceptance ownership: Full/direct — A16,A23 только при activated conditional scope; Supporting — A22.

**Acceptance Criteria:**

**Given** a conditional workload requiring formats beyond the already supported Markdown path,
**When** T17 is considered for activation,
**Then** the owner first supplies authorized representative real samples and agrees the formats, quality review and data/media profile, while only synthetic or sanitized derivative fixtures and hashes enter the workspace.
**And** without those real samples the applicable extraction work remains BLOCKED and no route is enabled or marked PASS; for a Markdown-only workload the task is recorded N/A only through an explicit ADR/owner decision rather than silently skipped.

**Given** the pinned upstream extraction integrations and approved samples,
**When** the extraction route is evaluated,
**Then** the existing Docling integration is assessed first, and any second pipeline requires documented evidence of unmet need, an approved design/ADR and a separate compatibility, license and rollback assessment.
**And** original, extracted and canonical artifacts retain source/page/slide provenance, original/extracted/canonical hashes, converter/model/config/assets versions and explicit loss reports, with no blind LLM summary presented as recovered original text.

**Given** golden fixtures for agreed tables, text/scanned PDFs, presentations, languages including Russian and complex media,
**When** extraction quality is measured,
**Then** page/slide counts, encoding, reading order, table structure/numbers, links/anchors, omissions/duplications and fully usable documents are reported separately by format and risk with an agreed sample-quality review.
**And** empty/garbled output, unsupported formats, extraction loss, OCR disagreement and security failures are quarantined with the original recoverable, and prices, legal terms and other critical content receive the required full human verification rather than a model-only quality claim.

**Given** decorative, illustrative, substantive, critical and handwritten media,
**When** media and OCR processing runs,
**Then** decorative content is excluded, illustrative assets retain captions, substantive automatic descriptions are explicitly labelled and cite the original page/slide, and critical/handwritten knowledge enters the index only after required human transcription/verification.
**And** untranscribed handwriting, unverified critical media or an unlabelled automatic description cannot become an indexed fact or answer citation, and every attachment revision remains immutable, manifest-covered and subject to the repository=Space ACL.

**Given** malicious or malformed samples and any required extraction/OCR/vision inference,
**When** admission and provider routing execute,
**Then** traversal, symlinks, executable HTML/MDX/XSS, secrets, oversized/decompression-bomb inputs and invalid UTF-8 are rejected before corpus/preview, and only approved providers, data profiles, pinned model/licenses/assets and egress routes are used after sample approval.
**And** unresolved PII/media hits, external PII egress, unplanned fallback, missing offline assets or inadequate object-store ACL block the affected route, and a failed extraction never advances source `merged` or publishes a partial index.

**Dependencies:** E06.1 dry-run/security/data barrier and owner-authorized real format samples; this conditional story does not depend on E08.2 or create a connector requirement.

**Evidence:** Planned evidence only, not executed tests: Full/direct A16,A23 only for activated conditional scope; supporting A22; real-sample authorization record without private payloads in the workspace, Docling assessment, golden/loss reports by format, table/language/OCR fixtures, media-class and human-verification results, original/hash recovery, malicious negatives, approved provider/license/SBOM/offline inventory and object-store ACL evidence. N/A or BLOCKED is explicit where activation conditions are absent.

**Rollback/upgrade impact:** rollback disables the new extraction route and quarantines its noncanonical outputs without altering existing canonical documents or publishing unverified media. Model/extraction changes use versioned provenance and a new validated index profile, while originals remain immutable; no second pipeline, production corpus, provider call or external dependency is enabled by this planning story.

<!-- End story repeat -->

### Story 8.4 (T18a): Repeatable config-only dedicated deployment

As a client delivery engineer,
I want to reproduce the complete platform for a second isolated client from the same pinned core and configuration,
So that dedicated delivery is repeatable without client code forks or shared security boundaries.

Requirements: R05,R15,R17,R18; I04,I07,I09,I10,I11,I12,I13,I14; UX-DR2, UX-DR4, UX-DR26, UX-DR29, UX-DR32, UX-DR33; A19,A20,A33; CF-22, CF-30.
Acceptance ownership: Full/direct — A19,A20,A33; Supporting — не назначены. A19 проверяет second config-only dedicated client, resource isolation и отсутствие code fork.

**Acceptance Criteria:**

**Given** pinned reusable core artifacts and owner-approved configuration for two clients,
**When** dedicated deployment is repeated,
**Then** each client receives its own repositories=Spaces, Open WebUI/GO/Identity configuration and adapters, PostgreSQL/index/CI/object storage, immutable assets, secret references, backups, mirrors, network perimeter and egress allowlist without code edits or a client branch.
**And** the second client cannot read or write the first client's repositories, history, grants, objects, caches, logs or backups, personal Notes and ordinary chats retain upstream behavior, and branding/notices remain preserved.

**Given** isolated PostgreSQL roles and the pinned migration baseline,
**When** startup and initial owner-specific schema setup run,
**Then** runtime workers use `ENABLE_DB_MIGRATIONS=False` and non-DDL roles, only the authorized external migrator for each owning component applies and verifies expected migration heads before traffic, and pre/post checks, lock/duration, sanitized errors and rollback assessment are recorded.
**And** upstream, managed grants/`kb_authz`, `kb_ops` and `kb_index` reject every non-owner or cross-schema write, retrieval remains read-only, and an empty database is never treated as proof that no merge or external operation occurred.

**Given** the repeated client configuration and prepared offline assets,
**When** cold startup and isolation smoke checks execute,
**Then** proposal/merge, connector, CI/index and retrieval credentials remain separated, default egress is closed except approved routes, startup performs no unapproved download or provider fallback, and readiness distinguishes published, indexed and unavailable states rather than declaring success from container startup.
**And** all client-specific values come from configuration and deployment secrets, and any unavailable second-client resource or required isolation check remains BLOCKED rather than being simulated for acceptance.

**Dependencies:** E06.4 portability/restore, applicable P0 safety and release gates, and E07.3 pilot-hardening evidence; no T19/T20 work is a dependency.

**Evidence:** Planned evidence only, not executed tests: T18a scope for A19,A20,A33; two-client config-only resource/isolation matrix, external-migrator and cross-write negatives, credential/egress separation, cold offline startup and Notes/chat/branding regression. Current `operations.md` remains DESIGN NOT EXECUTED until these rehearsals exist.

**Rollback/upgrade impact:** application/configuration rollback uses pinned compatible artifacts under freeze and each database owner follows its rehearsed external procedure without clearing unknown barriers. No client code fork, destructive cleanup, production deployment/migration or direct human/service merge fallback is permitted.

<!-- End story repeat -->

### Story 8.5 (T18b full/G3): Backup, restore, upgrade and full operational acceptance

As a client operations owner,
I want clean disaster-recovery and upgrade rehearsals with the selected source connector and independent G3 review,
So that full T18 completion rests on demonstrated recovery, security and repeatable operations rather than artifact existence.

Requirements: R05,R06,R09,R10,R11,R13,R14,R15,R17,R18; I01,I02,I03,I04,I05,I06,I07,I09,I10,I11,I12,I13,I14; UX-DR2, UX-DR13, UX-DR26, UX-DR27, UX-DR29, UX-DR31, UX-DR32, UX-DR33, UX-DR34; A14,A15,A19,A20,A28,A33; CF-14, CF-15, CF-16, CF-17, CF-18, CF-21, CF-22, CF-23, CF-25, CF-30.
Acceptance ownership: Full/direct — A15,A19,A20,A33; Supporting — A14,A28. A19 закрывается итоговой operational/G3 проверкой уже развёрнутого второго клиента.

**Acceptance Criteria:**

**Given** complete mirror/metadata/object/config backups and a separate secrets recovery policy for each deployed client,
**When** clean restore and disaster-recovery rehearsals run,
**Then** refs, MR/note/audit metadata, decisions/assets/authorization closure and hashes are validated, `kb_authz` is freshly rebuilt, Git-derived `kb_ops` projections are recovered under global merge freeze with conservative barriers, and `kb_index` is fully rebuilt before a new pointer and activation.
**And** a separate durable non-Git-derived correction backup preserves correction-task current projections, append-only events, restricted evidence and idempotency records; restore validates hashes/event sequences/perimeter and performs linked-MR reconciliation without fabricating, deleting, resolving or cancelling tasks. Git-only rebuild neither recreates nor discards correction state, and correction backup/restore/reconciliation never creates a second canonical write path—content changes still require MR/human DecisionRecord/GO merge.
**And** unknown merge outcomes remain quarantined, missing assets, incomplete closure or a missing/corrupt correction backup block READY for the affected scope, cross-client negative controls fail closed, and owner-approved RPO/RTO, retention, backup cadence and recovery evidence are recorded rather than inferred.

**Given** the deployed client perimeters and approved telemetry destinations,
**When** operations and incidents are exercised,
**Then** metrics/alerts/runbooks cover startup, cutover/activation, merge result/latency, locks/fencing/recovery age/quarantine, decision mismatches, CI/webhook/HEAD drift, revocation, source cursors, export/backup closure, source sync, TTFT/full response and restore/upgrade procedures.
**And** secrets, raw documents/chunks/queries/rationale/evidence, provider payloads, signed URLs and PII snippets are absent from telemetry, retention and attachment/mirror cleanup preserve unresolved recovery/DLQ/export closure. Routine/self-service admin break-glass and hard purge remain disabled; an out-of-band privileged GitLab Owner bypass triggers unexpected-HEAD reconciliation, immediate affected-target quarantine/managed-write freeze, preserved audit evidence and the G0-D3 emergency incident runbook through owner-reviewed closure.

**Given** an isolated upgrade target, prepared offline assets and the registered upstream seams,
**When** Open WebUI, GitLab and platform upgrade/rollback rehearsals run,
**Then** dependency pins, SBOM/license diff, branding/notices, external migration order, cold offline startup, startup reconciliation and every registered auth/grant/tool/editor/retrieval/connector seam are evaluated with rollback evidence.
**And** no unapproved download, model/provider fallback, destructive live index rebuild, canonical history rewrite or direct-merge fallback occurs, and failures block the upgrade rather than being waived as upstream debt.

**Given** the E08.4 second-client deployment, E08.2 real selected-connector evidence, clean backup/restore and upgrade results, and independent security/operations reviewers,
**When** full T18/G3 acceptance is evaluated,
**Then** one external source updates through human decision and GO merge without auto-merge, config-only second-client isolation, schema ownership, no-bypass controls, decisions/assets/metadata restore, observability/secrets/egress controls and all applicable runbooks are demonstrated in the real designated environment.
**And** any unavailable required connector, object-store, second-client or recovery check remains BLOCKED, owner acceptance is recorded separately rather than inferred from artifact existence, and only then can full T18 and the applicable G3 operational/security gate be considered complete.

**Dependencies:** E08.4 repeatable dedicated deployment and explicitly E08.2/T16 selected real connector for full T18/G3; E06.4 portability/restore including its separate correction backup/restore and linked-MR reconciliation is inherited through E08.4, and the existing E04.7 correction schema/API remains the only correction operational contract. E08.3 evidence is required only when its conditional extraction scope is activated, no future T19/T20 work is a dependency, and necessary pilot/T18a completion never marks full T18/G3 complete without T16. Correction content changes retain the governed MR path with no second canonical write path.

**Evidence:** Planned evidence only, not executed tests: full T18/G3 scope for A14,A15,A19,A20,A28,A33; selected-connector/no-auto-merge evidence, mirror/metadata/object restore drills, separate durable non-Git-derived correction-task current/events/evidence/idempotency backup and restore, hash/event-sequence/perimeter checks and linked-MR reconciliation without fabrication/deletion/resolve/cancel or a second canonical write path; conservative rebuild and unknown-outcome controls, secrets/egress/telemetry canaries, cold offline upgrade/rollback/SBOM/seam results, executed runbooks and independent owner acceptance. Current `operations.md` remains DESIGN NOT EXECUTED until these rehearsals exist.

**Rollback/upgrade impact:** application/configuration rollback uses pinned compatible artifacts under freeze, content uses reviewed revert-MR, indexes use validated compatible snapshots, and each database owner follows its rehearsed external procedure without clearing unknown barriers. No client code fork, destructive cleanup, production deployment/migration, plaintext secrets backup or direct human/service merge fallback is permitted.

<!-- End story repeat -->

### Deferred: T19/T20

- **T19 — Retrieval evolution:** deferred until T14 supplies measured ACL-aware quality/latency/cost benchmarks and a separate business gate approves the work. Only then may the baseline PG FTS+pgvector profile be compared with measured alternatives using shadow index/dual-read evaluation and a non-destructive migration plan; OpenSearch or another stack expansion is not pre-approved. This note creates no new epic or story ID.
- **T20 — Fast/Trust/Scale policies:** deferred until T14 and full T18 are complete and a separate measured/business gate approves the work. Its R/I/A mapping must be clarified at that future planning point because `spec.md` has no explicit T20 Requirements row; existing design-derived links are not normative assignments. No cache, routing, threshold, capacity or client-profile commitment is created here, and no new epic or story ID is introduced.

<!-- End story repeat -->

---

## Implementation Phase Epics

The epics below deliver the actual application code described by the contracts and harnesses in E01–E08. They are not replacements for T01–T18b; they are the implementation work that makes those contracts executable.

### Epic 9: Identity + AuthZ adapter implementation

Реальный Python/FastAPI сервис Identity + AuthZ adapter с PostgreSQL хранилищем, миграциями и API.

### Story 9.1 (I01): Project bootstrap and local infrastructure

As a developer,
I want a reproducible `src/` layout, Docker Compose for local dependencies and CI-ready Python tooling,
So that implementation work starts from a stable, repeatable environment.

Requirements: R01,R18; I01,I09,I10; A01; CF-01.
Acceptance ownership: Full/direct — A01.

**Acceptance Criteria:**

**Given** the repository root,
**When** `src/` layout is created,
**Then** `src/identity/`, `src/git-orchestrator/`, `src/retrieval/`, `src/ingestion/`, `src/open-webui/`, `src/contracts/`, and `src/docker/` exist with clear package boundaries and no cross-service imports in domain code.
**And** root `pyproject.toml` declares Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, psycopg, pgvector and dev tools, and `uv sync` completes without errors.

**Given** Docker Compose,
**When** `docker compose up -d postgres keycloak minio` runs,
**Then** PostgreSQL 18 + pgvector starts with `kb_authz`, `kb_ops`, `kb_index` schemas, Keycloak 26.8.2 starts in dev mode, and MinIO starts with console accessible.
**And** health checks pass and default credentials are documented in `.env.example`, not hardcoded in application code.

**Dependencies:** none (implementation phase bootstrap).

**Evidence:** `docker-compose.yml`, `src/docker/postgres-init/01-create-schemas.sql`, `src/*/pyproject.toml` or root package layout, `.env.example`, `uv sync` output.

### Story 9.2 (I02): Identity domain models and `kb_authz` migrations

As an identity engineer,
I want SQLAlchemy models and Alembic migrations for identities, group snapshots, policy bundles, AuthzContext and revocations,
So that `kb_authz` persists the data needed for authorization decisions.

Requirements: R05,R16; I05,I09,I10; A04,A24,A25,A26,A30,A32; CF-02.
Acceptance ownership: Full/direct — A04,A24,A25,A26; Supporting — A30,A32.

**Acceptance Criteria:**

**Given** the `src/identity/` package,
**When** models are defined,
**Then** `Identity`, `GroupSnapshot`, `PolicyBundle`, `AuthzContext`, and `Revocation` use SQLAlchemy 2.0 `Mapped[]`/`mapped_column`, target the `kb_authz` schema, and support PostgreSQL JSONB with SQLite fallback for tests.
**And** each table has created_at/updated_at timestamps and appropriate indexes for space_id, actor_id, epoch, and external_ref lookups.

**Given** Alembic,
**When** `alembic upgrade head` runs,
**Then** all five tables are created under `kb_authz`, and `alembic downgrade base` cleanly removes them.
**And** migration head is recorded and versioned; runtime workers never run migrations automatically.

**Dependencies:** I01.

**Evidence:** model files, initial migration, `alembic history` output, unit tests for model constraints.

### Story 9.3 (I03): Identity resolution and group snapshot ingestion

As an identity engineer,
I want stable identity resolution and nested group snapshot ingestion with epoch ordering,
So that every request maps to a durable identity and current group membership.

Requirements: R05,R16; I05,I09; A04,A24,A25,A26,A30,A32; CF-02.
Acceptance ownership: Full/direct — A04,A24; Supporting — A25,A26,A30,A32.

**Acceptance Criteria:**

**Given** external identity references (LDAP DN, OIDC sub, objectGUID, entryUUID),
**When** `POST /api/kb/v1/identity/resolve` is called,
**Then** a stable `Identity` is returned or created, and renames do not change the internal identity key.
**And** empty or conflicting external refs produce structured `{code,message,request_id,retryable}` errors.

**Given** group snapshots with nested groups and epochs,
**When** `POST /api/kb/v1/groups/snapshot` is called,
**Then** nested memberships are flattened into member_refs, epochs are monotonically ordered per Space, and out-of-order snapshots are rejected or recorded as stale.
**And** group rename preserves identity and historical snapshots remain queryable.

**Dependencies:** I02.

**Evidence:** service layer, API routes, T03a fixture-based contract tests, unit tests for rename and epoch ordering.

### Story 9.4 (I04): Policy activation, AuthzContext and path approval

As an authorization engineer,
I want policy bundle activation, computed AuthzContext, and longest-prefix path approval,
So that per-Space access decisions are deterministic and revocation-safe.

Requirements: R05,R16; I05,I09; A04,A24,A25,A26,A30,A32,A33; CF-02.
Acceptance ownership: Full/direct — A25,A26; Supporting — A04,A24,A30,A32,A33.

**Acceptance Criteria:**

**Given** a policy bundle with approvers and path patterns,
**When** `POST /api/kb/v1/policies/activate` is called,
**Then** the bundle is stored with activation_epoch and valid_until, and only one active policy per Space+epoch is allowed.
**And** activation validates policy schema and rejects malformed or conflicting bundles.

**Given** an actor, Space and group snapshot,
**When** `POST /api/kb/v1/authz/context` is called,
**Then** AuthzContext contains resolved groups, applicable policies, actor type, and epoch, and is cached or computed deterministically.
**And** revoked epochs invalidate cached contexts.

**Given** a document path and actor,
**When** `POST /api/kb/v1/authz/check` is called,
**Then** longest-prefix matching determines approval, path normalization prevents traversal, and unauthorized requests return structured errors.
**And** cross-Space checks are denied and no cross-Space data leaks in error messages.

**Dependencies:** I03.

**Evidence:** service layer, API routes, T03b fixture-based contract tests, unit tests for longest-prefix and revocation.

### Epic 10: Git Orchestrator implementation

Реальный Git Orchestrator с GitLab client, canonical reads, ProposalRecord/DecisionRecord lifecycle.

### Story 10.1 (I05): Git Orchestrator bootstrap and GitLab client

As a backend engineer,
I want a FastAPI service with GitLab client, connection pooling and exact-SHA read APIs,
So that canonical document reads are served by GO instead of direct UI Git access.

Requirements: R02,R05,R06,R09; I01,I02,I06,I08; A05,A06,A08,A09; CF-03.
Acceptance ownership: Full/direct — A08; Supporting — A05,A06,A09.

**Acceptance Criteria:**

**Given** `src/git-orchestrator/`,
**When** the service starts,
**Then** it exposes `/health`, `/api/kb/v1/documents/read`, `/api/kb/v1/documents/tree`, and GitLab client configuration via environment variables.
**And** reads are scoped to repository=Space and exact SHA; no write endpoints are exposed in this story.

**Dependencies:** E09.I01 (implementation-phase bootstrap only).

**Evidence:** service skeleton, GitLab adapter interface, read API, unit tests with mocked GitLab.

### Story 10.2 (I06): ProposalRecord and DecisionRecord lifecycle

As a backend engineer,
I want ProposalRecord creation, review, DecisionRecord persistence and exact merge coordination,
So that canonical changes follow the governed MR/human decision path.

Requirements: R06,R07,R08,R09; I02,I06,I08,I09; A05,A06,A07,A08,A09,A27,A28,A29,A30; CF-03,CF-04.
Acceptance ownership: Full/direct — A05,A06,A07,A08,A09,A27,A28,A29,A30.

**Acceptance Criteria:**

**Given** a ProposalRecord,
**When** it is submitted,
**Then** it is stored as a GitLab MR with a `kb_ops` operational projection, validated against schema, and linked to exact base SHA and idempotency key.
**And** only authorized actors can create proposals, and self-approval is denied.

**Given** a DecisionRecord and MR,
**When** merge is requested,
**Then** GO verifies HEAD matches proposal base, merge-only rules, and DecisionRecord before allowing GitLab merge.
**And** direct push and auto-merge are denied; recovery and quarantine states are explicit.

**Dependencies:** E10.I05.

**Evidence:** ProposalRecord/DecisionRecord models, merge enforcement service, T05/T06 fixture-based contract tests.

### Epic 11: Open WebUI fork KB seams

Управляемые расширения Open WebUI для KB tree, direct read, TipTap editor и review UI.

### Story 11.1 (I07): Open WebUI fork setup and KB API client

As a frontend engineer,
I want the pinned Open WebUI fork embedded under `src/open-webui/` with a typed KB API client,
So that UI can call GO/Identity services without direct GitLab or DB access.

Requirements: R01,R02,R03,R09; I01,I02,I06; A01,A08,A10; CF-01,CF-03.
Acceptance ownership: Full/direct — A01,A08; Supporting — A10.

**Acceptance Criteria:**

**Given** `src/open-webui/`,
**When** the fork is initialized,
**Then** upstream v0.13.0 commit is preserved, `src/lib/api/kb.ts` or equivalent client exists, and UI routes for KB tree and document read are registered.
**And** no direct GitLab API or `kb_*` DB access exists in UI code.

**Dependencies:** E10.I05, E09.I04.

**Evidence:** fork layout, KB API client, route registration, frontend build passes.

### Epic 12: Retrieval + indexing implementation

### Story 12.1 (I08): Index worker and pgvector search

As a retrieval engineer,
I want CI-triggered index builds, exact/semantic search and per-payload re-authorization,
So that users can search within their authorized document set.

Requirements: R04,R11,R16; I03,I05,I06; A02,A03,A11,A12,A21,A25,A31,A32; CF-05.
Acceptance ownership: Full/direct — A03,A12,A21; Supporting — A02,A11,A25,A31,A32.

**Acceptance Criteria:**

**Given** canonical snapshots from GO,
**When** index worker runs,
**Then** `kb_index` stores generations, active pointers, and pgvector embeddings; search results are filtered by AuthzContext per payload.
**And** exact search uses PostgreSQL FTS, semantic uses pgvector, and hybrid RRF is configurable.

**Dependencies:** E10.I05, E09.I04.

**Evidence:** index models, worker, search API, T10a/T10b fixture-based tests.

### Epic 13: Ingestion + source connectors implementation

### Story 13.1 (I09): Dry-run importer and source registry

As an ingestion engineer,
I want deterministic dry-run import, source registry and durable cursors,
So that external sources can be onboarded without canonical writes until approved.

Requirements: R12,R13,R16; I06,I08,I09; A13,A14,A23,A31,A35; CF-06.
Acceptance ownership: Full/direct — A13,A14,A23; Supporting — A31,A35.

**Acceptance Criteria:**

**Given** a source configuration,
**When** dry-run runs,
**Then** it produces manifest, blockers and hash-stable preview without writing to canonical Git or product DB.
**And** source cursors are durable and resumable; three-way updates detect conflicts.

**Dependencies:** E10.I06, E09.I04.

**Evidence:** importer, registry, T12a/T15 fixture-based tests.

<!-- End story repeat -->
