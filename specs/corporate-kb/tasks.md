# Corporate KB implementation tracker

## Readiness summary

- **G1 vertical slice readiness:** ~95% (functional acceptance passes; remaining work is production hardening/gates).
- **Overall system readiness per spec v1.3:** ~20% (phase A of five phases A–E is complete/in-progress; phases B–E are not started).

## 1. Active gate и фактические статусы

**G0 — APPROVED. T00 — VERIFIED (synthetic baseline). Owner G0 approval — получено.** Декомпозиция эпиков завершена; product implementation перешла в фазу G1 vertical slice. Правила фазы: [AGENTS.md](../../AGENTS.md).

- **T00 VERIFIED (synthetic):** pinned baseline выбран и записан в [baseline.md](baseline.md), sanitized evidence собрано в [evidence/t00](evidence/t00/README.md), design docs обновлены по audit findings; CI Runner exact-SHA/no-write synthetic PASS 7/7. Owner G0 approval получено ([g0-review.md](g0-review.md), APPROVED). Live runtime для полного T00 остаётся BLOCKED по deferred gates: T04 browser editor, T13/T16 object-store ACL, T11 hoster inputs, production AD/live-SLO, full product migrations/HA и legal clearance.
- **T01–T18b VERIFIED (synthetic harnesses only):** synthetic contract/document/identity/GO/retrieval/ingestion harnesses выполнены; evidence в `_bmad-output/test-artifacts/` и `specs/corporate-kb/evidence/`. Live runtime checks остаются **BLOCKED**, кроме явно перечисленного G1 subset в §1.1; полный A01–A36 на живом sandbox не выполнен.
- **T19/T20 DEFERRED:** ADR-19 deferral сохраняется; measured benchmark/business gate не достигнуты.
- **A01–A36 PARTIAL:** выполнен только G1 subset, перечисленный в §1.1 и evidence. Остальные сценарии A01–A36 **NOT EXECUTED**; synthetic harnesses не засчитываются как acceptance evidence. См. §6 ниже.
- Состояния задач используются строго: **TODO → IN_PROGRESS → VERIFIED (synthetic) → DONE (live acceptance)**, отдельно **BLOCKED (live runtime)**. Наличие DESIGN-документа или synthetic harness не является DONE. Недоступная обязательная real check помечается BLOCKED в соответствующем evidence, а не заменяется mock/PASS.
- Нормативные источники: [spec.md v1.3](spec.md), [Architecture Spine](architecture-spine.md), [ADR index](adr/README.md). Planning coverage: [planning-input.md](planning-input.md), [traceability.md](traceability.md).
- **WP-00 baseline evidence:** `git log --oneline -5` → `e3196de` HEAD; `uv run pytest -q` → 325 passed, 5 skipped, 1 warning (2026-11-10). Добавлен local stack orchestrator (`scripts/local_stack.py`, `scripts/smoke_local_stack.py`, `.env.example`) для полноценного локального запуска. Полный A01–A36 не запускался; выполнен только live subset в §1.1.

## 1.1. G1 vertical slice — IN_PROGRESS

- **Статус:** **IN_PROGRESS (live core flow verified)**. На sandbox GitLab CE `localhost:8081`, проект `corp-kb/sales`, выполнен ограниченный live flow `edit → MR → decision → merge → revert`. Это не полный G1/A01–A36 acceptance: durable drafts/history, lossless TipTap adapter, полный fault matrix и остальные A-сценарии остаются открытыми.
- **Текущее состояние WP-00–WP-05:**
  - WP-00: alembic-миграции используют configured schema; legacy decisions без anchors получают `quarantined`; custom-schema upgrade проверен.
  - WP-01: `/spaces/{space_id:path}/merge-rules` принимает `/` в `space_id`; добавлен regression test.
  - WP-02: live harnesses используют только explicitly allowed disposable `kb_ops_g1_test*` schema и localhost reset guard.
  - WP-03: revert/restore flow и merge replay проверены на живом GitLab; parentage проверяет обоих parents.
  - WP-04: unit/live checks покрывают recovery/reconcile, idempotent replay, actor spoofing и self-approval до создания anchors; полный concurrency/fault matrix не завершён.
  - WP-05: native Open WebUI `/kb` editor вызывает GO с verified session identity; author и approver работают в двух изолированных browser contexts. Standalone `/g1-editor` и публикация test-artifacts удалены. Durable drafts/history/guarded navigation реализованы и покрыты synthetic API checks; lossless TipTap adapter остаётся BLOCKED (T04b).
- **Evidence:**
  - API-level live subset: `_bmad-output/test-artifacts/g1/g1-live-results.json`, `_bmad-output/test-artifacts/g1/g1-live-summary.md`, `specs/corporate-kb/evidence/g1/g1-live-results.json`, `specs/corporate-kb/evidence/g1/g1-live-summary.md` — **20 PASS, 0 FAIL, 0 BLOCKED**.
  - Open WebUI live subset: `_bmad-output/test-artifacts/g1/g1-openwebui-results.json`, `_bmad-output/test-artifacts/g1/g1-openwebui-summary.md`, `specs/corporate-kb/evidence/g1/g1-openwebui-results.json`, `specs/corporate-kb/evidence/g1/g1-openwebui-summary.md` — **17 PASS, 0 FAIL, 0 BLOCKED**.

## 2. Живой tracker T00–T20

Dependencies сохранены из spec v1.3; G0 является дополнительным внешним gate для всего implementation. E00–E08 не переименованы; T19/T20 не включены в них искусственно.

