# Corporate KB implementation tracker

## 1. Active gate и фактические статусы

**G0 — APPROVED. T00 — DONE. Owner G0 approval — получено.** Разрешены декомпозиция эпиков и последующие задачи по зависимостям; product implementation начинается только по готовности stories и не меняет deferred gates. Правила фазы: [AGENTS.md](../../AGENTS.md).

- **T00 DONE:** pinned baseline выбран и записан в [baseline.md](baseline.md), sanitized evidence собрано в [evidence/t00](evidence/t00/README.md), design docs обновлены по audit findings; CI Runner exact-SHA/no-write PASS 7/7. Owner G0 approval получено ([g0-review.md](g0-review.md), APPROVED). Deferred gates: T04 browser editor, T13/T16 object-store ACL, T11 hoster inputs, production AD/live-SLO, full product migrations/HA и legal clearance перед managed distribution.
- **T01–T20 и T07b TODO:** зависимости перечислены ниже; G0 APPROVED не заменяет implementation-readiness PASS, task dependencies или required real evidence.
- **T00 DONE; остальные задачи не VERIFIED и не DONE.** A01–A36 не запускались; synthetic integration probes и external upstream migration выполнены, но full product migrations, restore/upgrade rehearsal и production readiness отсутствуют.
- Состояния задач используются строго: **TODO → IN_PROGRESS → VERIFIED → DONE**, отдельно **BLOCKED**. Наличие DESIGN-документа не является VERIFIED. Недоступная обязательная real check помечается BLOCKED в соответствующем evidence, а не заменяется mock/PASS.
- Нормативные источники: [spec.md v1.3](spec.md), [Architecture Spine](architecture-spine.md), [ADR index](adr/README.md). Planning coverage: [planning-input.md](planning-input.md), [traceability.md](traceability.md).

## 2. Живой tracker T00–T20

Dependencies сохранены из spec v1.3; G0 является дополнительным внешним gate для всего implementation. E00–E08 не переименованы; T19/T20 не включены в них искусственно.

