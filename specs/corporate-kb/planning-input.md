# Corporate KB — входной пакет для планирования эпиков и спринтов

## 1. Назначение, аудитория и правила использования

Документ собирает уже подготовленный design package в единый вход для последующей декомпозиции существующих **E00–E08** и задач **T00–T20**. Он предназначен для product owner, tech lead, backend/frontend, QA, DevOps, source owners и business approvers.

Это **не список новых эпиков или stories**, не sprint commitment и не разрешение на реализацию. Идентификаторы E/T не переименовываются и не перенумеровываются. Предлагаемые ниже вертикальные срезы — варианты для будущего planning, а не новые backlog IDs. Capacity, сроки, оценки, story points, бюджет и новые SLA не назначаются. Уже утверждённые ограничения group refresh ≤ 15 минут и revocation SLO ≤ 30 минут остаются требованиями, а не новым плановым обещанием.

Нормативный приоритет: [Architecture Spine AD-1–AD-17](architecture-spine.md) → [spec.md v1.3, R01–R18 и I01–I14](spec.md) → [ADR-03–ADR-17](adr/README.md) → component/database/integration design → плановые детали. Дополнительные ограничения фазы: [AGENTS.md](../../AGENTS.md). Полнота связей находится в [traceability.md](traceability.md), фактические статусы — в [tasks.md](tasks.md). T00 baseline evidence: [baseline.md](baseline.md) и [evidence/t00](evidence/t00/README.md); owner decision record: [g0-review.md](g0-review.md) (**APPROVED**). **T00 DONE, G0 APPROVED**; можно переходить к декомпозиции эпиков, сохраняя deferred gates и зависимости задач.

## 2. Design readiness и implementation boundary

### READY FOR EPIC DECOMPOSITION — только design package

Для аналитической декомпозиции уже есть:

- стабильные R01–R18, I01–I14, A01–A36, E00–E08 и T00–T20;
- принятые архитектурные инварианты AD-1–AD-17 и оформленные ADR-03–ADR-17 с различением Accepted/Proposed;
- component boundaries, state ownership, DB catalog, API/tool/event/schema contracts и integration protocols;
- dependency/gate model, acceptance coverage и правила evidence;
- synthetic-fixture и environment needs для последующего T01.

**Уровень этой готовности — DESIGN.** Она не означает VERIFIED, DONE, security approval, production approval или подтверждённую реализуемость на конкретных версиях.

### BLOCKED FOR IMPLEMENTATION — readiness correction и остаточные evidence gaps

Реализация T01–T20 не разблокирована:

- **T00 DONE, G0 APPROVED** ([tasks.md](tasks.md), [g0-review.md](g0-review.md)); implementation начинается только по зависимостям и сохраняет deferred gates, production readiness не заявляется;
- pinned baseline и capability evidence **записаны** ([baseline.md](baseline.md), [evidence/t00](evidence/t00/README.md)): Open WebUI `v0.13.0` `c38885a1…`, GitLab CE `19.5.3` (42 completed synthetic probes; target-race nonconforming merge proves mandatory GO lock), PostgreSQL `18.6` + pgvector `0.8.7` (22/22 synthetic gates), Keycloak adapter 9/9, stock OIDC 4 PASS/2 FAIL, external migrator PASS head `e42c8f710a36`. Это synthetic sandbox evidence, не production readiness;
- CI Runner exact-SHA/no-write evidence записан ([ci-runner.md](evidence/t00/ci-runner.md), 7/7 PASS); production queue/autoscaling/Docker executor/object-store не проверялись;
- выбран **TipTap adapter (G0-D8)**: WYSIWYG editing retained; headless CodeMirror byte fidelity PASS / TipTap normalization-loss; browser/IME/accessibility/XSS/full managed preview — APPROVED DEFERRAL на T04 (G0-D15), не PASS. Realtime collaboration/CRDT вне MVP; conflict detection, exact/fresh revisions, full diff и новая ProposalVersion обязательны;
- frontend quality gates не являются releasable baseline: svelte-check FAIL (5722 errors), ESLint parser crash, upstream `npm run build` OOM (G0-D9); Vitest и direct Vite build PASS;
- identity adapter, deny-by-default execution boundary и external migrator controls подтверждены как обязательные, но не реализованы; stock LDAP/OIDC и stock tool approval не являются ADR-010/ADR-012 implementations;
- [test-plan.md](test-plan.md) существует как `design_not_executed`; полные сценарии A01–A36 и fault matrix сохранены, R/I coverage вынесен в [traceability.md](traceability.md); A01–A36 и CF-01–CF-30 не выполнялись;
- реальные hoster.ai studio endpoint/credentials не подтверждены; для T11 это BLOCKED, mock не является PASS.

Фактические состояния T00–T20, G0, owner approval и текущие blockers поддерживаются только в [tasks.md](tasks.md); этот planning input не дублирует live tracker и не меняет статусы. Перечисленные выше отсутствующие evidence — границы готовности design package, а не отдельная динамическая сводка.

## 3. Готовые design inputs