| ID | Состояние | Depends / gate | Requirements | Существующий Epic | Фактический остаток / следующий evidence |
|---|---|---|---|---|---|
| **T00** | **VERIFIED (synthetic)** | baseline evidence + owner G0 approval | R01–R18 | E00 | [baseline.md](baseline.md), [capability matrix](evidence/t00/capability-matrix.md), sanitized evidence и [g0-review.md](g0-review.md) APPROVED. Live runtime BLOCKED по deferred gates (T04 editor, T13/T16 object-store, T11 hoster, production AD/SLO, migrations/HA). |
| T01 | VERIFIED (synthetic) | T00 + G0 | R18 | E01 | T01 contract harness executed; sanitized evidence в [evidence/t01](evidence/t01/) (contract-results.json, summary.md). CF-01–CF-30 projection mappings deterministic serialization/hash, semantic/consumer/projection roundtrips и synthetic fault matrix verified. Live acceptance BLOCKED. |
| T02 | VERIFIED (synthetic) | T00,T01 + G0 | R01,R02,R03 | E02 | Synthetic two-Space fixtures (`sales/`, `sales-pricing/`) and T02 document harness executed; front-matter-v2, tree navigation, whole/section direct read with exact revision SHA/bounds/cursor/truncation, attachment tuples, archive invariants, path normalization and malformed-heading negative checks verified. Evidence: `_bmad-output/test-artifacts/t02/` and `specs/corporate-kb/evidence/t02/`; A01,A32 live BLOCKED. |
| T03 | VERIFIED (synthetic) | T02 + G0 | R05,R16 | E02 | Synthetic identity/policy harnesses executed: stable identity keys (sub/objectGUID/entryUUID), nested group snapshots, rename survival, empty groups, epoch ordering, per-Space AuthzContext isolation, longest-prefix approval selection, path normalization, revocation epoch, error shape. Live IdP/AuthZ/GO runtime remains BLOCKED. Evidence: `_bmad-output/test-artifacts/t03a|t03b/` and `specs/corporate-kb/evidence/t03a|t03b/`; A04,A11,A18,A22,A24,A25,A26,A30,A31,A32,A33,A36 live BLOCKED. |
| T04 | **IN_PROGRESS / BLOCKED (remaining live checks)** | T03 + G0 | R09,R10 | E03 | Synthetic T04a API checks **9/9 PASS** (durable drafts, history cursor pagination, space/path validation). Open WebUI `/kb` editor extended with draft tabs, dirty-state guarded navigation и history panel. Live browser acceptance и lossless TipTap roundtrip (T04b) остаются BLOCKED до sandbox. |
| T05 | **IN_PROGRESS (live subset verified)** | T04 + G0 | R06–R10 | E04 | Synthetic T05a/T05b harnesses выполнены. Live API subset **20/20 PASS** и Open WebUI subset **17/17 PASS** подтверждают proposal/decision/merge/revert, idempotent replay, actor spoofing/self-approval denial до anchors и independent browser sessions. Полный A05–A10/A27–A30/A34/A36 acceptance, concurrency/fault matrix и полный canonical contract не заявляются DONE. |
| T06 | **IN_PROGRESS (live subset verified)** | T05 + G0; можно параллельно T07 | R05–R08,R16 | E04 | Synthetic T06 harness выполнен; live precondition подтверждает protected+merge_only, а security checks подтверждают session/path/actor enforcement для нового prepare flow. Полный direct-push/all-channel bypass, fencing/race/recovery acceptance остаётся IN_PROGRESS/BLOCKED; DONE не заявляется. |
| T07 | VERIFIED (synthetic) | T05 + G0; можно параллельно T06 | R07,R08 | E04 | T07 business review UI harness executed; sanitized evidence in `_bmad-output/test-artifacts/t07/` and `specs/corporate-kb/evidence/t07/`; exact diff, CSRF/Origin, independent decisions, lifecycle views, preview reliability; live browser/runtime remains BLOCKED; A06,A07,A22,A23,A27,A30 live BLOCKED. |
| **T07b** | **VERIFIED (synthetic)** | T05,T07 + `docops-correction-task-v1` schema/API/OpenAPI contract + G0 | R01,R05–R10 | E04.7 | T07b DocOps review projections/correction-task/UX telemetry harness executed; sanitized evidence in `_bmad-output/test-artifacts/t07b/` and `specs/corporate-kb/evidence/t07b/`; valid_until projections, correction-task lifecycle, telemetry redaction; live GO/kb_ops runtime remains BLOCKED; Supporting A01,A07,A22,A26,A27,A36 live BLOCKED. |
| T08 | VERIFIED (synthetic) | T02,T03,T07 + G0 | R01–R03 | E04 | T08 scoped agent context/direct-read harness executed; sanitized evidence in `_bmad-output/test-artifacts/t08/` and `specs/corporate-kb/evidence/t08/`; page/subtree/Space scope, canonical exact-revision reads, citations, cursor revocation; live agent/GO runtime remains BLOCKED; A01 live BLOCKED. |
| T09 | VERIFIED (synthetic) | T06,T08 + G0 | R03,R06,R07 | E04 | T09 restricted single-page agent proposal harness executed; sanitized evidence in `_bmad-output/test-artifacts/t09/` and `specs/corporate-kb/evidence/t09/`; AgentAnchoredPatchChange, forbidden capabilities/diff/channel negatives, prompt injection data treatment; live agent/GO runtime remains BLOCKED; A02,A21 live BLOCKED. |
| T10 | VERIFIED (synthetic) | T04,T03 + G0; параллельно T05–T09/T12 | R04,R11 | E05 | T10a/T10b harnesses executed; sanitized evidence in `_bmad-output/test-artifacts/t10a|t10b/` and `specs/corporate-kb/evidence/t10a|t10b/`; exact-SHA CI build, inactive preflight artifact, full/incremental index-snapshot-v1 contract, eligible-content exclusion, idempotent rebuild, preflight→published lifecycle, per-Space/profile CAS/fencing pointer, exact/semantic retrieval with citations, cursor binding/stale rejection, explicit `INDEX_NOT_READY`/`LIMIT_EXCEEDED`; live GitLab/PostgreSQL/CI/retrieval remains BLOCKED; A02,A03,A11,A12,A21,A22,A25,A31,A32,A35 live BLOCKED. |
| **T11** | **VERIFIED (synthetic)** | T09 + G0; ранняя config-first проверка после G0 | R15,R18 | E04 G1 profile + E07 | T11 inference harness executed; sanitized evidence in `_bmad-output/test-artifacts/t11/` and `specs/corporate-kb/evidence/t11/`; approved route inventory, streaming/tool-call correlation and authorization, malformed/unsafe input rejection, retry/cancel/disconnect observability, egress/perimeter controls and lifecycle metric structure verified; live hoster.ai endpoint/credentials/egress remains BLOCKED; A16 live BLOCKED. |
| T12 | VERIFIED (synthetic) | Полный T12/T12b: T03,T04,T05 + G0 и T10 preflight/published artifacts; отдельная T12a dry-run после T03,T04 может идти параллельно T05/T10 | R12,R13 | E06 | T12a/T12b harnesses executed; sanitized evidence in `_bmad-output/test-artifacts/t12a|t12b/` and `specs/corporate-kb/evidence/t12a|t12b/`; deterministic dry-run import, admission gates, path→ID mapping, PII/media/security blockers, zero canonical writes; controlled cutover/activation, CutoverRecord, freeze/HEAD/protection, preflight→published pointer order, no bypass; live source/GitLab/object-store/IdP checks remain BLOCKED; A13,A23,A31,A35 live BLOCKED. |
| T13 | VERIFIED (synthetic) | T12 + G0; correction restore использует существующий T07b contract | R14 | E06 | T13a/T13b harnesses executed; sanitized evidence in `_bmad-output/test-artifacts/t13a|t13b/` and `specs/corporate-kb/evidence/t13a|t13b/`; complete portable export with exact refs, decisions/assets/policy/grants manifests, authorization closure; mirror/metadata/object backup, secrets separation, clean isolated restore, conservative kb_authz/kb_ops/kb_index rebuild, correction-task backup reconciliation without fabricated/deleted canonical writes; live backup/restore/rebuild on GitLab/PostgreSQL/object-store/IdP remains BLOCKED; A11,A15,A25,A27,A32,A36 live BLOCKED. |
| **T14** | **VERIFIED (synthetic)** | T01,T09,T10,T11 + G0 | R18 | E01 initial + E05 checks + E07 acceptance | T14 evaluation harness executed; sanitized evidence in `_bmad-output/test-artifacts/t14/` and `specs/corporate-kb/evidence/t14/`; eval-case versioning, separated quality/safety/operational/observability metrics, citation groundedness, deterministic adversarial suites, Russian golden-set grading structure and human-in-the-loop disposition verified; real hoster.ai inference and owner-reviewed expert golden set remain BLOCKED; A03,A18,A20,A21 live BLOCKED. |
| **T15** | **VERIFIED (synthetic)** | T12,T05,T10 + G0 | R13 | E06 minimal + E08 full | T15 safe source registry/three-way updates/durable cursors harness executed; sanitized evidence in `_bmad-output/test-artifacts/t15/` and `specs/corporate-kb/evidence/t15/`; cursor durability, same-hash no-op, one outstanding proposal, ownership modes, tombstone deletion and crash replay verified; live source connector runtime remains BLOCKED; A14 live BLOCKED. |
| **T16** | **VERIFIED (synthetic)** | T15,T03 + G0 и owner source selection | R12,R13,R16 | E08 | T16 one owner-selected real source connector harness executed; sanitized evidence in `_bmad-output/test-artifacts/t16/` and `specs/corporate-kb/evidence/t16/`; feasibility inventory, connector identity/provenance/capabilities, revocation, deletion/retry/dedupe, attachments/object-ACL and secrets hygiene verified; live source connector sandbox/credentials remain BLOCKED; A14 live BLOCKED. |
| **T17** | **VERIFIED (synthetic)** | T12 + G0; conditional по реальным форматам | R12,R18 | E08 conditional | T17 evidence-gated extraction/media/OCR harness executed; sanitized evidence in `_bmad-output/test-artifacts/t17/` and `specs/corporate-kb/evidence/t17/`; route activation gate, Docling assessment, golden/loss fixtures, media classes, malicious rejection and provider/profile/egress checks verified; real owner-authorized non-Markdown samples remain BLOCKED; A16,A23 live BLOCKED. |
| **T18** | **VERIFIED (synthetic)** | P0 safety gates,T13 + соответствующие release gates; полный T18/G3 явно также T16/E08.2 | R14,R17,R18 | E07 necessary part + E08 operations | T18 necessary pilot slice harness executed; sanitized evidence in `_bmad-output/test-artifacts/t18/` and `specs/corporate-kb/evidence/t18/`; pilot environment isolation, credential/egress separation, runbook rehearsal checklist, backup/restore drill semantics, security/regression checks, privileged-bypass incident governance and business-user acceptance verified; live pilot environment/corpus and full G3/second-client acceptance remain BLOCKED; A15,A19,A20,A28,A33 live BLOCKED. |
| **T18a** | **VERIFIED (synthetic)** | T18 + E08.4 config-only dedicated deployment | R14,R17,R18 | E08.4 | T18a repeatable config-only dedicated deployment harness executed; sanitized evidence in `_bmad-output/test-artifacts/t18a/` and `specs/corporate-kb/evidence/t18a/`; resource isolation, config-only delivery, migration ownership, cold startup, credential/egress separation and readiness states verified; live second-client environment/object-store/CI/perimeter remains BLOCKED; A19,A20,A33 live BLOCKED. |
| **T18b** | **VERIFIED (synthetic)** | T18a,T16 + full G3 operational acceptance | R14,R17,R18 | E08.5 | T18b full G3 backup/restore/upgrade/operational acceptance harness executed; sanitized evidence in `_bmad-output/test-artifacts/t18b/` and `specs/corporate-kb/evidence/t18b/`; clean restore, correction-task backup reconciliation, unknown-merge quarantine, metrics/alerts/runbooks, upgrade/rollback rehearsal, cross-client negative controls and full G3 acceptance criteria verified; real second-client deployment, real connector evidence and independent G3 review remain BLOCKED; A15,A19,A20,A28,A33 live BLOCKED. |
| T19 | DEFERRED | T14 + measured benchmark/business gate | R04,R11,R18 | Отдельный deferred epic после E08; ID не создан | ADR-19 deferred; engine evolution только после ACL-aware benchmark; ранняя замена stack запрещена |
| T20 | DEFERRED | T14,T18 + measured/business gate | **В spec v1.3 не указаны** | Отдельный deferred epic после E08; ID не создан | ADR-19 deferred; Fast/Trust/Scale policies; R/I/A mapping и thresholds/capacity подтвердить при будущем gate |

## 3. Готовые design inputs — не implementation completion

| Артефакт | Готовая часть | Статус / оставшееся |
|---|---|---|
| [spec.md v1.3](spec.md) | R01–R18, I01–I14, A01–A36, T00–T20, E00–E08, gates и протоколы | Нормативный proposed spec; не baseline, не executed acceptance |
| [ARCHITECTURE-SPINE.md](architecture-spine.md) | AD-1–AD-17, component/capability map, deferred/consistency conventions | DESIGN; AD-17 owner-approved 2026-11-09; требуется сверка deployment implementation |
| [architecture.md](architecture.md) | Containers, responsibility/credential/state matrix, lifecycle/recovery/NFR, фактическая ADR/contracts navigation | T00 DONE, G0 APPROVED; deferred implementation gates сохранены |
| [open-webui-fork.md](components/open-webui-fork.md) | UI/review/editor/agent seams, Notes/chats regression | DESIGN; pinned commit и seam/toolchain/editor evidence записаны; TipTap adapter selected (G0-D8), browser checks BLOCKED |
| [git-orchestrator.md](components/git-orchestrator.md) | Proposal/decision/merge/recovery/cutover/export | DESIGN; GitLab CE 19.5.3 capabilities 42 completed probes synthetic; нет target-branch CAS, Owner bypass — G0-D3 |
| [identity-access.md](components/identity-access.md) | Stable identity/policies/grants/AuthzContext/revocation | DESIGN; Keycloak adapter 9/9 PASS, stock OIDC 4 PASS/2 FAIL; adapter mandatory; OpenLDAP 8/8 PASS; production AD/live subscriptions pending |
| [retrieval-indexing.md](components/retrieval-indexing.md) | Generation/profile/closure/preflight/pointer/query design | DESIGN; pgvector synthetic benchmark 22/22 PASS; production model/thresholds owner TBD |
| [ingestion-connectors.md](components/ingestion-connectors.md) | Import/data barrier/source modes/cursors/assets/media | DESIGN; upstream extraction seams audited; connector/formats/object-store остаются owner decisions |
| [ADR-03–ADR-17](adr/README.md) | Все обязательные ADR-файлы, Accepted/Proposed/stop conditions и verification links | DESIGN/Accepted per individual ADR; ADR-17 owner-approved 2026-11-09 отдельно от исторического G0; production deployment evidence отсутствует |
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
- T19/T20: DEFERRED по ADR-19; business gate и measured benchmarks заблокированы до реального корпуса и T14 evaluation.

