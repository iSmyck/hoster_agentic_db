# Corporate KB implementation tracker

## 1. Active gate и фактические статусы

**G0 — OPEN. T00 — IN_PROGRESS. Owner G0 approval — отсутствует.** Разрешены только T00 baseline audit и G0 design review; product implementation, migrations, dependency upgrades, production corpus и mass formatting не разрешены. Правила фазы: [AGENTS.md](../../AGENTS.md).

- **T00 IN_PROGRESS:** design part и документная синхронизация подготовлены; pinned baseline, real capability checks, editor/backend proposals, owner-facing design review [test-plan.md](test-plan.md)/operations/T01 vectors, sanitized evidence и owner approval остаются.
- **T01–T20 TODO:** зависимости перечислены ниже; TODO не означает разрешение начать реализацию до G0.
- **Ни одна задача не VERIFIED и не DONE.** A01–A36 не запускались; integration PASS, migrations, restore/upgrade rehearsal и production readiness отсутствуют.
- Состояния задач используются строго: **TODO → IN_PROGRESS → VERIFIED → DONE**, отдельно **BLOCKED**. Наличие DESIGN-документа не является VERIFIED. Недоступная обязательная real check помечается BLOCKED в соответствующем evidence, а не заменяется mock/PASS.
- Нормативные источники: [spec.md v1.3](spec.md), [Architecture Spine](architecture-spine.md), [ADR index](adr/README.md). Planning coverage: [planning-input.md](planning-input.md), [traceability.md](traceability.md).

## 2. Живой tracker T00–T20

Dependencies сохранены из spec v1.3; G0 является дополнительным внешним gate для всего implementation. E00–E08 не переименованы; T19/T20 не включены в них искусственно.