| Пакет | Что уже можно использовать | Статус и ограничение |
|---|---|---|
| [spec.md v1.3](spec.md) | Нормативные R/I/A/T/E, протоколы, gates, DoR/DoD | proposed; не baseline и не разрешение implementation |
| [ARCHITECTURE-SPINE.md](architecture-spine.md) | AD-1–AD-17, capability map, deferred и consistency conventions | обязательные design invariants; не upstream verification |
| [architecture.md](architecture.md) | Containers, responsibilities, credentials, lifecycle, recovery, NFR evidence | T00 DONE/G0 APPROVED; pinned code references записаны, implementation gates остаются |
| [Open WebUI fork](components/open-webui-fork.md) | UI/editor/review/agent seams, state model, regression Notes/chats | TipTap adapter selected G0-D8; canonical adapter/browser evidence pending |
| [Git Orchestrator](components/git-orchestrator.md) | Draft/proposal/decision/merge/recovery/cutover/export protocols | GitLab 42 synthetic capability probes записаны; product integration не выполнена |
| [Identity and Access](components/identity-access.md) | Stable identity, policy bundle, grants, AuthzContext, revocation | Keycloak/OpenLDAP synthetic evidence записано; production AD/live-SLO pending |
| [Retrieval and Indexing](components/retrieval-indexing.md) | Snapshot/generation/profile/closure/pointer/query semantics | pgvector validated candidate 22/22 synthetic gates; production parameters UNKNOWN |
| [Ingestion and Connectors](components/ingestion-connectors.md) | Dry-run, data barrier, ownership modes, cursors, assets/media | connector/source/object-store layout UNKNOWN |
| [ADR index](adr/README.md) | ADR-03–ADR-17 и их фактические статусы | Accepted не равен G0/production approval; ADR-01/02 withdrawn |
| [database.md](database.md) + [database-catalog.yaml](contracts/database-catalog.yaml) | Single-writer schemas, tables, transactions, rebuild/runbooks | логический DESIGN, не DDL/migrations; один instance — assumption до T00 |
| [integration.md](integration.md) + [contracts/README.md](contracts/README.md) | Сквозные integration protocols и contract map | PROPOSED; T01 contract/conformance tests не выполнялись |
| [openapi.yaml](contracts/openapi.yaml), [agent-tools.yaml](contracts/agent-tools.yaml), [events.yaml](contracts/events.yaml) | Собственные GO API, bounded tools, event envelopes | не утверждённые upstream routes/registrations/transports |
| [JSON schemas](contracts/README.md#2-карта-артефактов) | `document-front-matter-v2`, `authz-context-v2`, `export-manifest-v2`, policies, Proposal/Decision, index/origin и DocOps metadata | PROPOSED machine contracts; hashes/limits не являются production commitments |
| [projection-mapping.md](contracts/projection-mapping.md) + [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml) | Подготовленные canonical↔API↔event↔DB mappings и CF-01–CF-30 consumer vectors, включая correction lifecycle/idempotency/CAS/no-MR/backup negatives | **DESIGN output / DESIGN_NOT_EXECUTED**, не VERIFIED test и не integration PASS |
| [docops-correction-task.schema.json](contracts/docops-correction-task.schema.json) + [docops-correction-api.md](contracts/docops-correction-api.md) | Единственный correction-task contract для E04.7/T07b: exact revision, stable actor, policy owner, evidence hash, linked MR optional, open/in_review/resolved/cancelled, create/get/resolve/cancel, kb_ops backup/rebuild | PROPOSED/DESIGN после создания contract; implementation и T01 execution не выполнялись |
| [GitLab](contracts/gitlab-integration.md), [Identity](contracts/identity-integration.md), [Inference](contracts/inference-integration.md), [Source/storage](contracts/source-storage-integration.md) contracts | Детальные external-boundary protocols и T00 checks | Synthetic capabilities подтверждены в задокументированных sandbox scopes; production integrations и недоступные real hoster/source/object-store checks остаются BLOCKED |
| [content-standard.md](content-standard.md) | ETL, controlled initial publication, DocOps, media/data barriers | subordinate process standard 2.3; production corpus не создаётся |
| [operations.md](operations.md) | Deployment topology, credentials, startup/cutover/recovery/export/restore/upgrade runbooks | `design_not_executed`; T18 rehearsals и production readiness не подтверждены |
| [test-plan.md](test-plan.md) | Test levels, synthetic fixtures, полный A01–A36 scenario catalog, CF vectors и fault matrix | `design_not_executed`; R/I navigation не дублируется и находится в traceability; сценарии не запущены |
| [traceability.md](traceability.md) | R/I → AD/ADR → components → DB/contracts → A → T/E, A01–A36 и CF-01–CF-30 | DESIGN coverage, не executed test matrix |
| [tasks.md](tasks.md) | Живой tracker T00–T20, остаток T00, resolved discrepancies | **Единственный источник фактических динамических состояний** |

Навигация синхронизирована с фактически существующими [ADR index](adr/README.md), [contracts README](contracts/README.md), [operations.md](operations.md) и [architecture.md](architecture.md). Наличие документов остаётся DESIGN evidence, не owner G0 approval.

## 4. Границы MVP и non-goals

### MVP / обязательный периметр

- Единый Open WebUI experience: Spaces/tree/direct read/WYSIWYG/review/chat; бизнес-пользователь и approver не используют Git/CLI или GitLab account.
- Строго **один GitLab repository = один Space = один ACL/history/cutover/index/export/backup perimeter**. Разные ACL, включая pricing, разводятся заранее по repositories.
- GitLab canonical Markdown + closed front matter, opaque stable document UUID, exact full SHA revisions, MR/ProposalRecord, canonical DecisionRecord note+tag и real merge commits.
- Двухслойный RBAC: platform identity/approval policy для бизнеса; GitLab/CODEOWNERS только для engineering review. Business approval использует versioned `approval-policy.yaml`.
- После cutover все business/engineering/source-managed applies выполняет только GO после human decision; direct push/merge и auto-merge запрещены.
- Exact-SHA merge parentage/trailers, per-target serialization/fencing, durable `recovery_required`, Git-derived reconciliation/quarantine. Unknown/invalid без proven outcome не очищает barrier; `failed` имеет guarded same-decision retry после completed+no-merge evidence, `conflicted`/`invalid` terminal.
- `authz-context-v2` с independent per-Space repository/policy+approval revisions/group snapshot/revocation epoch; multi-Space fan-out/cursor не заимствует bindings. `document-front-matter-v2` сохраняет stable links/valid_until/origin и двусторонний archive invariant; restricted agent получает только body create/`AgentAnchoredPatchChange`.
- Rebuildable ACL/SHA/ancestry/profile-aware exact+semantic index из eligible published `main`; inactive cutover preflight никогда не serving.
- Controlled pre-cutover load только в unpublished `main` при закрытом доступе и отсутствии published index; затем freeze → exact HEAD → protections → inactive preflight → **separate same-SHA published request/run/snapshot** → per-Space/profile fence/CAS pointer across all generations → Space activation.
- Четыре source contracts: `migrated`, `source_managed`, `curated`, `live_operational`; последний остаётся typed read-only и не становится wiki автоматически.
- Dedicated client deployment и `export-manifest-v2`: explicit decision outcomes/recovery, decisions/assets/authorization closure + mirror/metadata backup + restore evidence.
- Approved inference/data profiles, bounded read/search/propose tools и deterministic security/regression evidence.

### Non-goals / DEFERRED без новых требований и ADR

Общая multi-tenant БД; arbitrary page-level ACL внутри repository; realtime collaborative editing/CRDT; agent/connector/LLM auto-merge; несколько approvers/quorum; arbitrary shell/Python/SQL/filesystem/Git; agent bulk/subtree/attachment operations; GraphRAG/people graph; новый inference gateway; universal two-way sync; все connectors сразу; второй Git hosting; automatic rebrand/white-label; routine/self-service admin break-glass product capability; privacy hard purge/filtered history export; GitLab-outage stale reads; OpenSearch без измеренной необходимости. Emergency G0-D3 out-of-band privileged incident runbook обязателен и не является routine break-glass feature.

T19/T20 относятся к последующим measured optimizations и не включаются в MVP по наличию общего design package. Обязательные realtime collaboration или page-level ACL с прямым Git access являются stop-триггерами пересмотра канона, а не скрытым расширением scope.

## 5. Workstreams и существующие E00–E08 / T00–T20

| Workstream | Существующий результат и IDs | Основной component/contract ownership | Acceptance/gate ownership |
|---|---|---|---|
| Baseline и governance | **E00 / T00**: pinned baseline, capabilities, ADR/design review | Tech lead + Open WebUI/GitLab/Identity/DB/CI auditors; owner решает G0 | T00 capability matrix, A24/A34 baseline checks, G0; вся A01–A36 mapping |
| Contracts и test foundation | **E01 / T01**, начальный **T14** | QA + contract owners; schemas/API/tools/events/DB catalog/fixtures | Closed-schema, negative/concurrency/crash harness, A21/A33; последующие все A |
| Managed documents и access | **E02 / T02,T03** | Open WebUI + GO document mapping + Identity/AuthZ; front matter/policies/AuthzContext | A01,A04,A24–A26,A30,A32,A33; G1 prerequisites |
| Save и history | **E03 / T04** | GO draft/save/history/revert + UI editor adapter | A08–A10 и связанные conflicts/statuses |
| Governed workflow | **E04 / T05,T06,T07,T07b,T08,T09**, G1-профиль **T11** | GO + Open WebUI + Identity + bounded tools/model connections + [correction contract](contracts/docops-correction-api.md) | A01,A02,A04–A10,A17,A18,A21–A23,A27–A30,A34,A36; G1 |
| Published knowledge pipeline | **E05 / T10**, проверки **T14** | CI/index writer + retrieval read-only + GO/Identity contracts | A02,A03,A11,A12,A21,A22,A25,A31,A35; G2 |
| Migration и portability | **E06 / T12,T13**, минимальная защита **T15**; полный T12/T12b после T05, отдельная T12a dry-run раньше | Ingestion + GO + index/export + Identity/object storage | A11,A13,A15,A23,A25,A27,A31,A32,A35,A36; G2 |
| Internal pilot acceptance | **E07 / T11,T14**, необходимая часть **T18** | Open WebUI/model connections + retrieval + QA + operations | A03,A16,A18,A20,A21 и expert quality/security evidence; G2 |
| Repeatable client delivery | **E08 / T15,T16,T18**, условно **T17**; полный T18/G3 явно после T16 | Source adapters + dedicated deployment/backup/upgrade/operations | A14–A16,A19,A20,A23,A28,A33; G3 |
| Measured evolution, вне текущих E00–E08 | **T19,T20** после benchmark/business gate | Retrieval/QA/operations по измеренной необходимости | T19 зависит T14; T20 зависит T14,T18; G4; новые E IDs здесь не создаются |

Один T может поддерживать несколько результатов, но при будущей декомпозиции получает одного ответственного и единый учёт труда. Компонентная таблица не назначает людей или capacity.

## 6. Dependency map: реальные блокеры и параллельность

### 6.1. Жёсткий критический путь

```text
T00 + owner G0
  → T01 → T02 → T03 → T04
                       ├─→ T05
                       │    ├─→ T06 ─┐
                       │    └─→ T07 ─┴─→ T08 ─→ T09 ─→ T11 ─┐
                       │    └─→ T12b ─→ T13 ────────────────┤
                       ├─→ T10 ─────────────────────────────┼─→ T14
                       │    └─→ T12b preflight/published artifacts
                       └─→ T12a dry-run (separate early work) ─→ T12b

T15 ← T12+T05+T10; T16 ← T15+T03
T18 necessary/T18a ← P0 safety gates+T13+соответствующие release gates
full T18/G3 ← T16+T18a+E06.4 restore evidence
T14+full T18 → T20; T14 → T19
```

Дополнительные зависимости: полный T12/T12b ← T03+T04+T05 и T10 artifacts; T13 ← T12; T14 ← T01+T09+T10+T11; T17 ← T12; T15 также поддерживает E06; T16 не опережает core; полный T18/G3 явно зависит от T16 и не закрывается necessary pilot/T18a. **T07b ← T05+T07+созданный correction-task contract**, в `sprint-status.yaml` попадает только при последующей deterministic generation после readiness PASS. T13/T18 restore использует отдельный durable non-Git-derived correction-task backup и linked-MR reconciliation без второго canonical write path. T20 не получает самостоятельного разрешения от наличия T14/T18: требуется measured/business gate.

### 6.2. Что можно параллелить после G0 без ослабления зависимостей

- **T06 и T07** после T05: enforcement и review UI; G1 закрывается только совместным real evidence. **T07b** после T07 и созданного correction contract не вводит forward dependency на E04.2 сверх существующей T05/T07 цепочки и не блокирует unrelated DocOps projection work.
- **T10** после T03+T04 параллельно с T05–T09: CI/index и retrieval не ждут завершения review/agent chain, но T14 ждёт обе ветки.
- **T12a dry-run/admission** после T03+T04 может выполняться параллельно T05/T10 только как отдельная работа без canonical writes. Полный T12/T12b cutover merge lifecycle начинается после T05 и использует T10 preflight/published artifacts; это не разрешает параллельный full T12 с T05. Production corpus и реальные данные — только после отдельного разрешения.
- **T13** после полного T12; полный restore не объявляется до clean-instance evidence, включая отдельный durable non-Git-derived correction-task current/events/evidence/idempotency backup/restore и linked-MR reconciliation без второго canonical write path.
- **T18 full/G3** явно ждёт T16 selected real connector вместе с T18a и E06.4 restore evidence; necessary pilot/T18a могут подготавливать свои slices, но не закрывают full T18/G3 досрочно.
- UI T07/T08 может готовиться по согласованным contracts параллельно с backend работой, но формальные Depends T08←T07 и T09←T06+T08 сохраняются; mock UI не закрывает G1.
- QA fixtures/contract vectors готовятся вместе с компонентами после T01, но real integration PASS требует реальных GitLab/IdP/PostgreSQL/CI/hoster по области проверки.

### 6.3. Блокеры, которые нельзя «распараллелить»

Исходные T00 blockers сохранены для traceability и помечены RESOLVED с датой/scope; они не являются текущими открытыми G0 blockers. Оставшиеся UNKNOWN/BLOCKED относятся к конкретным последующим tasks.

| Блокер | Что именно останавливает | Условие снятия |
|---|---|---|
| ~~Нет pinned baseline и реальных code paths~~ **RESOLVED for G0** | Было: implementation и выбор repo conventions | [baseline.md](baseline.md) содержит commit/tag, versions, toolchain, commands, migrations/seams; product implementation остаётся по dependencies |
| ~~GitLab capabilities UNKNOWN~~ **RESOLVED for G0** | Было: G0 stop | 42 synthetic real-sandbox probes записаны; target CAS/Owner limits приняты с controls. Product merge/cutover/export integration остаётся будущей проверкой |
| ~~Open WebUI seams UNKNOWN~~ **RESOLVED for G0** | Было: integration/upgrade plan stop | Pinned checkout, code-path/seam audits и Notes/chats regression scope записаны; implementation seam registry и browser checks остаются |
| ~~Identity/DB/CI capabilities UNKNOWN~~ **RESOLVED for G0** | Было: schema/security/pointer/recovery stop | Keycloak/OpenLDAP/PostgreSQL/CI synthetic evidence записано; production AD/live revocation и product pointer/recovery checks остаются |
| ~~Editor и retrieval benchmark отсутствуют~~ **RESOLVED for G0** | Было: G0 component choices | Headless editor/ACL-aware benchmark выполнен; TipTap selected G0-D8, pgvector validated candidate. T04 browser и production parameters остаются отдельными follow-up |
| ~~Owner G0 approval отсутствует~~ **RESOLVED 2026-11-08** | Было: старт T01–T20 | [g0-review.md](g0-review.md) APPROVED по baseline и всему ADR/design package; self-approval не использовалось. Implementation ждёт dependencies/readiness PASS |
| hoster.ai real endpoint отсутствует | T11 и G2 inference evidence | Согласованный endpoint/config/credentials/egress; иначе T11 BLOCKED |
| Corpus/source/connector decisions отсутствуют | Production load, T16, соответствующие части G2/G3 | Owner-approved perimeter/corpus/source objects/auth/sandbox; production corpus до этого запрещён |

## 7. Предлагаемые вертикальные срезы для последующего planning

Это **варианты упаковки существующих T/E**, не созданные stories и не последовательность с датами. Каждый срез включает backend/UI/tests в необходимом объёме и не закрывает gate частичным UI или mock.

| Вертикальный результат | Существующие IDs и acceptance | Зависимости / выход |
|---|---|---|
| Доказать feasibility и получить право на implementation | E00/T00; baseline mapping всех R/I/A, особенно A24/A34 | **DONE/APPROVED 2026-11-08:** `baseline.md`, capability matrix, TipTap/retrieval evidence, [test-plan.md](test-plan.md), G1 proposal и owner G0 record; дальше только dependencies/readiness PASS |
| Проверять contracts на двух изолированных Spaces до основной реализации | E01/T01 + начальный T14; A21,A33, [projection-mapping.md](contracts/projection-mapping.md), CF-01–CF-30 и fixture vectors для всех A | После G0; closed v2 schemas, explicit canonical↔projection roundtrips, two repositories/two Spaces с independent bindings, semantic/consumer/fault/concurrency/crash harness, real sandbox wiring |
| Пройти дерево → stable document → authorized read с двумя ACL perimeter | E02/T02,T03; A01,A04,A24–A26,A32,A33 | После T01; front matter/policies/identity fixtures и negative disclosure/schema-writer checks |
| Сохранить одну страницу, увидеть историю и конфликт без потери текста | E03/T04; A08–A10 | После T03; draft branch, exact revisions, restart/revert-MR, explicit conflicts |
| Пройти manual edit → MR → review → DecisionRecord → GO merge → restore | E04/T05–T08 + необходимый T06 + T07b correction contract; A05–A10,A17,A27–A30,A34,A36; G1 | После T04; business approver без GitLab user, exact parent/trailers/note/tag, no bypass, race/crash/recovery green; correction task только operational record |
| Добавить bounded single-page agent proposal без расширения полномочий | E04/T09 + G1-профиль T11; A02,A04,A05,A17,A18,A21 | После T06+T08; read/search/propose only, trusted run/principals, unsupported operations denied; real inference по доступности |
| Построить published-only index и выдать current canonical answer/citations | E05/T10 + T14; A02,A03,A11,A12,A21,A22,A25,A35 | После T03+T04; preflight non-serving, full/incremental equivalence, late-job/webhook/ACL/stale guards |
| Перенести synthetic corpus через controlled cutover и доказать portability | E06/T12,T13 + минимальный T15; A13,A15,A23,A31,A35,A36 | T12a dry-run отдельно после T03+T04; полный T12/T12b после T05 с T10 artifacts; dry-run → unpublished load → freeze/protection/preflight/activation → clone+manifests и отдельный correction backup/restore с linked-MR reconciliation |
| Провести internal pilot на согласованном corpus и approved hoster.ai | E07/T11,T14 + необходимый T18; A03,A16,A18,A20,A21; G2 | После E04–E06; real endpoint, expert questions, quality dimensions отдельно, deterministic P0 suite и runbook evidence |
| Подключить один источник и повторить dedicated delivery | E08/T15,T16,T18 + условный T17; A14–A16,A19,A20,A23,A28,A33; G3 | После G2 и owner source selection; no auto-merge, source cursor/crash evidence, second isolated instance, restore/upgrade rehearsal; full T18/G3 явно после T16 и включает correction restore/linked-MR reconciliation |
| Изменить retrieval/performance/trust только по измерениям | T19,T20; G4 | После T14/T18 и benchmark/business gate; не относить к E00–E08 и не создавать stack expansion заранее |

## 8. Requirement / component / contract / test ownership

Ownership ниже логический. При декомпозиции каждая story получает одного accountable component owner; QA владеет независимой проверкой, а владелец продукта — gate decisions. Наличие design owner не означает выполненную реализацию.

| Область | Requirements/invariants | Component и contract owner | Test/evidence owner |
|---|---|---|---|
| Canonical documents/UI | R01–R03,R07–R10,R13; I05,I13,I14 | Open WebUI + GO; front matter, Proposal/Decision, [correction-task](contracts/docops-correction-api.md), OpenAPI, GitLab protocol | UI/GO owners дают fixtures; QA проверяет A01,A02,A05–A10,A21–A23,A27–A30,A34 и correction CF-06/10/20/25; business approver выполняет UX acceptance |
| Identity, ACL и execution boundary | R05,R15,R16; I03,I04,I06,I09,I12 | Identity/AuthZ + GO + Open WebUI; access/approval/AuthzContext/tools/events | Security/QA: A04,A11,A17,A18,A22,A24–A26,A30,A32,A33,A36; real IdP/GitLab evidence |
| Merge, recovery и cutover | R06–R12,R14; I01,I02,I05–I08,I10,I14 | GO + GitLab/CI/Identity; DecisionRecord, recovery, CutoverRecord, export | GO/QA fault injection: A05–A10,A27–A31,A34–A36; real sandbox, не mocks |
| Retrieval/index/inference | R03,R04,R11,R15,R18; I08–I13 | CI/index single writer + retrieval read-only + managed model connections; index snapshot/events/inference | Retrieval/ML/QA: A02,A03,A11,A12,A16,A21,A22,A25,A35 и ACL-aware benchmark/golden set |
| Import/sources/assets/portability | R02,R12–R14,R16–R18; I01,I02,I08–I13 | Ingestion + GO + object storage/export; origin/front matter/import/export/events | Ingestion/source owners/QA: A13–A16,A22,A23,A27,A31,A32,A35,A36; sanitized quality/loss/closure reports |
| Schema/operations/client delivery | R14,R17,R18; I07,I09–I13,I14 | Component schema owners + DevOps; database catalog, backup/restore/upgrade/seam registry | DevOps/QA: A15,A19,A20,A28,A33; negative DB roles, second client, restore/upgrade drills |
| Cross-cutting regression | R18 и все R/I через связанные A | QA + все component owners; A01–A36 и machine contracts | QA владеет harness/traceability; component owner не отмечает собственный review; owner утверждает quality thresholds и gates |

DB writers не делятся между workstreams: upstream → Open WebUI upstream; managed grants/`kb_authz` → Identity/AuthZ; `kb_ops` → GO; `kb_index`/active pointer → CI/index workers; retrieval read-only. Тестирование не получает обходных writer credentials.

## 9. Definition of Ready

### 9.1. Ready for epic decomposition — доступно сейчас

Будущая story candidate должна сохранить:

1. существующие E/T IDs, пользовательский результат и R/I/A IDs;
2. ссылки на AD/ADR, component и versioned machine contract;
3. границы scope/non-goals, dependencies и внешние UNKNOWN;
4. positive/negative/concurrency/crash checks там, где применимо;
5. fixtures/environment и способ получения real evidence;
6. security/data profile, secrets handling, rollback/upgrade impact и evidence template.

Для этого уровня достаточно текущего DESIGN package. Он не является разрешением на код.

### 9.2. Ready for implementation — только после разблокировки

Дополнительно обязательны:

- явный owner G0 approval и завершённый T00 по фактическим критериям;
- pinned baseline, реальные code references, reproducible environment и repo-specific commands;
- подтверждённые либо пересмотренные через ADR required capabilities; stop conditions не скрыты;
- выбранные по evidence редактор/backend/config там, где они нужны именно этой story;
- reviewed contract version и готовые T01 fixtures/harness по зависимостям;
- доступные real sandbox/integration resources или явный BLOCKED без подмены mocks;
- owner decisions, необходимые именно для scope story, и отсутствие незакрытых prerequisite tasks.

## 10. Definition of Done и состояния

Используются только состояния **TODO → IN_PROGRESS → VERIFIED → DONE**, с отдельным **BLOCKED**. DESIGN-наличие документа не переводит задачу в VERIFIED.

Story/task DONE требует одновременно:

- заявленный пользовательский результат и все связанные A criteria выполнены;
- positive, negative, anti-enumeration, concurrency и crash/recovery tests по scope реально запущены и зелёные;
- canonical exact base/proposal, Decision note+tag/hash, real merge parents/trailers и no-direct-push/merge проверены там, где применимо;
- repository=Space, schema single-writer, preflight non-serving, dependency closure и decisions/assets export closure проверены там, где применимо;
- отчёт содержит baseline, environment, команды, результаты, blocked checks и sanitized evidence;
- code review и требуемый human/security/owner review завершены независимыми лицами;
- contracts/ADR/operations/traceability обновлены; rollback и upstream upgrade impact указаны;
- нет critical regression, secrets, реальных клиентских документов или unredacted personal data в repo/logs/evidence;
- mocked integration не выдана за real PASS; отсутствующая обязательная проверка остаётся BLOCKED.

## 11. Story evidence template

```text
Story candidate / existing Epic ID / existing Task ID:
User outcome and scope / explicit non-goals:
Requirements R / invariants I / acceptance A:
AD / ADR / component / contract versions:
Dependencies and external blockers:
Open WebUI commit/tag / GitLab version+edition / toolchain:
Reused upstream or GitLab capability with real code reference:
Changed modules / migrations / seam-registry entries:
Fixtures (two Spaces, principals, source modes, malicious cases):
Environment (local / real sandbox / dedicated test client):
Positive tests: commands → results → evidence:
Negative / concurrency / crash-recovery tests: commands → results → evidence:
Real GitLab / IdP / PostgreSQL / CI / hoster checks and outcomes:
Blocked checks / reason / owner of unblock condition:
Canonical evidence (base/proposal/decision/note/tag/parents/trailers):
ACL / cross-Space / schema-writer / preflight / export closure evidence:
Security, privacy, data-profile and secrets review:
Rollback / restore / upstream upgrade / license-SBOM impact:
Sanitized evidence links (machine output separately from review evidence):
Independent code review / required owner review record:
State: TODO | IN_PROGRESS | VERIFIED | DONE | BLOCKED
Next dependency or remaining work:
```

Machine-generated reports размещаются в `_bmad-output/test-artifacts`; в `specs/corporate-kb/evidence` попадают только sanitized reviewable extracts. Секреты и raw private payloads в evidence не включаются.

## 12. Fixture и environment needs

### 12.1. Synthetic fixtures

- **Два отдельных repositories = два Spaces** с разными ACL, включая изолированный pricing; отдельные refs/history/index/export/backup, independent per-Space policy bundles/access+approval revisions/group snapshots/revocation epochs/active snapshot profiles и отсутствие cross-Space caches или borrowed cursor bindings.
- Readers, authors, source owners, business approvers без GitLab users, engineering owners/CODEOWNERS, space/instance admins; trusted service/agent/connector/CI identities с разными scopes.
- Stable AD/OpenLDAP/OIDC identities, nested groups, issuer variation, joiner/mover/leaver, login/email rename и все три self-approval collisions: author/version-author/requester.
- Nested Markdown с Cyrillic paths, same basename, stable UUID rename/move, repeated headings, long pages, bounds/cursors, ID links, duplicate IDs/cycles/orphans и ambiguous patches.
- Immutable attachment versions/hashes и media classes: decorative/illustrative/substantive/critical/handwritten; verified/pending/rejected states, missing/mutable/mismatched assets.
- `migrated/source_managed/curated/live_operational`, previous imported base/current curated/incoming source, no-op/deletion/tombstone, concurrent workers и seen/proposed/merged crash points.
- Exact base/proposal/merge fixtures: accept/reject/cancel, note+tag corruption, supersedes, stale base, new commit/rebase, two clients/two MRs, target race, lock loss/fencing, response lost, crash до/после external call, DB loss/quarantine; invalid+unknown со second-MR denial, conclusive failed guarded same-decision/new-attempt retry и terminal conflicted/invalid tuple assertions.
- Index full/incremental/preflight fixtures: links/assets/policy dependencies включая approval revision, late generation, history rewrite, lost/duplicate/out-of-order webhook, CI outage, stale candidate и simultaneous old/new publication на одном Space/profile; separate preflight/published request/run/snapshot IDs с одинаковыми SHA/closure/hashes и pointer→Space activation.
- Malicious imports/preview: archive traversal, absolute/Unicode ambiguous paths, symlinks, executable HTML/MDX/XSS, `.git`/`.env`/secret-like files, oversized/decompression bombs и invalid UTF-8.
- Export/restore: explicit refs, peeled annotated tags, MR note metadata, parents/trailers, policy/grants mapping, export-v2 accepted-before-merge/rejected/cancelled/failed/conflicted/invalid outcomes+attempt+recovery, decisions/assets/authorization closure и missing/rejected objects без fabricated hashes; отдельный non-Git-derived correction-task current/events/evidence/idempotency backup с restore и linked-MR reconciliation без fabrication/deletion и второго canonical write path; второй synthetic client с независимыми resources.

### 12.2. Environments

| Environment | Назначение | Обязательные ограничения |
|---|---|---|
| Local/T00 | Read-only upstream audit, synthetic editor/backend spikes, contract design | Без product migrations, production corpus, реальных secrets/documents, платных/неутверждённых вызовов |
| Real integration sandbox | GitLab + PostgreSQL + CI + IdP и synthetic repositories | Scoped credentials, отдельные projects/groups, deterministic negative/concurrency/fault tests; mock не заменяет PASS |
| Approved inference sandbox | T11/T14/T17 streaming/tools/extraction/embeddings/OCR | Согласованные hoster.ai endpoint/config/egress/inventory; без credentials — BLOCKED |
| Connector sandbox | T16 update/revoke/delete/retry/attachments | Owner-selected source objects/auth/edition и synthetic/sanitized data |
| Clean restore / second client | T13/T18 portability и repeatability | Независимые repos/DB/index/objects/secrets/backups/egress; config-only delivery, не client code branch |

Production corpus до согласования perimeter/source corpus и отдельного разрешения не создаётся. Real client documents, private endpoints и unredacted personal data не используются в workspace/evidence.

## 13. Release gates G0–G4

| Gate | Требуемый доказанный результат | Что не засчитывается как exit evidence |
|---|---|---|
| **G0** | Pinned baseline; required GitLab/identity/DB capabilities подтверждены или stop/BLOCKED; весь ADR-03–16/design package явно reviewed/approved владельцем | DESIGN package, ADR-файлы, contract mappings и документное review без baseline/capability/owner record |
| **G1** | Одна страница, два пользователя: manual edit→MR→ProposalRecord→review→DecisionRecord→GO real merge→restore; owner без GitLab user; self-approval/direct merge невозможны; parents/trailers/race/crash/recovery/bypass green | UI/mock без real GitLab, race/crash и no-bypass evidence |
| **G2** | Согласованный corpus продаж с repository-per-Space ACL, controlled cutover/preflight→published pair/activation, retrieval/index/import/full export, real hoster endpoint, P0 suite и business review | Preflight activation, production corpus без perimeter/sign-off, mocked hoster или incomplete export |
| **G3** | Один external source без auto-merge, second dedicated instance, schema ownership, decisions/assets/metadata backup restore плюс отдельный correction backup/restore и linked-MR reconciliation, operational/security acceptance; full T18/G3 после T16 | Наличие runbook без connector/second-instance/restore drills или заявка full T18 без T16 |
| **G4** | Клиентские profile optimizations только после измерений и business gate | Ранняя замена stack или численные targets без benchmark/owner decision |

Фактические gate/task states и blockers находятся только в [tasks.md](tasks.md). Gate закрывается явной записью владельца и доказательствами, а не окончанием спринта или наличием артефакта.

## 14. T00 spikes и остаток доказательной работы

| Spike внутри T00 | Что проверить и записать | Блокирует |
|---|---|---|
| Baseline/reproducibility | Pin Open WebUI/GitLab/PostgreSQL/toolchain/Git object format; checkout, real code refs, dev/test/lint/typecheck commands, migrations; `baseline.md` | G0 и весь implementation |
| Open WebUI seams | auth/users/grants/LDAP/OIDC/JIT/sessions/CSRF/tools/all channels/RAG/model connections/streaming; Notes/chats regression и seam registry | G0, T03/T06–T11, upgrade plan |
| GitLab critical capabilities | Exact-SHA reads/merge/conflicts, real parents/trailers, no squash/rebase/FF, MR note ID/body/audit/mutation/export, protected annotated tags, merge-only-GO, scoped tokens, webhooks/audit | G0/G1/G2; возможный STOP/design review |
| Cutover/repository provisioning | Synthetic two Spaces, unpublished controlled bulk, freeze/HEAD/protections/inactive preflight→separate same-SHA published request/run/snapshot→per-Space/profile CAS pointer→activation, naming/group layout proposal | G0, T12/T13/G2; production corpus не создавать |
| Identity/revocation | objectGUID/entryUUID/issuer-sub, nested groups, read-only encrypted bind, empty-password/CVE-2026-44551, JIT, independent per-Space authz-v2 bindings/fresh recheck, mover/leaver, live subscriptions, ≤15/≤30 requirements | G0, T03/G1, retrieval/export |
| DB ownership/recovery | Upstream physical schemas/migrations/grant seams, one-instance feasibility, separate roles/writers, full-perimeter FK, advisory lock/fencing, target-wide invalid/unknown preservation и guarded failed retry, conservative rebuild | G0, T01/T03/T05/T18/G3 |
| Editor comparison | Готовый component: front-matter-v2 round-trip, complete diff/preview, Cyrillic, links/attachments/valid_until/archive/origin, XSS, keyboard/accessibility, license | G0 и T07/T08; не строить собственный без ADR |
| Retrieval/index audit и benchmark | Existing backend, exact+semantic per-Space fan-out, SHA/document mapping, ancestry/profile/closure+approval evidence, preflight/published pair и cross-generation pointer CAS, ACL-aware Russian recall, model/dimensions/chunking candidates | G0 engine choices, T10/T19; pgvector/ANN не выбирать заранее |
| Packaging/license/CI | Open WebUI notices/branding, GitLab edition/CODEOWNERS limits, core/plugins/models/dependencies license/SBOM, CI transport/offline assets | G0/commercial delivery и T18 |
| Acceptance design | Проверить [test-plan.md](test-plan.md), [traceability.md](traceability.md), projection mappings и CF-01–CF-30 на текущем spec v1.3; подготовить proposed first G1 vertical slice | G0 и последующий T01; A/CF-сценарии и coverage согласованы как DESIGN, но не являются executed evidence |
| Inference/source inventory | Hoster/model IDs/dependencies/egress/offline assets как UNKNOWN/config proposal; первый connector/source formats/object-store questions | T11/T16–T18/G2/G3; не объявлять mocked PASS |
| Owner review package | Capability matrix, sanitized baseline smoke, risks/UNKNOWN/DEFERRED, stop conditions, explicit owner G0 review record | Старт T01–T20 |

## 15. Открытые owner decisions и уже закрытые принципы

### 15.1. Не переоткрывать

Git-native канон; repository=Space; merge-only-GO и запрет direct human/bot/CI merge/auto-merge; business approval без GitLab users через `approval-policy.yaml`; CODEOWNERS только engineering; canonical DecisionRecord note+tag; exact-SHA parentage/trailers и per-target recovery; controlled two-phase cutover; single-writer schemas; clone+decisions/assets manifests; group refresh ≤15 минут и revocation SLO ≤30 минут. ADR-01/02 withdrawn.

### 15.2. Решения, необходимые для G0 после evidence

- Явно утвердить baseline и весь ADR/design package либо зафиксировать BLOCKED/stop и требуемый ADR пересмотр.
- По результатам аудита утвердить Open WebUI/GitLab versions+edition/toolchain, repository-compatible deployment approach, editor и retrieval/backend parameters.
- Утвердить repository naming/group layout/provisioning proposal без изменения правила 1:1.
- Принять capability/stop decisions по любым недоступным required GitLab/identity/DB/CI semantics.

### 15.3. Решения для последующих gates, не повод выдумывать значения сейчас

- Source corpus и repository perimeter по ACL, source owners, business approver groups/path scopes и engineering CODEOWNERS.
- Data profile/legal basis, approved hoster endpoints/model IDs/dimensions/provider inventory/egress/offline assets.
- Первый connector (SharePoint/Bitrix24/Kayako), exact objects/auth/edition/API constraints, supported formats и object-store layout.
- Corpus/profile/concurrency, p95/p99, TTFT/full response, freshness/queue lag, quality thresholds, workloads и budgets.
- RPO/RTO, retention по branches/MR/notes/tags/audit/chats/files/object versions/mirrors/backups и idempotency replay retention.
- Session/context TTL и operational retry/backoff/resource limits без ослабления revocation barrier.
- Commercial distribution/branding/license/SBOM/legal review и любые deferred capabilities через новый ADR.

## 16. Известные пробелы и ограничения пакета

1. **`baseline.md` и pinned versions записаны** ([baseline.md](baseline.md), [evidence/t00](evidence/t00/README.md)), но это synthetic sandbox evidence: production readiness не заявляется; CI Runner exact-SHA/no-write PASS 7/7, browser editor checks остаются BLOCKED.
2. **`test-plan.md`, operations и T01 catalog существуют только как DESIGN; executed acceptance/contract evidence отсутствует.** Полные A01–A36 и fault matrix сохранены; дублирующие R/I indexes удалены, нормативная coverage — [traceability.md](traceability.md). CF-01–CF-30 и canonical↔projection mappings подготовлены, но не запущены.
3. **G0-D12 APPROVED.** [g0-review.md](g0-review.md) APPROVED: baseline и ADR/design package приняты для epic planning; deferred gates остаются обязательными.
4. **Нет реальных product integration PASS.** GitLab/IdP/DB/retrieval evidence — synthetic sandbox capability checks, не A01–A36 execution; все A/CF имеют уровень DESIGN, не VERIFIED.
5. **TipTap adapter selected и owner-approved (G0-D8); canonical adapter/browser work остаётся T04.** Realtime CRDT вне MVP. Final retrieval parameters, models, source и object-store не выбраны; pgvector — validated candidate с owner-TBD thresholds. Нельзя превращать candidates в production architecture facts при декомпозиции.
6. **T20 не имеет явной строки Requirements в spec.md v1.3.** Любые R mappings для T20 являются design-derived и должны быть подтверждены при последующем planning; T19/T20 не входят в E00–E08.
7. **Подготовленные projection/state mappings — DESIGN output, не VERIFIED test.** [projection-mapping.md](contracts/projection-mapping.md) уже фиксирует Decision/Cutover/Proposal/index/source/AuthZ/path mappings; [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml) задаёт будущие consumer roundtrips и negatives. Их наличие не доказывает реализацию.
8. **`operations.md` существует как `design_not_executed`.** Он включён в G0 design review; T18 restore/upgrade/startup rehearsals и production readiness не выполнялись.
9. **Оценки даны как LOW/VERY LOW confidence сценарии, не commitments.** [delivery-estimates.md](delivery-estimates.md) фиксирует capacity assumption 24 person-days/sprint, ranges и риски; реальные capacity, даты и velocity не назначаются.