Owner decisions без выдуманных значений: business groups/path scopes/CODEOWNERS; hoster inventory/egress; corpus/concurrency/latency/freshness/quality/budgets; RPO/RTO/retention/idempotency replay/session limits; source connector/formats/object-store; commercial branding/license/SBOM. Уже утверждённые group refresh ≤15 минут и revocation SLO ≤30 минут не заменяются плановыми оценками.

## 8. Evidence и правила следующего обновления

Для каждого выполненного T00 check записать ID, область, command/environment, pinned versions/commit, result, failure/BLOCKED reason, sanitized evidence link и reviewer. Для последующих tasks дополнительно сохранить R/I/A/E mapping, contract version, fixtures, positive/negative/concurrency/crash results, security/privacy, rollback/upgrade и independent review.

Не отмечать тест или интеграцию выполненными по наличию schema/design/mock. Не создавать `baseline.md` с предположениями. Не переносить DESIGN в VERIFIED. Не отмечать owner review от его имени. Не назначать capacity, даты, оценки или новые SLA в этом tracker.

### Текущий evidence summary

- Design artifacts: ссылки в разделе 3.
- Sanitized T00 integration evidence: собрано — [evidence/t00/README.md](evidence/t00/README.md) (environment, GitLab 42 completed probes, CI Runner 7/7, Keycloak 9/9, stock OIDC 4 PASS/2 FAIL, auth/RAG/editor audits, toolchain, retrieval 22/22, license); raw artifacts в `_bmad-output/test-artifacts/t00/` не committed. Отсутствуют browser editor checks.
- **G1 live evidence (2026-11-10):**
  - API-level live subset `run_g1_live_acceptance.py` на sandbox GitLab CE `localhost:8081`, проект `corp-kb/sales` — **20 PASS, 0 BLOCKED, 0 FAIL**. Проверены health/merge-only, proposal/decision/merge/revert, both-parent ancestry/trailers, protected tag, idempotent merge replay, source-branch/no-decision/base-mismatch/merge-failure negatives, actor spoofing и self-approval denial до anchors. Browser/UX checks в этот report не включены.
  - Open WebUI live subset `run_openwebui_acceptance.py` — **17 PASS, 0 FAIL, 0 BLOCKED**. Проверены `/kb` route, random per-run users, unauthenticated/CI-path denials, idempotent prepare retry, author submit, denial of author approval, decision/merge в отдельном approver browser context, both-parent ancestry/trailers/tag и merged file visibility.
  - Артефакты: `_bmad-output/test-artifacts/g1/g1-live-results.json`, `_bmad-output/test-artifacts/g1/g1-live-summary.md`, `_bmad-output/test-artifacts/g1/g1-openwebui-results.json`, `_bmad-output/test-artifacts/g1/g1-openwebui-summary.md`, `specs/corporate-kb/evidence/g1/g1-live-results.json`, `specs/corporate-kb/evidence/g1/g1-live-summary.md`, `specs/corporate-kb/evidence/g1/g1-openwebui-results.json`, `specs/corporate-kb/evidence/g1/g1-openwebui-summary.md`.
- **A01–A36 execution status:** заявляется только описанный выше live subset. Полный A01–A36 **NOT EXECUTED**; DONE для T04/T05/T06 и полного G1 не утверждается. Synthetic harnesses (T01–T18b) не засчитываются как acceptance evidence.
- Owner G0 approval record: получен 2026-11-08 ([g0-review.md](g0-review.md), **APPROVED**); это не product acceptance.
- **WP-00 baseline evidence (2026-11-10):** `git log --oneline -5` → `e3196de` HEAD; `uv run pytest -q` → 220 passed, 1 warning. Live subset: 20/20 API + 17/17 Open WebUI; полный G1 acceptance остаётся IN_PROGRESS.
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
- **PASS по scope/status (на 2026-11-06):** историческая проверка до появления baseline, snapshot не переписывается. Актуальное состояние: [baseline.md](baseline.md) **VERIFIED (synthetic)**, T00 VERIFIED (synthetic)/G0 APPROVED; [test-plan.md](test-plan.md) и [operations.md](operations.md) остаются `design_not_executed`, A/CF/product execution не заявлены.

Это только документная валидация разрешённого пакета, **не product test, не contract test, не acceptance/integration evidence и не G0 approval**. Она не меняет состояния T00–T20.

## 9. Tech-debt baseline tests

- **Status:** DONE 2026-11-08.
- **Scope:** pytest baseline in project root and unit tests for T01–T04b harness reporters/sanitize and key validators.
- **Artifacts:** `pyproject.toml`, `tests/test_reporters.py`, `tests/test_t02_validators.py`, `tests/test_t03a_validators.py`, `tests/test_t03b_validators.py`, `tests/test_t04a_validators.py`, `tests/test_t04b_validators.py`.
- **Verification:**
  - `uv run pytest -q` — all tests pass;
  - `uv run ruff check tests --select=F` — clean;
  - `uv run ruff format --check tests` — clean.
- **Constraints respected:** no product code changes, no pinned version changes, synthetic fixtures only, no real credentials/endpoints.

## 10. Future phases — remaining work (B–E)

Phase A corresponds to the G1 vertical slice (`edit → MR → review → DecisionRecord → merge → restore`) currently IN_PROGRESS. Phases B–E are required to finish the system per spec v1.3 and are not started. Detailed plans for each phase are in the sections below. All new phase tasks use IDs `B01–B28`, `C01–C18`, `D01–D15`, `E01–E17` and initial status `TODO`.

> Scope discipline: tasks are not created for deferred topics. T19/T20 remain DEFERRED per ADR-19. Page-level ACL inside a single Space, realtime CRDT collaboration, OpenSearch stack swap, universal two-way sync, routine break-glass product capability and privacy hard purge remain DEFERRED and require a separate ADR before implementation.

## 11. Phase B plan — Identity / Retrieval services live integration

Closes the live runtime gaps for Identity/AuthZ, sessions and the Retrieval service.

### Epic B.1 — Identity service live integration

| Field | Value |
|---|---|
| ID | B.1 |
| Title | Identity service live integration |
| Goal | Provide live stable identity, nested group resolution, per-Space ACL and path-scoped approval policy enforcement using Keycloak/OpenLDAP sandboxes. |
| Scope boundaries | Reuses upstream Open WebUI LDAP/OIDC authentication; identity/AuthZ adapter owns stable ID mapping, group snapshots, policy evaluation and `AuthzContext`. Does NOT implement production Active Directory integration (Phase E) or create GitLab users for business approvers. |

#### Stories

- **Story B.1.1 — Stable identity login via Keycloak/OpenLDAP**
  - *As a business user I log in through the corporate IdP so that I receive a stable platform identity that survives renames.*
  - Given a user record exists in Keycloak/OpenLDAP with `objectGUID`/`entryUUID`/issuer-scoped `sub`
    - When they authenticate through the Open WebUI login seam
    - Then the identity adapter maps them to an internal user keyed by stable_id and normalizes `{username, display_name, groups[]}`
  - Given a user is renamed in the IdP (login/email change)
    - When they log in again
    - Then all history, MR attribution and pending reviews remain linked to the same stable_id
  - Given duplicate or ambiguous directory matches for the same login
    - When the adapter resolves the identity
    - Then the login is rejected and a security audit event is recorded

- **Story B.1.2 — Nested group closure and revocation**
  - *As a security operator I enforce group-based access so that revocation takes effect within the agreed SLO.*
  - Given a user is a member of nested IdP groups
    - When the AuthzContext is built
    - Then the effective group set includes transitive closure and is recorded in the group snapshot
  - Given a user is removed from all IdP groups
    - When the next group snapshot refresh runs (interval ≤ 15 min)
    - Then managed grants are revoked and the AuthzContext becomes fail-closed
  - Given a revoked user attempts search, merge, export or agent tool use
    - When the request reaches a sensitive operation recheck point
    - Then the request is denied and live subscriptions are closed

- **Story B.1.3 — Per-Space ACL and approval policy enforcement**
  - *As a platform I resolve Space roles and path-scoped approvers so that authorization is consistent across UI, tools, retrieval, merge and export.*
  - Given a policy bundle containing `access-policy.yaml` and `approval-policy.yaml` at a known Git SHA
    - When a user's AuthzContext is evaluated for a Space
    - Then it contains `space_scopes`, `policy_bundle_id`, `access_policy_revision`, `approval_policy_revision` and `revocation_epoch`
  - Given an approver group is assigned to a path prefix in `approval-policy.yaml`
    - When a proposal targets a document under that prefix
    - Then the longest-prefix approver selection resolves the correct business approver group
  - Given an access or approval policy revision mismatch at merge time
    - When GO rechecks the policy bundle and group snapshot
    - Then the merge is refused with zero writes to `main`

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| B01 | Implement identity adapter stable_id mapping and duplicate/ambiguous rejection | `src/identity-access/adapter/`, `kb_authz.users`, Open WebUI auth seam | M | TODO |
| B02 | Implement JIT provisioning and group snapshot ingestion | Identity service, `kb_authz.group_snapshots`, IdP admin API adapter | M | TODO |
| B03 | Implement nested group closure | Identity service group resolver, cache layer | L | TODO |
| B04 | Implement empty-group revocation and epoch tracking | Identity service, `kb_authz.grants`, AuthzContext builder | M | TODO |
| B05 | Implement per-Space policy bundle loader and revision tracker | Identity service, Git policy reader, `kb_authz.policy_bundles` | M | TODO |
| B06 | Integrate AuthzContext issuance with Open WebUI `/kb` routes and GO API | Open WebUI backend KB routers, `src/git-orchestrator/app/api/auth.py` | L | TODO |
| B07 | Add live acceptance tests for Keycloak/OpenLDAP identity flows | `tests/b01_identity_live/`, fixtures | M | TODO |
| B08 | Add revocation SLO telemetry and alerting hooks | Identity service metrics, dashboards | S | TODO |