| ID | Состояние | Depends / gate | Requirements | Существующий Epic | Фактический остаток / следующий evidence |
|---|---|---|---|---|---|
| **T00** | **DONE** | Выполнено: baseline evidence + owner G0 approval | R01–R18 | E00 | [baseline.md](baseline.md), [capability matrix](evidence/t00/capability-matrix.md), sanitized evidence и [g0-review.md](g0-review.md) APPROVED. Deferred gates остаются follow-up и не считаются PASS |
| T01 | DONE | T00 + G0 | R18 | E01 | T01 contract harness executed; sanitized evidence в [evidence/t01](evidence/t01/) (contract-results.json, summary.md). CF-01–CF-30 projection mappings deterministic serialization/hash, semantic/consumer/projection roundtrips и synthetic fault matrix verified. |
| T02 | DONE | T00,T01 + G0 | R01,R02,R03 | E02 | Synthetic two-Space fixtures (`sales/`, `sales-pricing/`) and T02 document harness executed; front-matter-v2, tree navigation, whole/section direct read with exact revision SHA/bounds/cursor/truncation, attachment tuples, archive invariants, path normalization and malformed-heading negative checks verified. Evidence: `_bmad-output/test-artifacts/t02/` and `specs/corporate-kb/evidence/t02/`; A01,A32 |
| T03 | DONE | T02 + G0 | R05,R16 | E02 | Synthetic identity/policy harnesses executed: stable identity keys (sub/objectGUID/entryUUID), nested group snapshots, rename survival, empty groups, epoch ordering, per-Space AuthzContext isolation, longest-prefix approval selection, path normalization, revocation epoch, error shape. Live IdP/AuthZ/GO runtime remains BLOCKED. Evidence: `_bmad-output/test-artifacts/t03a|t03b/` and `specs/corporate-kb/evidence/t03a|t03b/`; A04,A11,A18,A22,A24,A25,A26,A30,A31,A32,A33,A36 |
| T04 | TODO | T03 + G0 | R09,R10 | E03 | Ready editor adapter, draft/save/conflict/history/revert-MR exact revisions; A08,A10 |
| T05 | TODO | T04 + G0 | R06–R10 | E04 | MR+ProposalRecord, canonical DecisionRecord note+tag, real GO merge, target-wide barriers/fencing/reconciliation, conclusive failed guarded retry vs terminal conflicted/invalid; A05–A10,A27–A30,A34,A36 |
| T06 | TODO | T05 + G0; можно параллельно T07 | R05–R08,R16 | E04 | GitLab+GO enforcement всех direct human/bot/CI/engineering/source bypass; A04,A05,A09,A17,A18,A28,A29,A34 |
| T07 | TODO | T05 + G0; можно параллельно T06 | R07,R08 | E04 | Platform review для business без GitLab users, full preview/evidence/restore, decision races; A06,A07,A22,A23,A27,A30 |
| **T07b** | **TODO** | T05,T07 + созданный `docops-correction-task-v1` schema/API/OpenAPI contract + G0; не добавлять в sprint-status вручную | R01,R05–R10 | E04.7 | [Correction schema](contracts/docops-correction-task.schema.json), [API](contracts/docops-correction-api.md), create/get/resolve/cancel, GO-owned `kb_ops` current/events/evidence/idempotency, exact revision/stable actor/policy owner/CAS/optional MR/no-MR evidence/backup-rebuild; Supporting A01,A07,A22,A26,A27,A36; DESIGN_NOT_EXECUTED |
| T08 | TODO | T02,T03,T07 + G0 | R01–R03 | E04 | Tree/direct read/WYSIWYG/front matter/review/revision UX; TipTap adapter selected G0-D8, T04 browser evidence pending; A01 |
| T09 | TODO | T06,T08 + G0 | R03,R06,R07 | E04 | Bounded read/search/propose tools, trusted run/principals, read-only credential boundary; A02,A21 |
| T10 | TODO | T04,T03 + G0; параллельно T05–T09/T12 | R04,R11 | E05 | Audited backend, CI/index writers, independent full/incremental closure proof, separate same-SHA preflight→published pair, per-Space/profile fence/CAS pointer across generations, per-Space fan-out/read-only retrieval; A02,A03,A11,A12,A21,A22,A25,A31,A32,A35 |
| T11 | TODO | T09 + G0; ранняя config-first проверка после G0 | R15,R18 | E04 G1 profile + E07 | Approved hoster.ai studio model connections/streaming/tools/no-fallback; real endpoint/credentials/egress — обязательный blocker, mock не PASS; A16 |
| T12 | TODO | Полный T12/T12b: T03,T04,T05 + G0 и T10 preflight/published artifacts; отдельная T12a dry-run после T03,T04 может идти параллельно T05/T10 | R12,R13 | E06 | T12a dry-run/immutable manifests/data barrier/provenance — отдельная ранняя работа без canonical writes; unpublished load→freeze/protection/preflight/activation только после T05 с T10 artifacts; production corpus запрещён; A13,A23,A31,A35 |
| T13 | TODO | T12 + G0; correction restore использует существующий T07b contract | R14 | E06 | Full export-v2 clone+decisions/assets manifests с explicit outcomes/recovery и decisions/assets/authorization closure, mirror/metadata backup, clean restore и conservative rebuild; отдельный durable non-Git-derived correction-task current/events/evidence/idempotency backup/restore, hashes/event-sequence checks и linked-MR reconciliation без fabrication/deletion и второго canonical write path; A11,A15,A25,A27,A32,A36 |
| T14 | TODO | T01,T09,T10,T11 + G0 | R18 | E01 initial + E05 checks + E07 acceptance | Synthetic golden/negative/concurrency/crash suites и expert Russian set; thresholds не выдумывать; A03,A18,A20,A21 |
| T15 | TODO | T12,T05,T10 + G0 | R13 | E06 minimal + E08 full | Registry/cursors/three-way/no-op/tombstone/one outstanding; human decision+GO merge, без auto-merge; A14 |
| T16 | TODO | T15,T03 + G0 и owner source selection | R12,R13,R16 | E08 | Один SharePoint/Bitrix24/Kayako connector после выбора; real sandbox update/revoke/delete/retry/assets; A14 |
| T17 | TODO | T12 + G0; conditional по реальным форматам | R12,R18 | E08 conditional | Форматные golden/loss/media/scan/OCR fixtures и approved extraction inference; real corpus отдельно авторизуется; A16,A23 |
| T18 | TODO | P0 safety gates,T13 + соответствующие release gates; полный T18/G3 явно также T16/E08.2 | R14,R17,R18 | E07 necessary part + E08 operations | Repeatable dedicated deploy, second isolated client, secrets/egress/observability, backup/restore/upgrade/SBOM/seam registry/runbooks; отдельный non-Git-derived correction backup/restore и linked-MR reconciliation без второго canonical write path; necessary pilot/T18a не закрывают full T18 без T16; A15,A19,A20,A28,A33 |
| T19 | TODO | T14 + measured benchmark/business gate | R04,R11,R18 | Отдельный deferred epic после E08; ID не создан | Engine evolution только по ACL-aware benchmark; ранняя замена stack запрещена; отдельные A в spec не назначены |
| T20 | TODO | T14,T18 + measured/business gate | **В spec v1.3 не указаны** | Отдельный deferred epic после E08; ID не создан | Fast/Trust/Scale policies; R/I/A mapping подтвердить при будущем planning, не назначать thresholds/capacity заранее |