| ID | Состояние | Depends / gate | Requirements | Существующий Epic | Фактический остаток / следующий evidence |
|---|---|---|---|---|---|
| **T00** | **IN_PROGRESS** | Нет task dependency; owner G0 после evidence | R01–R18 | E00 | Design inputs и документная синхронизация подготовлены; нужны `baseline.md`, real code refs/capability matrix/smoke, editor и retrieval proposals, design review [test-plan.md](test-plan.md)/operations/T01 vectors, minimal G1 proposal, sanitized evidence и явный owner G0 review |
| T01 | TODO | T00 + G0 | R18 | E01 | [Projection mappings](contracts/projection-mapping.md) и [CF-01–CF-30](contracts/t01-contract-tests.yaml) подготовлены как **DESIGN output**; после G0 выполнить versioned compatibility, deterministic serialization/hash, semantic/consumer/projection roundtrips, synthetic fault matrix и real sandbox/test harness; никакие conformance tests не выполнены |
| T02 | TODO | T00,T01 + G0 | R01,R02 | E02 | Spaces/documents mapping, two repositories/two Spaces, closed front-matter-v2/read/navigation; A01,A32 |
| T03 | TODO | T02 + G0 | R05,R16 | E02 | Real upstream auth/grants seams, stable identity/nested groups, versioned per-Space access+approval bundle, revocation; A04,A11,A18,A22,A24,A25,A26,A30,A31,A32,A33,A36 |
| T04 | TODO | T03 + G0 | R09,R10 | E03 | Ready editor adapter, draft/save/conflict/history/revert-MR exact revisions; A08,A10 |
| T05 | TODO | T04 + G0 | R06–R10 | E04 | MR+ProposalRecord, canonical DecisionRecord note+tag, real GO merge, target-wide barriers/fencing/reconciliation, conclusive failed guarded retry vs terminal conflicted/invalid; A05–A10,A27–A30,A34,A36 |
| T06 | TODO | T05 + G0; можно параллельно T07 | R05–R08,R16 | E04 | GitLab+GO enforcement всех direct human/bot/CI/engineering/source bypass; A04,A05,A09,A17,A18,A28,A29,A34 |
| T07 | TODO | T05 + G0; можно параллельно T06 | R07,R08 | E04 | Platform review для business без GitLab users, full preview/evidence/restore, decision races; A06,A07,A22,A23,A27,A30 |
| T08 | TODO | T02,T03,T07 + G0 | R01–R03 | E04 | Tree/direct read/WYSIWYG/front matter/review/revision UX, editor selection evidence; A01 |
| T09 | TODO | T06,T08 + G0 | R03,R06,R07 | E04 | Bounded read/search/propose tools, trusted run/principals, read-only credential boundary; A02,A21 |
| T10 | TODO | T04,T03 + G0; параллельно T05–T09/T12 | R04,R11 | E05 | Audited backend, CI/index writers, independent full/incremental closure proof, separate same-SHA preflight→published pair, per-Space/profile fence/CAS pointer across generations, per-Space fan-out/read-only retrieval; A02,A03,A11,A12,A21,A22,A25,A31,A32,A35 |
| T11 | TODO | T09 + G0; ранняя config-first проверка после G0 | R15,R18 | E04 G1 profile + E07 | Approved hoster.ai studio model connections/streaming/tools/no-fallback; real endpoint/credentials/egress — обязательный blocker, mock не PASS; A16 |
| T12 | TODO | T03,T04 + G0; параллельно T05/T10 | R12,R13 | E06 | Dry-run/immutable manifests/data barrier/provenance и unpublished load→freeze/protection/preflight/activation; production corpus запрещён; A13,A23,A31,A35 |
| T13 | TODO | T12 + G0 | R14 | E06 | Full export-v2 clone+decisions/assets manifests с explicit outcomes/recovery и decisions/assets/authorization closure, mirror/metadata backup, clean restore и conservative rebuild; A11,A15,A25,A27,A32,A36 |
| T14 | TODO | T01,T09,T10,T11 + G0 | R18 | E01 initial + E05 checks + E07 acceptance | Synthetic golden/negative/concurrency/crash suites и expert Russian set; thresholds не выдумывать; A03,A18,A20,A21 |
| T15 | TODO | T12,T05,T10 + G0 | R13 | E06 minimal + E08 full | Registry/cursors/three-way/no-op/tombstone/one outstanding; human decision+GO merge, без auto-merge; A14 |
| T16 | TODO | T15,T03 + G0 и owner source selection | R12,R13,R16 | E08 | Один SharePoint/Bitrix24/Kayako connector после выбора; real sandbox update/revoke/delete/retry/assets; A14 |
| T17 | TODO | T12 + G0; conditional по реальным форматам | R12,R18 | E08 conditional | Форматные golden/loss/media/scan/OCR fixtures и approved extraction inference; real corpus отдельно авторизуется; A16,A23 |
| T18 | TODO | P0 safety gates,T13 + соответствующие release gates | R14,R17,R18 | E07 necessary part + E08 operations | Repeatable dedicated deploy, second isolated client, secrets/egress/observability, backup/restore/upgrade/SBOM/seam registry/runbooks; A15,A19,A20,A28,A33 |
| T19 | TODO | T14 + measured benchmark/business gate | R04,R11,R18 | Отдельный deferred epic после E08; ID не создан | Engine evolution только по ACL-aware benchmark; ранняя замена stack запрещена; отдельные A в spec не назначены |
| T20 | TODO | T14,T18 + measured/business gate | **В spec v1.3 не указаны** | Отдельный deferred epic после E08; ID не создан | Fast/Trust/Scale policies; R/I/A mapping подтвердить при будущем planning, не назначать thresholds/capacity заранее |

## 3. Готовые design inputs — не implementation completion