### Epic B.2 — Session service

| Field | Value |
|---|---|
| ID | B.2 |
| Title | Session service |
| Goal | Provide short-lived, identity-bound and policy-bound sessions, secure token refresh/logout, and revocation propagation to GO and Retrieval. |
| Scope boundaries | Reuses upstream Open WebUI session cookies/tokens where possible; adds session-bound AuthzContext and policy-bundle revision binding. Does NOT replace upstream user/session tables. |

#### Stories

- **Story B.2.1 — Session creation and binding**
  - *As a user I receive a session after login so that subsequent requests are bound to my stable identity and current policy bundle.*
  - Given a successful login
    - When the session is issued
    - Then it contains `session_id`, `stable_id`, `issued_at`, `expires_at` and the policy-bundle revisions active at issue time
  - Given a request to GO or Retrieval
    - When a valid session token is presented
    - Then the service validates the token and attaches the current AuthzContext
  - Given a session with an expired token
    - When a protected route is called
    - Then the service returns `401/403` and does not process the request

- **Story B.2.2 — Token refresh and revocation**
  - *As a user I refresh my session so that I stay authenticated without re-entering credentials.*
  - Given a valid refresh token
    - When a refresh is requested
    - Then a new access token is issued and the previous token is invalidated
  - Given a global or per-user revocation event
    - When an affected token is presented
    - Then it is refused within the revocation SLO and live subscriptions are closed
  - Given a token is replayed after revocation
    - When the token is validated
    - Then validation fails and an audit event is emitted

- **Story B.2.3 — Session-bound Git Orchestrator requests**
  - *As an author I submit a proposal through my browser session so that GO receives my verified identity.*
  - Given a valid browser session
    - When the UI calls GO prepare/submit/decide
    - Then GO validates the session with the identity service and uses the stable_id as the trusted actor
  - Given a forged or stolen session token
    - When it is sent to GO
    - Then GO returns `401/403` and logs the attempt
  - Given a session whose policy bundle has changed
    - When a merge/export is attempted
    - Then GO re-fetches the AuthzContext and refuses the operation if the bundle is no longer valid

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| B09 | Implement session token issuance and validation service | Session service, shared token strategy, `kb_authz.sessions` | M | TODO |
| B10 | Implement token refresh and revocation event handler | Session service, identity service event bus/polling | M | TODO |
| B11 | Bind AuthzContext and policy revisions to session | Identity service, session middleware | M | TODO |
| B12 | Wire session validation into GO API auth layer | `src/git-orchestrator/app/api/auth.py`, GO middleware | M | TODO |
| B13 | Implement logout and global/per-user revocation endpoint | Open WebUI auth routes, session service | S | TODO |
| B14 | Add session fault/timeout acceptance tests | `tests/b09_session_live/`, fault injection | S | TODO |

### Epic B.3 — Retrieval API and search/ranking

| Field | Value |
|---|---|
| ID | B.3 |
| Title | Retrieval API and search/ranking |
| Goal | Serve ACL-filtered exact, semantic and hybrid search with citations over activated published Spaces. |
| Scope boundaries | Uses the pgvector + FTS baseline selected at G0; OpenSearch stack swap remains DEFERRED per ADR-19. Document-level ACL inside a single Space is DEFERRED per spec v1.3 / ADR-16. |

#### Stories

- **Story B.3.1 — ACL-filtered semantic search**
  - *As a reader I search an activated published Space so that I receive only documents I am authorized to read.*
  - Given an activated published Space with a versioned access policy
    - When a Reader searches with a natural-language query
    - Then the Retrieval API queries only eligible `published` `main` snapshots
  - Given a user with no access to a Space
    - When they attempt to search it
    - Then the result is an empty list or anti-enumeration `NOT_FOUND`
  - Given search candidates exist in the index
    - When results are returned
    - Then snippets are filtered server-side by Space ACL before leaving the server and before entering any LLM payload

- **Story B.3.2 — Hybrid search, reranking and highlighting**
  - *As a reader I use hybrid search so that keyword and semantic signals are combined and the best sources surface.*
  - Given a query with rare or compound Russian terms
    - When hybrid mode is selected
    - Then both FTS and vector results are retrieved and merged by a deterministic fusion rule
  - Given a reranker is configured
    - When candidates are returned
    - Then the reranker reorders them and the response includes per-candidate scores
  - Given a result is displayed in the UI or agent answer
    - Then highlighted spans are shown with source `document_id`, `document_revision_sha` and section/range

- **Story B.3.3 — Cursor binding, stale rejection and explicit limits**
  - *As a platform I reject stale or over-limit requests so that clients receive explicit, safe errors.*
  - Given a cursor bound to a specific published snapshot
    - When that snapshot is no longer the active published snapshot
    - Then the request returns `STALE_SNAPSHOT` and the client can re-query
  - Given a request that exceeds configured result or depth limits
    - When it is processed
    - Then the service returns `LIMIT_EXCEEDED` with a clear boundary
  - Given an inactive preflight or cutover index
    - When a retrieval request targets it
    - Then the request is refused and never served as published

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| B15 | Implement Retrieval API service with `/api/kb/v1/search` and `/read` endpoints | `src/retrieval/app/main.py`, routers | L | TODO |
| B16 | Implement exact/semantic pgvector query builder with ACL filtering | `src/retrieval/adapters/pgvector.py`, `kb_index` queries | L | TODO |
| B17 | Implement hybrid search merge and reranker integration | Retrieval service, reranker adapter | L | TODO |
| B18 | Implement result highlighting and citation metadata | Retrieval service, Open WebUI/agent response formatting | M | TODO |
| B19 | Implement cursor binding, stale rejection and `LIMIT_EXCEEDED` | Retrieval API, `kb_index.snapshot_registry` | M | TODO |
| B20 | Integrate retrieval adapter with agent tools (`read_document`, `search_documents`) | Open WebUI tool bindings / agent orchestration | M | TODO |
| B21 | Add live ACL-aware retrieval benchmark with Russian corpus | `tests/b15_retrieval_live/`, golden set | L | TODO |
| B22 | Wire Retrieval API authorization to identity service and GO | Retrieval service auth middleware | M | TODO |

### Epic B.4 — Index management and relevance tuning

| Field | Value |
|---|---|
| ID | B.4 |
| Title | Index management and relevance tuning |
| Goal | Build, publish and tune search indices with full/incremental equivalence, single-writer pointer semantics and safe profile changes. |
| Scope boundaries | Index builds are triggered by CI/webhooks; single writer per `(space_id, profile_id)`. Profile changes require a shadow build; destructive live rebuild is forbidden. |

#### Stories

- **Story B.4.1 — Index build from published main**
  - *As a CI worker I build an index from an eligible published snapshot so that retrieval can serve it.*
  - Given a merge commit reaches `main`
    - When CI receives `IndexRequested` for the exact `main_sha`
    - Then it reads the exact snapshot, builds exact and semantic projections and validates dependency closure
  - Given the build succeeds
    - When the active pointer is published
    - Then it is advanced atomically by the single index writer per `(space_id, profile_id)`
  - Given the build fails validation
    - When the run completes
    - Then the active pointer is not advanced and an alert is emitted

- **Story B.4.2 — Full/incremental equivalence and late-job protection**
  - *As a platform I guarantee incremental builds are equivalent to full builds so that stale jobs cannot downgrade the index.*
  - Given an incremental run is produced
    - When its dependency closure is validated against an independent full run
    - Then the closures match or the incremental result is rejected
  - Given a late job from an older Git generation
    - When it tries to advance the pointer
    - Then it receives zero updated rows and the active pointer stays on the newer generation
  - Given history is rewritten in a Space
    - When the index worker detects a new generation
    - Then it performs a full rebuild instead of an incremental update

- **Story B.4.3 — Relevance tuning and profile management**
  - *As an operator I configure chunking, embedding model and thresholds without destructive live rebuild.*
  - Given a new index profile version
    - When it is activated
    - Then a shadow build runs in parallel without affecting the active pointer
  - Given the shadow build passes validation
    - When the operator approves the cutover
    - Then the active pointer switches to the new profile atomically
  - Given the new profile underperforms
    - When the operator requests rollback
    - Then the previous profile pointer is restored

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| B23 | Implement CI index worker with exact-SHA Git read | `src/index-worker/`, CI pipeline definitions | L | TODO |
| B24 | Implement full and incremental index-run equivalence check | Index worker, `kb_index.run_registry` | L | TODO |
| B25 | Implement single-writer active pointer CAS and generation fence | `kb_index.active_pointer`, index worker | M | TODO |
| B26 | Implement index profile versioning and shadow build orchestration | Index worker config, `kb_index.profile_registry` | M | TODO |
| B27 | Implement Russian-aware chunking and embedding model integration | Index worker, embedding adapter | M | TODO |
| B28 | Add index build observability (queue lag, run duration, closure status) | Metrics, dashboards | S | TODO |

### Phase B dependencies

- Phase A G1 vertical slice closed for the identity/retrieval-relevant subset: T03 design implemented, T04/T05 live acceptance passed, T10 preflight/published artifacts stable.
- Design decisions accepted: ADR-10 (identity), ADR-03 (retrieval adapter), ADR-05 (index delivery), ADR-15 (schema ownership), ADR-16 (repository=Space).
- Sandbox/infrastructure: Keycloak or OpenLDAP reachable; PostgreSQL/pgvector instance for `kb_index`; CI runner with exact-SHA/no-write credentials.
- Owner inputs: production IdP profile deferred to Phase E; embedding model dimensions and chunking strategy needed before B.4 relevance tuning can close.