## 3. Готовые design inputs — не implementation completion

| Артефакт | Готовая часть | Статус / оставшееся |
|---|---|---|
| [spec.md v1.3](spec.md) | R01–R18, I01–I14, A01–A36, T00–T20, E00–E08, gates и протоколы | Нормативный proposed spec; не baseline, не executed acceptance |
| [ARCHITECTURE-SPINE.md](architecture-spine.md) | AD-1–AD-16, component/capability map, deferred/consistency conventions | DESIGN; требуется сверка с pinned checkout |
| [architecture.md](architecture.md) | Containers, responsibility/credential/state matrix, lifecycle/recovery/NFR, фактическая ADR/contracts navigation | T00 DONE, G0 APPROVED; deferred implementation gates сохранены |
| [open-webui-fork.md](components/open-webui-fork.md) | UI/review/editor/agent seams, Notes/chats regression | DESIGN; pinned commit и seam/toolchain/editor evidence записаны; TipTap adapter selected (G0-D8), browser checks BLOCKED |
| [git-orchestrator.md](components/git-orchestrator.md) | Proposal/decision/merge/recovery/cutover/export | DESIGN; GitLab CE 19.5.3 capabilities 42 completed probes synthetic; нет target-branch CAS, Owner bypass — G0-D3 |
| [identity-access.md](components/identity-access.md) | Stable identity/policies/grants/AuthzContext/revocation | DESIGN; Keycloak adapter 9/9 PASS, stock OIDC 4 PASS/2 FAIL; adapter mandatory; OpenLDAP 8/8 PASS; production AD/live subscriptions pending |
| [retrieval-indexing.md](components/retrieval-indexing.md) | Generation/profile/closure/preflight/pointer/query design | DESIGN; pgvector synthetic benchmark 22/22 PASS; production model/thresholds owner TBD |
| [ingestion-connectors.md](components/ingestion-connectors.md) | Import/data barrier/source modes/cursors/assets/media | DESIGN; upstream extraction seams audited; connector/formats/object-store остаются owner decisions |
| [ADR-03–ADR-16](adr/README.md) | Все обязательные ADR-файлы, Accepted/Proposed/stop conditions и verification links | DESIGN/Accepted per individual ADR; ADR-04/10/12/15 дополнены T00 STOP findings и adapter controls; **не общий owner G0 approval** |
| [baseline.md](baseline.md) | Pinned versions, sandbox environment, reproducible commands, capability summary, design deltas | **DONE; G0 APPROVED**; runtime evidence synthetic-only, не production approval |
| [evidence/t00](evidence/t00/README.md) | Sanitized evidence index: environment, GitLab 42 completed probes, Keycloak 9/9, stock OIDC 4+2, auth/RAG/editor audits, toolchain, retrieval 22/22, license | Collected for owner review; raw artifacts в `_bmad-output/test-artifacts/t00/` не committed |
| [g0-review.md](g0-review.md) | Owner decision record G0-D1–D17, editor options, approval evidence rules | **APPROVED**; D1–D17 APPROVED 2026-11-08 |
| [database.md](database.md) + [database-catalog.yaml](contracts/database-catalog.yaml) | Single-writer ownership, logical tables, transactions/rebuild, DB assertions | DESIGN; не DDL/migrations; single instance и physical upstream layout не подтверждены |
| [integration.md](integration.md) + [contracts/README.md](contracts/README.md) | API/tools/events/error/idempotency/integration protocols | PROPOSED; T01 validation/compatibility и real integration tests не выполнены |
| [JSON/OpenAPI/YAML machine contracts](contracts/README.md#2-карта-артефактов) | Front-matter-v2/policies/Authz-v2/Proposal/Decision/index/Export-v2/origin/DocOps + `docops-correction-task-v1`/API/tools/events | PROPOSED; correction schema/API/OpenAPI созданы как DESIGN, fixture execution не выполнялось |
| [projection-mapping.md](contracts/projection-mapping.md) + [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml) | Подготовленные canonical↔API↔event↔DB state/enum/ID/path mappings и CF-01–CF-30 consumer vectors | **DESIGN output / DESIGN_NOT_EXECUTED**, не VERIFIED test и не implementation completion |
| [content-standard.md](content-standard.md) | ETL/controlled publication/DocOps синхронизированы с v1.3 | Process DESIGN 2.3; не разрешение corpus load |
| [operations.md](operations.md) | Deployment/startup/cutover/recovery/export/restore/upgrade runbooks | `design_not_executed`; T18 rehearsals и production readiness не подтверждены |
| [test-plan.md](test-plan.md) | Test levels, fixtures, полный A01–A36 catalog, CF links и crash matrix; R/I navigation в traceability | `design_not_executed`; owner design review APPROVED, duplicate R/I indexes удалены; execution отсутствует |
| [planning-input.md](planning-input.md) | Вход для будущей декомпозиции, dependencies/slices/DoR/DoD/fixtures/gates/spikes | READY FOR EPIC DECOMPOSITION только; не implementation approval |
| [traceability.md](traceability.md) | Полные R/I/A/T/E matrices и machine-contract links | DESIGN coverage; не test plan и не executed test report |

[baseline.md](baseline.md) создан по фактическому аудиту и имеет статус **DONE — G0 APPROVED**. [test-plan.md](test-plan.md) и [operations.md](operations.md) существуют как `design_not_executed`; полные A01–A36/fault matrix и runbooks включены в approved G0 design review, но не выполнялись. Отдельный `sprint-status.yaml` не создавался и не редактируется вручную; sprint tracking относится к будущему deterministic generation после readiness PASS. Этот `tasks.md` — единственный live tracker динамических статусов.

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

- [x] Выбрать и закрепить Open WebUI commit/tag, GitLab version/edition, PostgreSQL/toolchain/Git object format и upstream checkout; не угадывать версии. → [baseline.md](baseline.md) §1, [environment.md](evidence/t00/environment.md).
- [x] Записать в `baseline.md` реальные code paths, dev/test environment, lint/test/typecheck commands, migrations/upgrade behavior и sanitized results. → [baseline.md](baseline.md) §3/§5, [toolchain](evidence/t00/openwebui-toolchain.md).
- [x] Проверить Open WebUI auth/users/grants/LDAP/OIDC/JIT/session/CSRF/tool/all-channel/RAG/model-connection seams, personal Notes/chats regression и DB migration ownership. **Static seam + runtime checks выполнены:** [auth audit](evidence/t00/openwebui-auth-audit.md), [toolchain](evidence/t00/openwebui-toolchain.md), [Notes/chats regression](evidence/t00/notes-chats-regression.md) 8/8 PASS; browser UI/IME/XSS и live subscription regression — отдельные deferred checks, не PASS.
- [x] На real sandbox GitLab проверить exact-SHA reads/merge/conflicts, no squash/rebase/FF, first parent=base/second parent=proposal, trailers, structured MR note ID/body/audit/mutation/export, protected annotated decision/cutover tags и refs. → 42 completed probes, [gitlab-capabilities.md](evidence/t00/gitlab-capabilities.md).
- [x] Доказать MR-only/merge-only-GO для non-admin actors, запрет direct human/bot/engineering/CI merge, scoped proposal/CI GitLab credentials, webhook authenticity/replay и audit/metadata export. → [gitlab-capabilities.md](evidence/t00/gitlab-capabilities.md); privileged Owner bypass зафиксирован как G0-D3, не как PASS.
- [ ] Проверить scoped object/source credentials и source-store authorization matrix. **Открыто:** S3 ACL probe FAIL, production source/object-store credentials не проверялись — [object-store.md](evidence/t00/object-store.md), G0-D16/T13/T16.
- [x] На synthetic unpublished repositories проверить controlled bulk exception, cutover freeze→exact HEAD→protections→inactive preflight→pointer/activation и отсутствие retrieval до activation. → cutover GitLab side PASS ([gitlab-capabilities.md](evidence/t00/gitlab-capabilities.md)); preflight/stale/pending exclusion gates PASS в retrieval harness ([retrieval-benchmark.md](evidence/t00/retrieval-benchmark.md)); полный product-side preflight→published→activation chain — implementation после G0.
- [x] Проверить stable AD/OpenLDAP/OIDC IDs, nested groups/JIT/read-only encrypted bind/empty-password CVE-2026-44551, fresh group recheck, mover/leaver/live subscriptions и revocation requirements. **Выполнено на выбранном LDAP/OIDC profile:** OpenLDAP 8/8 PASS ([ldap-capabilities.md](evidence/t00/ldap-capabilities.md)); Keycloak adapter 9/9 PASS ([identity-capabilities.md](evidence/t00/identity-capabilities.md)); stock OIDC runtime 4 PASS/2 FAIL ([openwebui-oidc-runtime.md](evidence/t00/openwebui-oidc-runtime.md)); approval policy 14/14 PASS ([approval-policy-probe.md](evidence/t00/approval-policy-probe.md)); production AD и live subscriptions/measured SLO — последующие integration checks, не PASS.
- [ ] Подтвердить отдельные upstream/`kb_authz`/`kb_ops`/`kb_index` roles/migrations и возможность выделенного PostgreSQL instance; иначе STOP/design review. **Частично:** upstream schema + external migrator + runtime DDL denial PASS; synthetic `kb_*` schemas и четыре cross-write denial PASS ([postgres-schema-probe.md](evidence/t00/postgres-schema-probe.md)); recovery barrier persistence/rebuild semantics 6/6 PASS ([postgres-recovery-probe.md](evidence/t00/postgres-recovery-probe.md)); полные 39-table migrations/denial matrix/HA drills ещё не выполнялись.
- [x] Проверить GitLab CI exact-SHA read, CI without Git write, index/pointer ownership и required clone/metadata/export capabilities. **CI exact-SHA/no-write PASS:** [ci-runner.md](evidence/t00/ci-runner.md).
- [ ] Получить object-store immutable version/hash evidence. **Частично:** immutable versions/delete-marker PASS, cross-bucket ACL FAIL в LocalStack — [object-store.md](evidence/t00/object-store.md); production engine и ACL recheck остаются T13/T16/G0-D16.

### 5.2. Editor, retrieval, inference и packaging spikes

- [x] Сравнить готовые web-редакторы по front matter round-trip, full diff/preview, Cyrillic/links/attachments/XSS/accessibility/license; не выбирать custom editor по умолчанию. **Выбран TipTap adapter (G0-D8):** headless CodeMirror vs TipTap evidence записано ([rag-editor audit](evidence/t00/openwebui-rag-editor-audit.md)); browser/IME/accessibility/XSS/full managed preview — APPROVED DEFERRAL на T04 (G0-D15), не PASS. WYSIWYG retained; realtime collaboration/CRDT вне MVP и не требуется для T04.
- [x] Провести existing retrieval backend audit и ACL-aware Russian benchmark. → 22/22 deterministic gates PASS ([retrieval-benchmark.md](evidence/t00/retrieval-benchmark.md)); production model/dimensions/chunking/thresholds остаются owner TBD, не выбраны.
- [ ] Зафиксировать hoster.ai studio endpoints/model IDs/dependencies/egress/offline assets как configuration UNKNOWN; не объявлять integration без real endpoint. **Остаётся UNKNOWN:** endpoint/model IDs не предоставлены; T11 BLOCKED.
- [x] Зафиксировать Open WebUI branding/notices, GitLab edition/CODEOWNERS limitations и core/plugins/models/dependencies license/SBOM review. **G0-D10 APPROVED:** branding сохраняется, white-label/commercial distribution до legal clearance запрещены; engineering evidence — [license review](evidence/t00/openwebui-license-review.md), [gitlab-capabilities.md](evidence/t00/gitlab-capabilities.md); full legal/SBOM остаётся follow-up перед managed distribution.
- [x] Предложить repository naming/group layout/provisioning без создания production repositories/corpus; определить первый connector/formats/object-store только как questions/candidates до owner decision. → [repository-provisioning.md](repository-provisioning.md).
- [x] Зафиксировать estimation assumptions и capacity-based сценарии первых двух delivery-спринтов с LOW/VERY LOW confidence, без обязательств по срокам. → [delivery-estimates.md](delivery-estimates.md).

### 5.3. Review, planning и evidence

- [x] Завершить owner-facing design review обновлённых [test-plan.md](test-plan.md), [operations.md](operations.md), [traceability.md](traceability.md), [projection-mapping.md](contracts/projection-mapping.md) и [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml): сохранить two-Space fixtures, semantic/consumer negatives, concurrency/crash matrix, environments и explicit blocked real checks. Сами mappings/vectors уже подготовлены как DESIGN, не VERIFIED. D1–D17 APPROVED.
- [x] Подготовить capability matrix, sanitized baseline smoke, риски/UNKNOWN/DEFERRED и предложенный минимальный G1 vertical slice; существующая traceability не заменяет этот output. → [capability-matrix.md](evidence/t00/capability-matrix.md), [baseline.md](baseline.md) §4/§8, G1 slice в [planning-input.md](planning-input.md) §7.
- [x] Обновить ADR/design только по фактическим audit findings; Accepted invariants не переоткрывать без stop evidence, Proposed engine/editor/deployment details не выдавать за Accepted. → ADR-04/10/12/15, components, architecture, test-plan, operations, planning-input дополнены T00 evidence 2026-11-08.
- [x] Сохранить machine output в `_bmad-output/test-artifacts`, а sanitized reviewable evidence — в `specs/corporate-kb/evidence/t00`; реальные секреты/документы/PII не включать. → [evidence/t00/README.md](evidence/t00/README.md).
- [x] Получить и записать **явный owner G0 review/approval по baseline и всему ADR/design package**. Self-approval и наличие файлов не засчитываются. → [g0-review.md](g0-review.md), D1–D17 APPROVED 2026-11-08.

## 6. Design discrepancies: resolved at design-source level

| Прежняя проблема | Разрешение в v1.3/design package | Остаток |
|---|---|---|
| MR-only противоречил bulk import | **RESOLVED:** I01/I02 и [ADR-11](adr/ADR-011-two-phase-publication.md): controlled engineering bulk только в unpublished `main` при закрытом доступе/без published index; далее freeze/exact HEAD/protections/preflight/activation | GitLab cutover side проверен synthetic (42 completed probes); product-side chain и production corpus — после G0/owner decisions |
| Auto-merge противоречил R06/R13 | **RESOLVED:** R06,R13,I02 и [ADR-04](adr/ADR-004-execution-capability-boundary.md), [ADR-11](adr/ADR-011-two-phase-publication.md): agent/connector/LLM/source-managed auto-merge запрещён, apply только GO после human decision | GitLab merge-only-GO enforcement PASS synthetic; product-side bypass matrix (A04/A17/A18) не выполнялась |
| Разные ACL models | **RESOLVED:** R02,R05,I09 и [ADR-10](adr/ADR-010-ldap-oidc-identity.md), [ADR-16](adr/ADR-016-repository-per-space.md): repository=Space=ACL, path scopes только proposal/review/approval, front matter `access` не grant | Cross-Space isolation и nested groups PASS synthetic (GitLab + Keycloak); fresh AuthZ recheck в product — implementation после G0 |
| Merge identity/approver mapping | **RESOLVED:** R05–R10 и [ADR-12](adr/ADR-012-business-approval-without-gitlab-users.md), [ADR-13](adr/ADR-013-merge-serialization-recovery.md), [ADR-14](adr/ADR-014-canonical-decision-record.md): external group/path policy, approver без GitLab user, stable principals, CODEOWNERS только engineering | GitLab notes/tags/merge parents/trailers PASS synthetic; self-approval matrix и platform review — implementation после G0 |
| ADR-09 unknown и 25 vs 36 acceptance IDs | **RESOLVED:** [ADR-09](adr/ADR-009-platform-review-ux.md) существует и Accepted; [spec.md](spec.md) содержит A01–A36; [content-standard.md](content-standard.md) 2.3 синхронизирован | Editor/UX implementation и A01–A36 execution остаются |
| `architecture.md` §12.2–12.3 утверждал отсутствие ADR/contracts | **RESOLVED:** разделы ссылаются на фактические [ADR index](adr/README.md), [contracts README](contracts/README.md), integration/DB/operations/projection/T01 artifacts | Owner G0 review APPROVED; implementation/integration execution остаётся |
| Planning утверждал отсутствие `operations.md`, использовал несуществующую operational document table, неверные T02/T04 acceptance links и незакрытые state mappings | **RESOLVED:** [operations.md](operations.md) существует как DESIGN; R03 использует GO canonical read + kb_index; T02=A01,A32 и T04=A08,A10; [projection-mapping.md](contracts/projection-mapping.md) и CF-01–CF-30 подготовлены | T01 execution, T18 rehearsals и real integration evidence отсутствуют |
| Test-plan R/I duplicate indexes расходились со spec/traceability | **RESOLVED:** duplicate R/I-index удалён; полные A01–A36/fault matrix сохранены, [traceability.md](traceability.md) — единый R/I source; R04−A02, R05+A31, R11+A22, R18−A34 соответствуют spec | Owner design review APPROVED; выполнение A/CF не выполнялось |

Эти записи не закрывают T00, G0 или owner/security approval. Они только устраняют старый normative drift и указывают на актуальные источники. Все prepared mappings/vectors остаются DESIGN output, не VERIFIED test.

## 7. Текущие блокеры и открытые решения

### G0 resolutions и acceptance follow-up / старт implementation

- **G0-D12 APPROVED:** owner утвердил [baseline.md](baseline.md) и весь ADR/design package 2026-11-08 ([g0-review.md](g0-review.md)); T00 DONE, G0 APPROVED. Self-approval не использовалось.
- **CI Runner exact-SHA/no-write:** PASS 7/7 ([ci-runner.md](evidence/t00/ci-runner.md)); production queue/autoscaling/Docker executor/object-store остаются последующими проверками.
- **Browser editor checks DEFERRED:** TipTap adapter выбран (G0-D8); WYSIWYG/raw preview/IME/accessibility/XSS/full managed preview перенесены на T04 по G0-D15 и не считаются PASS. Realtime collaboration/CRDT вне MVP и не является deferred T04 blocker. Headless evidence: CodeMirror byte fidelity PASS, TipTap normalization/loss.
- **Owner decisions приняты с follow-up:** privileged GitLab admin/Owner bypass governance (G0-D3), frontend toolchain debt (G0-D9), license/branding legal review перед managed distribution (G0-D10), hoster.ai deferral (G0-D11).
- Pinned versions, upstream checkout, [baseline.md](baseline.md), real code refs, capability matrix, retrieval benchmark и sanitized evidence — **записаны** и больше не являются blocker; это synthetic sandbox evidence, не production readiness.

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
- Sanitized T00 integration evidence: собрано — [evidence/t00/README.md](evidence/t00/README.md) (environment, GitLab 42 completed probes, CI Runner 7/7, Keycloak 9/9, stock OIDC 4 PASS/2 FAIL, auth/RAG/editor audits, toolchain, retrieval 22/22, license); raw artifacts в `_bmad-output/test-artifacts/t00/` не committed. Отсутствуют browser editor checks.
- Executed A01–A36 evidence: отсутствует.
- Owner G0 approval record: получен 2026-11-08 ([g0-review.md](g0-review.md), **APPROVED**); это не product acceptance.
- Documentation-only validation текущего planning package: результаты приведены ниже; это не product test.

### Documentation validation

Локальными read-only Python/Ruby stdlib проверками без новых зависимостей и artifacts проверено:

- **PASS 2026-11-08 residual readiness corrections:** 17 JSON/YAML contract files и 2 Markdown front matter блока парсятся; 63 Markdown documents имеют 0 broken local links/reference definitions/heading anchors. 39 dependency/status/correction assertions, 21 parent T Requirements mappings и 5 изменённых story R/I/A/F/S mappings совпадают; T12a отделена от full T12/T12b после T05, full T18/G3 зависит от T16, correction restore покрыт E06.4/E08.5, A10 имеет Full/direct E03.1 + Supporting E04.2. [Sprint Change Proposal](../../_bmad-output/planning-artifacts/sprint-change-proposal-2026-11-08.md) — **APPROVED / APPLIED after validation**; новый readiness PASS и sprint-status generation не заявляются.
- **PASS 2026-11-08 Sprint Change Proposal:** все 28 epics story Requirements содержат применимые I/A IDs и Full/Supporting ownership; exclusions E02.1−R05/A04, E03.1/E04.1−A09, E07.3−A19 и E04.2+A28 подтверждены. [traceability.md](traceability.md) содержит 28 final-story rows и все split IDs T03a/b,T04a/b,T05a/b,T07b,T10a/b,T12a/b,T13a/b,T18a/b с R/I/A/F/S.
- **PASS correction contract design/reference validation:** созданные [schema](contracts/docops-correction-task.schema.json) и [API](contracts/docops-correction-api.md) существуют до T07b tracker row; 16 JSON/YAML contract files парсятся Ruby stdlib, internal/external JSON pointers разрешаются (0 broken), 4 correction operations и lifecycle/invariants проверены (0 semantic wiring errors), новые contract placeholder markers отсутствуют.
- **PASS live docs:** 62 Markdown files имеют 0 broken local links; 43 live non-evidence Markdown files не содержат open-G0/stale editor-selection markers; исторические evidence snapshots не переписывались.
- **PASS:** в [traceability.md](traceability.md) ровно 18 R-строк (R01–R18), 14 I-строк (I01–I14), 36 A-строк (A01–A36), 21 parent T-строка (T00–T20), 9 E-строк (E00–E08) и 30 CF-строк (CF-01–CF-30); [test-plan.md](test-plan.md) сохраняет ровно один упорядоченный сценарий каждого A01–A36 и не содержит duplicate R/I index rows.
- **PASS:** прямые R/A/T mappings и inverse R→A/T→A assignments в traceability точно совпадают с текущей acceptance matrix spec v1.3, включая раскрытие диапазонов R02–R04/R08–R10 и R04−A02, R05+A31, R11+A22, R18−A34.
- **PASS:** tracker acceptance links T02=A01,A32; T03=A04,A11,A18,A22,A24,A25,A26,A30,A31,A32,A33,A36; T04=A08,A10 совпадают с spec.
- **PASS:** все локальные Markdown links/reference definitions и проверяемые heading anchors в 11 разрешённых human-facing docs разрешаются без ошибок.
- **PASS:** фактический [database-catalog.yaml](contracts/database-catalog.yaml) содержит 39 уникальных tables, совпадающих с 39 table headings в [database.md](database.md); это read-only structural check, не DB test.
- **PASS по scope/status (на 2026-11-06):** историческая проверка до появления baseline, snapshot не переписывается. Актуальное состояние: [baseline.md](baseline.md) **DONE**, T00 DONE/G0 APPROVED; [test-plan.md](test-plan.md) и [operations.md](operations.md) остаются `design_not_executed`, A/CF/product execution не заявлены.

Это только документная валидация разрешённого пакета, **не product test, не contract test, не acceptance/integration evidence и не G0 approval**. Она не меняет состояния T00–T20.