| Артефакт | Готовая часть | Статус / оставшееся |
|---|---|---|
| [spec.md v1.3](spec.md) | R01–R18, I01–I14, A01–A36, T00–T20, E00–E08, gates и протоколы | Нормативный proposed spec; не baseline, не executed acceptance |
| [ARCHITECTURE-SPINE.md](architecture-spine.md) | AD-1–AD-16, component/capability map, deferred/consistency conventions | DESIGN; требуется сверка с pinned checkout |
| [architecture.md](architecture.md) | Containers, responsibility/credential/state matrix, lifecycle/recovery/NFR, фактическая ADR/contracts navigation | DESIGN DRAFT для G0; real code refs и owner review отсутствуют |
| [open-webui-fork.md](components/open-webui-fork.md) | UI/review/editor/agent seams, Notes/chats regression | DESIGN; commit/code paths/editor/test commands UNKNOWN |
| [git-orchestrator.md](components/git-orchestrator.md) | Proposal/decision/merge/recovery/cutover/export | DESIGN; GitLab version/edition/capabilities UNKNOWN |
| [identity-access.md](components/identity-access.md) | Stable identity/policies/grants/AuthzContext/revocation | DESIGN; real IdP/upstream verification отсутствует |
| [retrieval-indexing.md](components/retrieval-indexing.md) | Generation/profile/closure/preflight/pointer/query design | DESIGN; backend/model/dimensions/benchmark UNKNOWN |
| [ingestion-connectors.md](components/ingestion-connectors.md) | Import/data barrier/source modes/cursors/assets/media | DESIGN; connector/formats/object-store UNKNOWN |
| [ADR-03–ADR-16](adr/README.md) | Все обязательные ADR-файлы, Accepted/Proposed/stop conditions и verification links | DESIGN/Accepted per individual ADR; **не общий owner G0 approval** |
| [database.md](database.md) + [database-catalog.yaml](contracts/database-catalog.yaml) | Single-writer ownership, logical tables, transactions/rebuild, DB assertions | DESIGN; не DDL/migrations; single instance и physical upstream layout не подтверждены |
| [integration.md](integration.md) + [contracts/README.md](contracts/README.md) | API/tools/events/error/idempotency/integration protocols | PROPOSED; T01 validation/compatibility и real integration tests не выполнены |
| [JSON/OpenAPI/YAML machine contracts](contracts/README.md#2-карта-артефактов) | Front-matter-v2/policies/Authz-v2/Proposal/Decision/index/Export-v2/origin/DocOps/API/tools/events | PROPOSED; fixture execution не выполнялось |
| [projection-mapping.md](contracts/projection-mapping.md) + [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml) | Подготовленные canonical↔API↔event↔DB state/enum/ID/path mappings и CF-01–CF-30 consumer vectors | **DESIGN output / DESIGN_NOT_EXECUTED**, не VERIFIED test и не implementation completion |
| [content-standard.md](content-standard.md) | ETL/controlled publication/DocOps синхронизированы с v1.3 | Process DESIGN 2.3; не разрешение corpus load |
| [operations.md](operations.md) | Deployment/startup/cutover/recovery/export/restore/upgrade runbooks | `design_not_executed`; T18 rehearsals и production readiness не подтверждены |
| [test-plan.md](test-plan.md) | Test levels, fixtures, полный A01–A36 catalog, CF links и crash matrix; R/I navigation в traceability | `design_not_executed`; owner design review остаётся, duplicate R/I indexes удалены |
| [planning-input.md](planning-input.md) | Вход для будущей декомпозиции, dependencies/slices/DoR/DoD/fixtures/gates/spikes | READY FOR EPIC DECOMPOSITION только; не implementation approval |
| [traceability.md](traceability.md) | Полные R/I/A/T/E matrices и machine-contract links | DESIGN coverage; не test plan и не executed test report |

`baseline.md` намеренно не создан без фактического аудита. [test-plan.md](test-plan.md) и [operations.md](operations.md) существуют как `design_not_executed`; полные A01–A36/fault matrix и runbooks включены в T00 design review, но не выполнялись. Отдельный `sprint-status.yaml` не создавался; sprint tracking относится к будущему planning после разрешения. Этот `tasks.md` — единственный live tracker динамических статусов.

## 4. Выполненная design part T00

Отметки ниже означают только создание/сверку документов, не выполнение T00 acceptance:

- [x] Синхронизированы normative decisions spec v1.3 и Architecture Spine.
- [x] Подготовлены architecture/component design drafts для пяти логических компонентов; ADR/contracts/operations navigation приведена к фактическим файлам.
- [x] Оформлены ADR-03–ADR-16; ADR-01/02 остаются withdrawn.
- [x] Подготовлены logical database design/catalog с ownership, full-perimeter associations, rebuild и retention UNKNOWN.
- [x] Подготовлены integration protocols и PROPOSED machine contracts, включая authz/front-matter/export/agent-tools v2.
- [x] Подготовлены [projection-mapping.md](contracts/projection-mapping.md) и [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml) CF-01–CF-30 как **DESIGN output**, не VERIFIED test.
- [x] [test-plan.md](test-plan.md) сохранён как `design_not_executed`; A01–A36 и fault matrix сверены, дублирующий R/I-index удалён в пользу traceability без отметки сценариев выполненными.
- [x] Подготовлены [operations.md](operations.md) как `design_not_executed`, planning-input и полная DESIGN traceability R01–R18/I01–I14/A01–A36/T00–T20/E00–E08/CF-01–CF-30.
- [x] Зафиксированы dependency/gate boundaries, fixture needs и будущие варианты вертикальных срезов без создания stories/сроков/оценок.

## 5. Оставшиеся обязательные T00 outputs

### 5.1. Baseline и реальные capabilities

- [ ] Выбрать и закрепить Open WebUI commit/tag, GitLab version/edition, PostgreSQL/toolchain/Git object format и upstream checkout; не угадывать версии.
- [ ] Записать в будущий `baseline.md` реальные code paths, dev/test environment, lint/test/typecheck commands, migrations/upgrade behavior и sanitized results.
- [ ] Проверить Open WebUI auth/users/grants/LDAP/OIDC/JIT/session/CSRF/tool/all-channel/RAG/model-connection seams, personal Notes/chats regression и DB migration ownership.
- [ ] На real sandbox GitLab проверить exact-SHA reads/merge/conflicts, no squash/rebase/FF, first parent=base/second parent=proposal, trailers, structured MR note ID/body/audit/mutation/export, protected annotated decision/cutover tags и refs.
- [ ] Доказать MR-only/merge-only-GO, запрет direct human/bot/engineering/CI merge, scoped proposal/CI/object/source credentials, webhook authenticity/replay и audit/metadata export.
- [ ] На synthetic unpublished repositories проверить controlled bulk exception, cutover freeze→exact HEAD→protections→inactive preflight→pointer/activation и отсутствие retrieval до activation.
- [ ] Проверить stable AD/OpenLDAP/OIDC IDs, nested groups/JIT/read-only encrypted bind/empty-password CVE-2026-44551, fresh group recheck, mover/leaver/live subscriptions и revocation requirements.
- [ ] Подтвердить отдельные upstream/`kb_authz`/`kb_ops`/`kb_index` roles/migrations и возможность выделенного PostgreSQL instance; иначе STOP/design review.
- [ ] Проверить GitLab CI exact-SHA read, CI without Git write, index/pointer ownership, object-store immutable versions и required clone/metadata/export capabilities.

### 5.2. Editor, retrieval, inference и packaging spikes

- [ ] Сравнить готовые web-редакторы по front matter round-trip, full diff/preview, Cyrillic/links/attachments/XSS/accessibility/license; не выбирать custom editor по умолчанию.
- [ ] Провести existing retrieval backend audit и ACL-aware Russian benchmark; SHA mapping, exact+semantic, generation/profile/closure/preflight/late job, model/dimensions/chunking и pgvector/ANN остаются UNKNOWN до evidence.
- [ ] Зафиксировать hoster.ai studio endpoints/model IDs/dependencies/egress/offline assets как configuration UNKNOWN; не объявлять integration без real endpoint.
- [ ] Зафиксировать Open WebUI branding/notices, GitLab edition/CODEOWNERS limitations и core/plugins/models/dependencies license/SBOM review.
- [ ] Предложить repository naming/group layout/provisioning без создания production repositories/corpus; определить первый connector/formats/object-store только как questions/candidates до owner decision.

### 5.3. Review, planning и evidence

- [ ] Завершить owner-facing design review обновлённых [test-plan.md](test-plan.md), [operations.md](operations.md), [traceability.md](traceability.md), [projection-mapping.md](contracts/projection-mapping.md) и [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml): сохранить two-Space fixtures, semantic/consumer negatives, concurrency/crash matrix, environments и explicit blocked real checks. Сами mappings/vectors уже подготовлены как DESIGN, не VERIFIED.
- [ ] Подготовить capability matrix, sanitized baseline smoke, риски/UNKNOWN/DEFERRED и предложенный минимальный G1 vertical slice; существующая traceability не заменяет этот output.
- [ ] Обновить ADR/design только по фактическим audit findings; Accepted invariants не переоткрывать без stop evidence, Proposed engine/editor/deployment details не выдавать за Accepted.
- [ ] Сохранить machine output в `_bmad-output/test-artifacts`, а sanitized reviewable evidence — в `specs/corporate-kb/evidence/t00`; реальные секреты/документы/PII не включать.
- [ ] Получить и записать **явный owner G0 review/approval по baseline и всему ADR/design package**. Self-approval и наличие файлов не засчитываются.

## 6. Design discrepancies: resolved at design-source level

| Прежняя проблема | Разрешение в v1.3/design package | Остаток |
|---|---|---|
| MR-only противоречил bulk import | **RESOLVED:** I01/I02 и [ADR-11](adr/ADR-011-two-phase-publication.md): controlled engineering bulk только в unpublished `main` при закрытом доступе/без published index; далее freeze/exact HEAD/protections/preflight/activation | Проверить на real GitLab в T00; production corpus не создавать |
| Auto-merge противоречил R06/R13 | **RESOLVED:** R06,R13,I02 и [ADR-04](adr/ADR-004-execution-capability-boundary.md), [ADR-11](adr/ADR-011-two-phase-publication.md): agent/connector/LLM/source-managed auto-merge запрещён, apply только GO после human decision | Проверить GitLab/GO bypass matrix |
| Разные ACL models | **RESOLVED:** R02,R05,I09 и [ADR-10](adr/ADR-010-ldap-oidc-identity.md), [ADR-16](adr/ADR-016-repository-per-space.md): repository=Space=ACL, path scopes только proposal/review/approval, front matter `access` не grant | Проверить nested groups/cross-Space/AuthZ freshness |
| Merge identity/approver mapping | **RESOLVED:** R05–R10 и [ADR-12](adr/ADR-012-business-approval-without-gitlab-users.md), [ADR-13](adr/ADR-013-merge-serialization-recovery.md), [ADR-14](adr/ADR-014-canonical-decision-record.md): external group/path policy, approver без GitLab user, stable principals, CODEOWNERS только engineering | Проверить real GitLab auth/notes/tags/merge parents/trailers |
| ADR-09 unknown и 25 vs 36 acceptance IDs | **RESOLVED:** [ADR-09](adr/ADR-009-platform-review-ux.md) существует и Accepted; [spec.md](spec.md) содержит A01–A36; [content-standard.md](content-standard.md) 2.3 синхронизирован | Editor/UX implementation и A01–A36 execution остаются |
| `architecture.md` §12.2–12.3 утверждал отсутствие ADR/contracts | **RESOLVED:** разделы ссылаются на фактические [ADR index](adr/README.md), [contracts README](contracts/README.md), integration/DB/operations/projection/T01 artifacts | Owner G0 review остаётся |
| Planning утверждал отсутствие `operations.md`, использовал несуществующую operational document table, неверные T02/T04 acceptance links и незакрытые state mappings | **RESOLVED:** [operations.md](operations.md) существует как DESIGN; R03 использует GO canonical read + kb_index; T02=A01,A32 и T04=A08,A10; [projection-mapping.md](contracts/projection-mapping.md) и CF-01–CF-30 подготовлены | T01 execution, T18 rehearsals и real integration evidence отсутствуют |
| Test-plan R/I duplicate indexes расходились со spec/traceability | **RESOLVED:** duplicate R/I-index удалён; полные A01–A36/fault matrix сохранены, [traceability.md](traceability.md) — единый R/I source; R04−A02, R05+A31, R11+A22, R18−A34 соответствуют spec | Owner design review и выполнение A/CF не выполнялись |

Эти записи не закрывают T00, G0 или owner/security approval. Они только устраняют старый normative drift и указывают на актуальные источники. Все prepared mappings/vectors остаются DESIGN output, не VERIFIED test.

## 7. Текущие блокеры и открытые решения

### Блокируют G0 / старт implementation

- Нет pinned versions, upstream checkout, `baseline.md`, real code refs и воспроизведённых commands.
- Нет real GitLab/Open WebUI/Identity/PostgreSQL/CI capability evidence; required unavailable capability должна стать BLOCKED/STOP, не предположением.
- Нет editor comparison и ACL-aware retrieval/backend benchmark; T00 design review не может превратить candidates в выбранные решения.
- [test-plan.md](test-plan.md), [operations.md](operations.md), projection mappings и T01 vectors требуют owner-facing design review; sanitized baseline/capability evidence, minimal G1 evidence-based proposal и явный owner G0 review record отсутствуют. Документный R/I sync завершён и не является blocker evidence.

### Блокируют конкретные последующие потоки, не повод скрывать их в TODO

- T11/G2: реальные hoster.ai endpoint/config/credentials/egress; без них T11 BLOCKED.
- T12 production load/G2: согласованные repository perimeter/source corpus/data profile/legal basis/source owners; production corpus запрещён до решения.
- T16/G3: выбранный connector/source objects/auth/edition/API/sandbox.
- T17: реальные synthetic/sanitized форматы и approved extraction/OCR assets.
- T18/G3: owner RPO/RTO/retention/resource decisions, second-client resources, clean backup/restore/upgrade rehearsal.
- T19/T20: измерения и business gate; отдельные будущие эпики и A mappings не созданы.

Owner decisions без выдуманных значений: business groups/path scopes/CODEOWNERS; hoster inventory/egress; corpus/concurrency/latency/freshness/quality/budgets; RPO/RTO/retention/idempotency replay/session limits; source connector/formats/object-store; commercial branding/license/SBOM. Уже утверждённые group refresh ≤15 минут и revocation SLO ≤30 минут не заменяются плановыми оценками.

## 8. Evidence и правила следующего обновления

Для каждого выполненного T00 check записать ID, область, command/environment, pinned versions/commit, result, failure/BLOCKED reason, sanitized evidence link и reviewer. Для последующих tasks дополнительно сохранить R/I/A/E mapping, contract version, fixtures, positive/negative/concurrency/crash results, security/privacy, rollback/upgrade и independent review.

Не отмечать тест или интеграцию выполненными по наличию schema/design/mock. Не создавать `baseline.md` с предположениями. Не переносить DESIGN в VERIFIED. Не отмечать owner review от его имени. Не назначать capacity, даты, оценки или новые SLA в этом tracker.

### Текущий evidence summary

- Design artifacts: ссылки в разделе 3.
- Sanitized T00 integration evidence: отсутствует.
- Executed A01–A36 evidence: отсутствует.
- Owner G0 approval record: отсутствует.
- Documentation-only validation текущего planning package: результаты приведены ниже; это не product test.

### Documentation validation

Локальными read-only Python-проверками без новых зависимостей и artifacts проверено:

- **PASS:** в [traceability.md](traceability.md) ровно 18 R-строк (R01–R18), 14 I-строк (I01–I14), 36 A-строк (A01–A36), 21 T-строка (T00–T20), 9 E-строк (E00–E08) и 30 CF-строк (CF-01–CF-30); [test-plan.md](test-plan.md) сохраняет ровно один упорядоченный сценарий каждого A01–A36 и не содержит duplicate R/I index rows.
- **PASS:** прямые R/A/T mappings и inverse R→A/T→A assignments в traceability точно совпадают с текущей acceptance matrix spec v1.3, включая раскрытие диапазонов R02–R04/R08–R10 и R04−A02, R05+A31, R11+A22, R18−A34.
- **PASS:** tracker acceptance links T02=A01,A32; T03=A04,A11,A18,A22,A24,A25,A26,A30,A31,A32,A33,A36; T04=A08,A10 совпадают с spec.
- **PASS:** все локальные Markdown links/reference definitions и проверяемые heading anchors в 11 разрешённых human-facing docs разрешаются без ошибок.
- **PASS:** фактический [database-catalog.yaml](contracts/database-catalog.yaml) содержит 39 уникальных tables, совпадающих с 39 table headings в [database.md](database.md); это read-only structural check, не DB test.
- **PASS по scope/status:** `baseline.md` отсутствует; [test-plan.md](test-plan.md) и [operations.md](operations.md) существуют как `design_not_executed`, документный sync завершён, owner design review и execution не заявлены.

Это только документная валидация разрешённого пакета, **не product test, не contract test, не acceptance/integration evidence и не G0 approval**. Она не меняет состояния T00–T20.