### Phase B risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Stock Open WebUI LDAP/OIDC gaps (email linking, missing stable attributes, stale groups) require a non-trivial adapter. | High | Treat the identity/AuthZ adapter as mandatory per baseline.md §6; do not rely on upstream JIT; add synthetic→live test ladder. |
| Embedding model and relevance thresholds are owner TBD; Russian quality targets undefined. | High | Shadow-build approach lets model selection proceed in parallel; use synthetic Russian corpus and golden-set grading structure from T14; block production cutover until thresholds are agreed. |
| Retrieval adapter must enforce ACL before payload exposure; a bug could leak snippets to LLM or UI. | High | Server-side filtering with deterministic negative tests; no client-side trust of `access` front matter; audit every search resultset. |
| Late index jobs or generation races could serve stale content. | Medium | Single-writer CAS per `(space_id, profile_id)`; ancestry-based generation checks; reconciliation loop between Git HEAD and active pointer. |

### Phase B Definition of Done

- [ ] All B01–B28 tasks are `DONE` or `VERIFIED` with live/synthetic evidence.
- [ ] Live Keycloak/OpenLDAP identity flows pass stable-ID, nested groups, empty-group revocation and rename survival.
- [ ] Session service validates tokens, supports refresh/logout, propagates revocation and binds requests to GO with verified stable_id.
- [ ] Retrieval API returns ACL-filtered exact/semantic/hybrid results with citations, `STALE_SNAPSHOT`/`LIMIT_EXCEEDED` shapes, and rejects inactive preflight.
- [ ] Index worker builds from exact published `main_sha`, advances active pointer atomically, and full/incremental equivalence is verified.
- [ ] No document-level ACL inside a single Space is introduced without a separate ADR.
- [ ] Evidence is recorded in `specs/corporate-kb/evidence/b*/` and raw artifacts in `_bmad-output/test-artifacts/b*/`.

## 12. Phase C plan — Ingestion / source connectors

Implements file upload, connector framework, parsing/indexing pipeline and content-standard enforcement.

### Epic C.1 — File upload and media handling

| Field | Value |
|---|---|
| ID | C.1 |
| Title | File upload and media handling |
| Goal | Accept raw file/media uploads, stage them in MinIO/object store with ACL/version/hash, and produce deterministic dry-run reports without canonical writes. |
| Scope boundaries | Uses MinIO as the object store per sprint-status decision G1-D5. Object-store ACL production hardening is Phase E. |

#### Stories

- **Story C.1.1 — Dry-run upload and object store staging**
  - *As a source owner I upload raw files so that the system stages them and produces a dry-run report without touching canonical Git.*
  - Given a raw file upload
    - When it is received
    - Then it is stored as an immutable/versioned object with SHA-256 and object ACL
  - Given a batch of uploads
    - When dry-run runs
    - Then it returns path→ID map, provenance, links/anchors, attachment manifests, original/extracted hashes, losses and errors
  - Given dry-run mode
    - When the job completes
    - Then zero canonical Git writes have occurred

- **Story C.1.2 — Media classification and critical-media gating**
  - *As a platform I classify media so that critical content is not indexed without human review.*
  - Given an uploaded PDF/PPTX with embedded images
    - When media classification runs
    - Then it labels each image as decorative, illustrative, substantive, critical or handwritten per content-standard 2.3 A7
  - Given a critical media item
    - When the parser encounters it
    - Then indexing is blocked until manual transcription/review is recorded
  - Given a decorative media item
    - When the page is indexed
    - Then it is excluded from the index and not surfaced in search

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| C01 | Implement file upload API and MinIO object-store adapter | `src/ingestion/app/routers/upload.py`, MinIO client | M | TODO |
| C02 | Implement object ACL/version/hash staging and assets manifest | Object-store wrapper, `kb_index`/`kb_ops` asset registry | M | TODO |
| C03 | Implement dry-run reporter (path→ID, provenance, attachments, errors) | Ingestion service, report schema | M | TODO |
| C04 | Implement media classification service | Media classifier, content-standard A7 rules | M | TODO |

### Epic C.2 — Connector framework

| Field | Value |
|---|---|
| ID | C.2 |
| Title | Connector framework |
| Goal | Provide a secure, proposal-only connector framework for GitLab repos, file-system folders and generic webhooks. |
| Scope boundaries | Connectors submit proposals to GO only; they never push to `main`, merge or auto-apply. One outstanding proposal per source object. |

#### Stories

- **Story C.2.1 — Source registry and connector registration**
  - *As a source owner I register an external source so that the system tracks ownership, mode and cursors.*
  - Given a source with a stable owner identity, ownership_mode and cursor policy
    - When it is registered
    - Then the source registry stores `seen`/`proposed`/`merged` cursors per source object
  - Given the same source object changes twice
    - When the second change is detected before the first proposal is merged
    - Then the system maintains at most one outstanding proposal per source object
  - Given a source object hash is unchanged
    - When the connector polls
    - Then it performs an idempotent no-op

- **Story C.2.2 — GitLab repo connector**
  - *As a platform I sync a GitLab repository so that changes become GO proposals.*
  - Given a configured binding to a source GitLab repo
    - When a new commit is detected
    - Then the connector prepares a ProposalRecord with provenance and submits it to GO as a proposal-only operation
  - Given a source-managed update conflicts with an existing curated edit
    - When the proposal is reviewed
    - Then the conflict is surfaced and auto-merge is denied
  - Given the connector credential
    - When it is scoped
    - Then it has no merge, index or grant permissions

- **Story C.2.3 — File-system and webhook connectors**
  - *As a source owner I connect a file share or webhook so that changes are captured securely.*
  - Given a file-system connector watching a path
    - When a file changes
    - Then a source event is queued, deduplicated and mapped to a source object
  - Given a generic webhook
    - When it fires with a valid signature
    - Then the payload is verified and a proposal is prepared after source identity check
  - Given an invalid webhook signature
    - When it arrives
    - Then it is rejected and logged

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| C05 | Implement source registry schema and API | `src/ingestion/app/models/sources.py`, registry API | M | TODO |
| C06 | Implement GitLab repo connector (proposal-only) | `src/ingestion/connectors/gitlab_repo.py` | L | TODO |
| C07 | Implement file-system connector with durable cursor | `src/ingestion/connectors/filesystem.py` | M | TODO |
| C08 | Implement generic webhook connector with signature verification | `src/ingestion/connectors/webhook.py` | M | TODO |
| C09 | Implement connector identity/credential scoping | Connector credential vault, GO proposal capability binding | M | TODO |

### Epic C.3 — Parsing pipeline

| Field | Value |
|---|---|
| ID | C.3 |
| Title | Parsing pipeline |
| Goal | Convert DOCX/PDF/PPTX/HTML and other supported formats into canonical markdown while preserving structure and provenance. |
| Scope boundaries | Uses upstream extraction seams where possible; Docling integration is evidence-gated per T17. Extraction model licenses and egress are tracked in the provider inventory. |

#### Stories

- **Story C.3.1 — DOCX/PDF/PPTX/HTML extraction**
  - *As a platform I parse common formats so that canonical markdown is produced with preserved structure.*
  - Given a DOCX file with tables
    - When the parsing pipeline runs
    - Then the output markdown preserves table headers, rows and merged cells
  - Given a PDF with text layer
    - When it is parsed
    - Then structure (headings, paragraphs, lists) is extracted and page provenance is recorded
  - Given a malformed, encrypted or unsafe input
    - When the parser runs
    - Then it is rejected with a clear error and no partial content enters the corpus

- **Story C.3.2 — Evidence-gated extraction route activation**
  - *As an operator I enable extraction routes only after they pass quality gates.*
  - Given a new extractor (e.g., Docling)
    - When its golden/loss fixtures are evaluated
    - Then it is activated only if quality and license checks pass
  - Given an extractor fails quality gates
    - When a route is requested
    - Then the system falls back to an approved route and logs the reason
  - Given PII/permitted-profile constraints
    - When extraction uses an external provider
    - Then it is blocked for `pii_permitted` content unless the provider is inside the approved perimeter

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| C10 | Implement parsing pipeline for Markdown/DOCX/PDF/HTML | `src/ingestion/parsers/`, extractor adapters | L | TODO |
| C11 | Integrate Docling or upstream extraction seam as evidence-gated route | Ingestion config, evidence fixture runner | M | TODO |
| C12 | Implement three-level quality check (count, LLM compare, human spot-check) | Quality checker, review queue integration | M | TODO |
| C13 | Implement extraction provenance and converter versioning | Parsed document metadata, `origin` front matter | M | TODO |

### Epic C.4 — Content-standard enforcement and ingestion job queue

| Field | Value |
|---|---|
| ID | C.4 |
| Title | Content-standard enforcement and ingestion job queue |
| Goal | Enforce canonical front-matter-v2, data profiles and data barrier; run ingestion jobs with retries, dead-letter and observability. |
| Scope boundaries | Content-standard enforcement runs before any canonical write or proposal. Controlled bulk load is allowed only in unpublished `main` before cutover. |

#### Stories

- **Story C.4.1 — Front-matter and data-profile validation**
  - *As a content operator I validate that every page follows canonical front-matter-v2 and the chosen data profile.*
  - Given a parsed page
    - When validation runs
    - Then it rejects `access`, arbitrary `status`/`owner`/`date` keys and any `additionalProperties`
  - Given a page with `ownership_mode = source_managed`
    - When validated
    - Then `origin` is required and matches the ownership mode
  - Given a `pii_permitted` file without documented legal basis
    - When validated
    - Then it is rejected and no external egress occurs

- **Story C.4.2 — Ingestion job queue, retries and observability**
  - *As an operator I observe ingestion jobs so that failures are retried and dead-lettered.*
  - Given an ingestion job
    - When it fails transiently
    - Then it retries with bounded exponential backoff
  - Given a job fails permanently
    - When the retry budget is exhausted
    - Then it moves to a dead-letter queue with sanitized reason
  - Given the ingestion queue
    - When metrics are scraped
    - Then queue lag, attempt count and outcome are observable

- **Story C.4.3 — Controlled bulk load and cutover boundary**
  - *As a platform I load validated content so that pre-cutover bulk is allowed but post-cutover uses GO/MR.*
  - Given an unpublished Space with no published index and closed user access
    - When controlled bulk load runs
    - Then it pushes to unpublished `main` only
  - Given the Space is activated/cutover
    - When a new content load is requested
    - Then it is routed through GO/MR/human decision and direct bulk push is refused
  - Given a bulk load attempts traversal/symlink/executable/secret/oversized input
    - When validated
    - Then it is rejected

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| C14 | Implement front-matter-v2 and content-standard validator | `src/ingestion/validators/front_matter.py`, schema checker | M | TODO |
| C15 | Implement strict/pii_permitted data barrier gate | Data profile config, legal-basis registry | M | TODO |
| C16 | Implement ingestion job queue, retry and dead-letter | Job queue backend, worker, DLQ | L | TODO |
| C17 | Add ingestion observability (queue lag, attempts, dead-letter) | Metrics, dashboards | S | TODO |
| C18 | Implement controlled bulk loader with cutover state checks | Bulk loader, GO proposal fallback, admission gates | M | TODO |

### Phase C dependencies

- Phase A T12/T15/T16 design implemented (dry-run, source registry, one real connector design).
- Phase B identity/retrieval services live (AuthzContext needed for upload/source authorization, retrieval for index query validation).
- Owner source selection and sample formats (T16/T17).
- MinIO/object-store staging available; production ACL hardening is Phase E.
- content-standard.md 2.3 rules stable.

### Phase C risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Owner has not selected the first source/connector or sample formats. | High | Make connector framework generic; implement GitLab repo and file-system connectors as baseline; leave owner-selected connector as C06 variant; do not block other C tasks. |
| Object-store ACL production recheck is still open (G0-D16/T13/T16). | High | Implement against MinIO with policy-as-code; mark production ACL hardening as Phase E gate; do not claim PASS on production ACL in Phase C. |
| Extraction quality and model licenses are unknown. | Medium | Evidence-gated route activation; keep human-in-the-loop for critical media and prices/legal content; no auto-merge. |
| Source-managed sync could overwrite curated edits if mis-implemented. | High | Connector submits proposals only; GO enforces no auto-merge; conflict detection in review UI. |

### Phase C Definition of Done

- [ ] All C01–C18 tasks are `DONE` or `VERIFIED`.
- [ ] File/media upload stores immutable/versioned objects, returns dry-run reports and performs zero canonical writes in dry-run mode.
- [ ] GitLab repo, file-system and webhook connectors operate proposal-only with scoped credentials.
- [ ] Parsing pipeline produces canonical markdown for Markdown/DOCX/PDF/HTML with provenance and rejects malformed/unsafe inputs.
- [ ] Content-standard validator enforces front-matter-v2 and strict/pii_permitted data barrier.
- [ ] Ingestion jobs run with retries, dead-letter and observability.
- [ ] Controlled bulk load respects unpublished/cutover boundary; post-cutover changes flow through GO/MR.
- [ ] Evidence recorded in `specs/corporate-kb/evidence/c*/` and raw artifacts in `_bmad-output/test-artifacts/c*/`.

## 13. Phase D plan — Backup / restore and disaster recovery

Implements scheduled backups, point-in-time restore and cross-site resilience.

### Epic D.1 — Scheduled backups

| Field | Value |
|---|---|
| ID | D.1 |
| Title | Scheduled backups |
| Goal | Automate periodic backup of Git state, GitLab metadata, object store content, PostgreSQL operational schemas and configuration/secrets policy. |
| Scope boundaries | Per-Space backup packages inside per-client outer perimeter; platform-wide instance backup is only control-plane DR, not a client restore unit. |

#### Stories

- **Story D.1.1 — Git mirror and metadata backup**
  - *As an operator I schedule backups so that Git state and metadata are captured.*
  - Given a Space
    - When the backup job runs
    - Then it produces a Git mirror with all refs, MR notes, protected decision/cutover tags and decisions manifest
  - Given the backup completes
    - Then the package includes `kb_ops` correction-task events, evidence and idempotency records
  - Given a backup failure
    - Then the job alerts and does not mark the backup as complete

- **Story D.1.2 — PostgreSQL and object-store backup**
  - *As an operator I back up operational state and objects so that they can be restored.*
  - Given `kb_authz`, `kb_ops`, `kb_index`
    - When the backup job runs
    - Then durable operational records are captured with schema ownership preserved
  - Given object-store buckets
    - When the backup job runs
    - Then immutable object versions are captured and the assets manifest is exported
  - Given secrets/configuration policy
    - When backed up
    - Then secrets are stored separately and never included in ordinary export logs

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| D01 | Implement Git mirror backup job | Backup worker, `git clone --mirror` orchestration | M | TODO |
| D02 | Implement GitLab MR/note/tag metadata export | GitLab API exporter, metadata manifest | M | TODO |
| D03 | Implement per-Space backup package assembler | Backup package builder, closure manifest | M | TODO |
| D04 | Implement PostgreSQL `kb_authz`/`kb_ops`/`kb_index` backup | DB dump/restore orchestration, role preservation | M | TODO |
| D05 | Implement object-store backup and versioning | Object replication, version preservation | M | TODO |

### Epic D.2 — Point-in-time restore

| Field | Value |
|---|---|
| ID | D.2 |
| Title | Point-in-time restore |
| Goal | Restore a Space to a clean environment with conservative projection rebuild and correction-task reconciliation. |
| Scope boundaries | Restore starts under global managed-write freeze; Git is the canonical source for documents; `kb_ops` operational records are restored from durable backup, not fabricated. |

#### Stories

- **Story D.2.1 — Clean restore and conservative rebuild**
  - *As an operator I restore a Space so that the system rebuilds projections safely.*
  - Given a clean environment and a backup package
    - When restore runs
    - Then it rebuilds `kb_authz`/`kb_ops`/`kb_index` conservatively from Git + backup
  - Given correction tasks exist in the backup
    - When restored
    - Then they are reconciled with linked MRs; tasks are not fabricated, deleted or resolved automatically
  - Given Git-derived state differs from backup projection
    - When reconciliation runs
    - Then affected targets are quarantined until conclusive verification

- **Story D.2.2 — Decisions/assets/grants closure verification**
  - *As a platform I prove closure after restore so that the corpus is consistent.*
  - Given a restored package
    - When the closure check runs
    - Then decisions manifest, assets manifest, policy/grants closure hashes and exact refs match the pre-restore baseline
  - Given an unknown or conflicting merge is found
    - When reconciliation runs
    - Then the target is placed under `recovery_required`/quarantine
  - Given the closure check fails
    - Then the Space is not activated for user access

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| D06 | Implement restore orchestration and conservative rebuild | Restore service, projection rebuilders | L | TODO |
| D07 | Implement correction-task reconciliation after restore | `kb_ops` task reconciler, linked-MR verifier | M | TODO |
| D08 | Implement decisions/assets/grants closure verifier | Closure checker, manifest comparators | M | TODO |

### Epic D.3 — Cross-site replication / DR

| Field | Value |
|---|---|
| ID | D.3 |
| Title | Cross-site replication / DR |
| Goal | Replicate backup packages off-site and rehearse failover within owner-agreed RPO/RTO if required. |
| Scope boundaries | Cross-site replication is owner-required; if not required, this epic produces a documented "not configured" decision and retains single-site backup. |

#### Stories

- **Story D.3.1 — Cross-site replication**
  - *As an operator I replicate backups off-site so that failover is possible.*
  - Given owner-agreed RPO
    - When the replication job runs
    - Then backup packages are copied to the secondary site within the RPO window
  - Given replication lag exceeds threshold
    - When monitored
    - Then an alert fires
  - Given a backup package at the secondary site
    - When inspected
    - Then per-client perimeter isolation is preserved

- **Story D.3.2 — Failover drill**
  - *As an operator I fail over to secondary site so that RTO is met.*
  - Given replicated backups at the secondary site
    - When a failover drill is executed
    - Then restore completes within owner-agreed RTO
  - Given the drill runs
    - Then no cross-client data is exposed and no mixed-client restore unit is created
  - Given the drill finds gaps
    - Then they are recorded as incident/action items before production reliance

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| D09 | Implement cross-site replication job (if required) | Replication worker, secondary storage target | L | TODO |
| D10 | Implement failover drill harness | DR drill runner, RTO timer, verification checks | M | TODO |

### Epic D.4 — Backup integrity, encryption and retention

| Field | Value |
|---|---|
| ID | D.4 |
| Title | Backup integrity, encryption and retention |
| Goal | Verify backup integrity, encrypt backups at rest and enforce owner-configurable retention without exposing customer content. |
| Scope boundaries | Integrity checks run against hashes/manifests; auditors do not need access to raw customer documents. |

#### Stories

- **Story D.4.1 — Integrity verification**
  - *As an auditor I verify backup integrity without reading customer content.*
  - Given a backup package
    - When the integrity job runs
    - Then hashes and closure manifests are verified
  - Given an integrity mismatch
    - When detected
    - Then the backup is marked corrupt and an alert fires
  - Given integrity logs
    - Then they contain no secrets or raw private content

- **Story D.4.2 — Encryption at rest and retention**
  - *As a security operator I enforce encryption and retention so that backups are protected.*
  - Given backup storage
    - When configured
    - Then encryption at rest is enabled
  - Given an owner-configurable retention policy
    - When the retention job runs
    - Then expired backups are removed according to policy
  - Given a retention removal
    - Then an audit record is written and the action is irreversible

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| D11 | Implement backup integrity verification (hashes, manifests) | Integrity checker, manifest parser | M | TODO |
| D12 | Implement encryption at rest for backups | Backup storage encryption, key management integration | M | TODO |
| D13 | Implement retention policy enforcement | Retention scheduler, deletion workflow | S | TODO |
| D14 | Implement DR runbook automation and operator steps | Runbook markdown (operations.md update), automation scripts | M | TODO |
| D15 | Add backup/restore live drill acceptance tests | `tests/d01_backup_restore_live/`, fixtures | L | TODO |

### Phase D dependencies

- Phase A T13a/T13b design implemented (export, mirror, metadata backup, clean restore).
- Phase C object-store implementation (object versions, assets manifest).
- Owner RPO/RTO/retention decisions and backup storage target selection.
- PostgreSQL `kb_authz`/`kb_ops`/`kb_index` schemas stable.

### Phase D risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Owner RPO/RTO/retention are not yet decided. | High | Build single-site backup first; add cross-site replication as optional epic gated by owner decision; do not invent thresholds. |
| Correction-task backup reconciliation is complex and error-prone. | High | Restore starts under global managed-write freeze; reconcile linked MRs before lifting barrier; keep operational records in durable backup separate from Git mirror. |
| Cross-site replication may be unnecessary or cost-prohibitive. | Medium | Make D.3 optional; if owner declines, document decision and retain single-site DR. |
| Backup integrity failures may be discovered too late. | Medium | Run integrity checks after every backup; alert on mismatch; periodic restore drills. |

### Phase D Definition of Done

- [ ] All D01–D15 tasks are `DONE` or `VERIFIED`.
- [ ] Scheduled backups produce per-Space packages with Git mirror, metadata, object versions, `kb_ops` records and separate secrets policy.
- [ ] Restore to a clean environment rebuilds projections conservatively and reconciles correction tasks.
- [ ] Decisions/assets/grants closure is verified after restore; unknown merges trigger quarantine.
- [ ] Backup integrity verification, encryption at rest and retention policy are operational.
- [ ] Cross-site replication and failover drill are either implemented per owner RPO/RTO or explicitly documented as not configured.
- [ ] Evidence recorded in `specs/corporate-kb/evidence/d*/` and raw artifacts in `_bmad-output/test-artifacts/d*/`.

## 14. Phase E plan — Production hardening, Hoster evaluation, second-client deployment

Closes production gates and prepares managed deployment.

### Epic E.1 — Production identity and SLO

| Field | Value |
|---|---|
| ID | E.1 |
| Title | Production identity and SLO |
| Goal | Integrate production Active Directory/LDAP and meet owner-agreed availability/latency/freshness SLOs with monitoring and alerting. |
| Scope boundaries | Production IdP profile is owner-provided; Keycloak/OpenLDAP sandbox from Phase B remains a fallback test fixture. |

#### Stories

- **Story E.1.1 — Production AD/LDAP integration**
  - *As a client I authenticate against production AD/LDAP so that grants are correct within the revocation SLO.*
  - Given a production AD/LDAP profile
    - When a user logs in
    - Then stable-ID, nested-group, mover/leaver and revocation tests pass
  - Given group membership changes
    - When the refresh interval elapses (≤ 15 min)
    - Then access is updated and the revocation SLO (≤ 30 min) is measured
  - Given a long-running session
    - When a sensitive operation is attempted
    - Then groups are re-checked before the payload is exposed

- **Story E.1.2 — Production SLO monitoring and alerting**
  - *As an operator I monitor availability and latency so that SLO breaches are alerted.*
  - Given owner-agreed p95/p99 latency, freshness lag, queue lag and availability targets
    - When metrics are collected
    - Then dashboards display actual vs. target values
  - Given an SLO breach
    - When the threshold is crossed
    - Then an alert fires with severity and affected component
  - Given a freshness lag anomaly
    - When detected
    - Then the on-call runbook is referenced automatically

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| E01 | Implement production AD/LDAP profile adapter | Identity service AD connector, LDAPS/StartTLS | M | TODO |
| E02 | Implement production SLO metrics, dashboards and alerts | Monitoring stack, SLO definitions, alertmanager rules | L | TODO |

### Epic E.2 — Object-store ACL and production storage

| Field | Value |
|---|---|
| ID | E.2 |
| Title | Object-store ACL and production storage |
| Goal | Harden object-store ACL and bucket policies in production and separate attachment credentials from application/browser/agent perimeters. |
| Scope boundaries | Production engine may be MinIO or S3; LocalStack synthetic FAIL from T00 must be replaced by production-engine PASS. |

#### Stories

- **Story E.2.1 — Object-store ACL hardening**
  - *As a platform I enforce object-store ACL in production so that the LocalStack FAIL is resolved.*
  - Given the production object-store engine
    - When the ACL probe runs
    - Then cross-bucket/client isolation passes
  - Given immutable object semantics
    - When an object is versioned or deleted
    - Then versions/delete-markers are preserved per retention policy
  - Given a bucket policy change
    - When reviewed
    - Then it is applied through versioned infrastructure-as-code

- **Story E.2.2 — Secrets and attachment access separation**
  - *As a security operator I separate attachment credentials so that they are outside the agent/browser perimeter.*
  - Given an attachment reference
    - When stored in the assets manifest
    - Then it contains `{object_id, version, sha256, size, media_type, source_ref}` and no mutable URL or secret
  - Given an attachment read request from UI/agent
    - When authorized
    - Then a short-lived presigned URL or proxy is issued, not long-lived credentials
  - Given source credentials
    - Then they are stored in the deployment secret mechanism and never logged

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| E03 | Implement object-store ACL hardening and bucket policy review | IaC bucket policies, ACL probe | M | TODO |
| E04 | Implement attachment credential separation and assets manifest hardening | Attachment proxy/presigned URL service, manifest validation | M | TODO |

### Epic E.3 — Migrations and high availability

| Field | Value |
|---|---|
| ID | E.3 |
| Title | Migrations and high availability |
| Goal | Run owned PostgreSQL migrations with rollback verification and deploy resilient PostgreSQL/GitLab/object-store/retrieval tiers. |
| Scope boundaries | HA topology is owner-selected; single-writer schema ownership must be preserved during failover. |

#### Stories

- **Story E.3.1 — Owned PostgreSQL migrations with rollback**
  - *As an operator I run owned migrations so that upgrades are safe and reversible.*
  - Given an external migrator role
    - When migration runs
    - Then it reaches Alembic head and runtime DDL is denied
  - Given pre/post data-copy checks
    - When migration completes
    - Then checks pass and rollback is rehearsed
  - Given the full 39-table migration/denial matrix
    - When verified
    - Then cross-schema writes are denied for non-owning roles

- **Story E.3.2 — HA for PostgreSQL, GitLab, object store and retrieval**
  - *As an operator I deploy resilient tiers so that failover works without breaking single-writer ownership.*
  - Given an HA PostgreSQL setup
    - When failover is rehearsed
    - Then single-writer schema ownership is preserved and `kb_index` remains rebuildable
  - Given HA GitLab
    - When failover occurs
    - Then merge/notes/tags durability is maintained
  - Given HA object store and retrieval
    - When failover is rehearsed
    - Then RTO targets are met and no cross-client data is exposed

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| E05 | Implement full 39-table migration/denial matrix verification | Migration tests, role/schema denial matrix | L | TODO |
| E06 | Implement PostgreSQL HA/replica failover rehearsal | HA setup, failover scripts, ownership checks | L | TODO |
| E07 | Implement GitLab HA and shared-upgrade coordination | GitLab HA topology, maintenance window orchestration | L | TODO |
| E08 | Implement object-store HA and cross-site replication (if required) | Object-store HA config, replication rules | L | TODO |
| E09 | Implement retrieval service HA and failover | Retrieval service replicas, load balancer health checks | M | TODO |

### Epic E.4 — Hoster white-label and second-client deployment

| Field | Value |
|---|---|
| ID | E.4 |
| Title | Hoster white-label and second-client deployment |
| Goal | Integrate real hoster.ai endpoints and deploy a second client using only config and versioned templates. |
| Scope boundaries | hoster.ai integration is owner-deferred; KIMI remains the approved interim provider per G1-D3. White-label branding is allowed under hoster.by per G1-D7. |

#### Stories

- **Story E.4.1 — Hoster.ai inputs and evaluation**
  - *As hoster.ai I provide endpoints and model IDs so that inference can switch from the interim provider.*
  - Given hoster.ai endpoint/model IDs/credentials/egress rules
    - When configured
    - Then T11 inference harness runs against the real endpoint
  - Given an owner-reviewed golden set
    - When T14 evaluation runs
    - Then quality/safety metrics are measured and human-reviewed
  - Given egress policy
    - When hoster.ai calls are made
    - Then they use approved routes and no unplanned fallback occurs

- **Story E.4.2 — Second-client tenant onboarding**
  - *As a platform team I deploy a second client so that isolation is maintained without a code branch.*
  - Given the config-only dedicated deployment template
    - When a second client is deployed
    - Then namespace isolation, per-client credentials/backups and inherited `gitlab_mode` are verified
  - Given two clients on the same shared GitLab instance
    - When cross-client negative tests run
    - Then one client cannot read, propose, merge, export or restore the other's Spaces
  - Given a dedicated second client
    - When deployed
    - Then it uses separate endpoints, secrets, storage, network and backups from the first client

- **Story E.4.3 — Full G3 operational acceptance**
  - *As an operator I complete G3 acceptance so that the system is production-ready.*
  - Given the T18b harness
    - When it runs
    - Then clean restore, correction-task reconciliation, metrics/alerts/runbooks, upgrade/rollback rehearsal and cross-client negative controls pass
  - Given G3 acceptance passes
    - Then the deployment is approved for production traffic
  - Given any G3 check fails
    - Then the failure is recorded, remediated and re-verified before go-live

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| E10 | Implement hoster.ai provider adapter and egress config | Provider inventory, hoster.ai client, egress rules | M | TODO |
| E11 | Implement second-client tenant onboarding automation | Tenant provisioning, config templating | L | TODO |
| E12 | Implement config-only dedicated deployment template | Helm/Kustomize/compose templates, versioned config | M | TODO |
| E13 | Implement cross-client negative controls and isolation tests | Multi-tenant test harness, isolation assertions | M | TODO |
| E14 | Implement G3 operational acceptance harness | T18b runner, runbook rehearsal automation | L | TODO |

### Epic E.5 — Security audit and egress/ingress policy

| Field | Value |
|---|---|
| ID | E.5 |
| Title | Security audit and egress/ingress policy |
| Goal | Close security review findings, remediate pen-test issues and finalize egress/ingress policies. |
| Scope boundaries | Security audit is owner-authorized; no production penetration testing without explicit owner approval. |

#### Stories

- **Story E.5.1 — Security audit and pen-test remediation**
  - *As a security operator I audit the platform so that vulnerabilities are remediated.*
  - Given security review or pen-test findings
    - When remediation is planned
    - Then each finding is mapped to a task with owner and deadline
  - Given a remediated finding
    - When re-tested
    - Then regression tests pass and evidence is recorded
  - Given high/critical findings
    - When unresolved
    - Then production go-live is blocked

- **Story E.5.2 — Egress/ingress policy finalization**
  - *As a platform I finalize network policies so that only approved providers are reachable.*
  - Given the approved provider inventory
    - When egress rules are applied
    - Then unplanned fallback is blocked at the network layer
  - Given ingress rules
    - When applied
    - Then only required ports/endpoints are exposed
  - Given provider calls
    - When logged
    - Then they include provider ID, model ID, data profile and outcome for audit

#### Technical tasks

| ID | Title | Files / components | Size | Status |
|---|---|---|---|---|
| E15 | Implement security audit findings remediation | Security backlog, fixes, regression tests | M | TODO |
| E16 | Implement egress/ingress policy enforcement | NetworkPolicy/firewall rules, egress proxy | M | TODO |
| E17 | Implement pen-test regression suite | Adversarial tests, automated re-checks | M | TODO |

### Phase E dependencies

- Phases B-D completed or at least stable enough to harden.
- Production AD/LDAP access and profile (owner-provided).
- hoster.ai endpoint/model IDs/credentials/egress rules (owner-deferred from G1-D3).
- Second-client resources and tenant profile decision.
- Owner SLO/budget/HA/retention decisions.

### Phase E risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| hoster.ai inputs are deferred (T11 BLOCKED); switching from KIMI may not happen before launch. | High | Keep KIMI as approved interim provider; implement provider adapter port so hoster.ai switch is config-only when inputs arrive; do not hardcode provider. |
| Production AD/LDAP and SLO targets are not yet available. | High | Build against Keycloak/OpenLDAP sandbox in Phase B; production integration is a Phase E gate; do not claim PASS without production evidence. |
| Second-client environment/resources not provisioned. | High | Use synthetic two-client fixtures for development; real second-client deployment gated by owner resources and T18a/T18b. |
| Security/pen-test findings may force scope changes late. | High | Run continuous adversarial suites from Phase B; maintain security backlog; require owner approval for any production pen-test. |

### Phase E Definition of Done

- [ ] All E01–E17 tasks are `DONE` or `VERIFIED`.
- [ ] Production AD/LDAP integration passes stable-ID, group and revocation SLO tests.
- [ ] Production SLO monitoring/alerting is operational with owner-agreed targets.
- [ ] Object-store ACL hardening passes production-engine probe; attachment credentials are separated.
- [ ] PostgreSQL/GitLab/object-store/retrieval HA failover is rehearsed; single-writer ownership preserved.
- [ ] hoster.ai adapter is validated against real endpoint or explicitly remains on KIMI with owner decision.
- [ ] Second-client deployment is verified with cross-client negative controls.
- [ ] G3 operational acceptance (T18b) passes.
- [ ] Security audit/pen-test findings are remediated; egress/ingress policies enforced.
- [ ] Evidence recorded in `specs/corporate-kb/evidence/e*/` and raw artifacts in `_bmad-output/test-artifacts/e*/`.

## 15. Planning assumptions

The following assumptions and deferred items are recorded so that phase plans can start without inventing owner decisions:

- **Deferred per ADR-19:** T19 retrieval engine evolution and T20 Fast/Trust/Scale policies are not scheduled. No tasks are created for OpenSearch stack swap, cache/routing layers or trust policies until T14 measured benchmarks and a separate business gate/ADR exist.
- **Deferred per spec v1.3 / ADR-16:** Page-level ACL inside a single Space, realtime CRDT collaborative editing, universal two-way sync, routine/self-service admin break-glass product capability and privacy hard purge are out of MVP scope. Their implementation requires a dedicated ADR.
- **Owner inputs still required before Phase B can start:** production IdP profile (Phase E), embedding model dimensions/chunking/thresholds (B.4), hoster.ai endpoint/model IDs (E.4). Phase B can proceed with Keycloak/OpenLDAP sandbox and a placeholder embedding model, but final acceptance of B.4 and Phase E gates is blocked until these inputs are provided.
- **Object-store ACL:** MinIO is sufficient for development (G1-D5). Production-engine ACL hardening is Phase E; Phase C tasks do not claim production ACL PASS.
- **RPO/RTO/retention/cross-site replication:** These are owner decisions. Phase D includes optional cross-site replication; if the owner decides single-site backup is sufficient, D.3 tasks are closed as "not configured" with documented rationale.
- **Task state convention:** Ungated new phase tasks are initialized as `TODO`; externally gated Epic 14 rows are initialized as `BLOCKED`; deferred planning reserves create no executable task. Tasks transition through `IN_PROGRESS → VERIFIED → DONE` only after their gates open, with `BLOCKED` used when an external gate is unavailable. No task is marked `DONE` from design or synthetic harness alone.
- **No new ADRs/contracts/runbooks:** This planning update does not create new design ADRs, contracts or operational runbooks. It references existing ADR-03, ADR-05, ADR-10, ADR-15, ADR-16, ADR-17 and ADR-19.

## 16. Proposed Epic 14 backlog — planning only / BLOCKED

**Status boundary:** Epic 14 — Editorial Publishing является approved-as-proposed planning structure, а не изменением действующих R01–R18/I01–I14/A01–A36 или разрешением implementation. Stories ожидают batch review; product code, ADR/contracts, migrations, runbooks, nightly schedules, provider calls, egress и production changes не активированы. Полные requirements/AC/evidence: [epics.md](../../_bmad-output/planning-artifacts/epics.md#proposed-implementation-phase-epic-14-editorial-publishing). Impact/handoff: [Sprint Change Proposal 2026-11-12](../../_bmad-output/planning-artifacts/sprint-change-proposal-2026-11-12.md).

Этот раздел не меняет G1/WP-00–WP-05, E00–E13/T00–T20, readiness percentages или deferred T19/T20. Использовать полное `Epic 14 / Story 14.x (Fxx)`; сокращение `E14` запрещено, поскольку уже занято Phase E acceptance task.

| Story | User outcome | Dependencies | Owner/design gates | ED requirement navigation | State | Remaining evidence |
|---|---|---|---|---|---|---|
| **14.1 (F01)** | Один organic Open WebUI KB module с reproducible overlay/BFF и upgrade-safe seams | G1 live acceptance; существующие E09–E11 seams | Current-phase permission; pinned baseline; no upstream migrations | ED-F-01/07/15/17; ED-N-08/09/12; ED-UX-01/02/05/07 | **BLOCKED** | Pristine reconstruction, collision/dirty-tree/idempotence/cleanup tests, BFF auth, Notes/chats regression, Vitest/direct Vite, modified-file allowlist |
| **14.2 (F02)** | Department owner назначает/отзывает scoped editors среди участников отдела, включая себя | F01; G1 | Editorial registry/personal-grant lifecycle, governed grant writes и `kb_authz` schema-ownership ADR/spec | ED-F-04/05/06/09/16/17; ED-UX-03 | **BLOCKED** | Self-assignment, non-member/cross-scope denial, grant idempotency/CAS, mover/joiner/leaver, fresh revocation, browser/API parity, audit/export/rebuild |
| **14.3 (F03)** | Assigned editor публикует own/employee final version без MR и второго review | F01+F02 | No-MR canonical publication, target-writer/protection, shared lock/recovery и R/I amendments; live GitLab probes | ED-F-02/03/04/07/15/16/17; ED-UX-02/07 | **BLOCKED** | Zero-MR create/update, takeover terminal disposition, principals/audit tag/trailers, stale base/race/replay/crash/quarantine, export/restore и ordinary MR regression |
| **14.4 (F04)** | Author получает простое verified published/published-with-edits/rejected notification | F01+F03; existing MR closure | Notification event/identity/retention contracts и GO-owned outbox schema | ED-F-02/08/15/16/17; ED-UX-01/05 | **BLOCKED** | Canonical-byte comparison, post-verification timing, outbox retry/DLQ/replay/dedupe, issuer+sub bridge, socket-after-commit, inbox a11y/XSS/revocation и two-user live acceptance |
| **14.5 (F05)** | Chief editor видит typed dependencies и company-wide triggers; отделы получают review signal | F02+F03+F04; F06 не требуется | Editorial ownership/dependency/event contracts, graph storage и cross-Space privacy design | ED-F-04/09/10/11/15/16/17; ED-UX-04/05 | **BLOCKED** | Stable-ID graph, cycles/orphans/duplicates, exact-snapshot fanout/coalescing, cross-Space denial, dashboards, unassigned/partial states, backup/rebuild/index closure |
| **14.7 (F07)** | Только code-proven deterministic link repairs публикуются автоматически | F03+F05; F06 не требуется | Deterministic transformation/auto-publication/service-attribution ADR; source-managed decision; independent kill switch | ED-F-07/10/13/14/15/16/17; ED-UX-07 | **BLOCKED** | Independent recomputation/AST whitelist, semantic-infiltration/unsafe-link negatives, isolated credential, zero-MR live service record, stale/race/restart/kill-switch, export/restore/index |

### Deferred planning reserve — not an executable task

**Story 14.6 (F06), nightly semantic harmonization proposals:** зарезервирована в Epic 14 для будущих bounded agents, которые создают только MR для assigned human editors. Состояние planning — **DEFERRED**, но задача в executable tracker не создаётся и task state не присваивается. Activation требует F05 и отдельных owner decisions о cadence, approved provider/egress, budgets, queue/retention limits и agent-tool contract. Ночной worker, schedule, live provider call и auto-publication этим backlog не разрешаются.

Общий dependency order: `F01 → F02 → F03 → F04 → F05 → {F06, F07}`; F07 не зависит от F06. До fresh readiness PASS и generator/status repair `sprint-status.yaml` вручную не редактируется и не регенерируется из этой пачки.
