# Sprint Change Proposal — Epic 14 Editorial Publishing

Дата: 2026-11-12

Статус: **APPROVED FOR PLANNING CHANGES / APPLIED 2026-11-14; IMPLEMENTATION BLOCKED**

Scope classification: **Major**

Recommended approach: **Direct Adjustment после G1, planning-only в текущей фазе**

Триггер: новая editorial governance модель, подтверждённая пользователем в Party Mode и requirements/epic workflow.

> Этот proposal фиксирует продуктовое направление и конкретную синхронизацию planning/backlog artifacts. Он не является owner-approved ADR, не меняет действующие R01–R18/I01–I14/A01–A36, не разрешает product implementation, migrations, new contracts/runbooks, nightly schedules, provider calls, egress или production changes. Текущий G1/WP-00–WP-05 и статусы E00–E13/T00–T20 сохраняются.

## 1. Issue Summary — проблема и основание

Пользователь утвердил продуктовую модель, в которой:

- обычные сотрудники отправляют изменения через MR;
- явно назначенные human editors могут редактировать и публиковать собственные и employee-authored тексты **без создания MR и без второго review**;
- `kb_admin` и отдельный chief editor имеют global editorial authority; chief editor отвечает за company-common знания;
- department scope owner назначает редакторов только среди участников своего отдела и может назначить себя; editorial permission является per-scope grant, а не должностью;
- автор получает простое `опубликовано`, `опубликовано с правками редактора` или `отклонено`;
- company-common publication создаёт notification trigger для зависимых отделов;
- nightly semantic agents в последующей фазе создают только MR для assigned editors;
- code-proven deterministic link repairs могут публиковаться автоматически;
- реализация должна быть отдельным эпиком с органичным Open WebUI UX и upgrade-устойчивой модульной поставкой.

Действующая модель требует `MR → independent human DecisionRecord → GO real merge` для всех managed changes и запрещает auto-merge (`specs/corporate-kb/spec.md:204-210,220-226,237-251,332-345`). Поэтому новое направление нельзя реализовать как скрытый `if admin` или self-approved DecisionRecord. Требуется отдельный Epic 14, новые canonical publication/grant/dependency/notification contracts и owner-approved ADR/spec amendments после G1.

### 1.1. Подтверждённые входные артефакты

- Requirements и 7 stories: `_bmad-output/planning-artifacts/epics.md:2183-2625`.
- Текущий G1 IN_PROGRESS и live subset, не полный acceptance: `specs/corporate-kb/tasks.md:20-29,44-46`.
- Текущий запрет новых ADR/contracts/runbooks до G1: `AGENTS.md:5-10`.
- MR-only/independent-review/no-auto-merge conflicts: `specs/corporate-kb/spec.md:204-210,220-226`.
- Personal grants сейчас exception, path scopes не read ACL: `specs/corporate-kb/spec.md:273-280`.
- Pinned Open WebUI и upgrade constraints: `specs/corporate-kb/baseline.md:39-45,78-86,90-118`.

### 1.2. Checklist outcome

| Section | Status | Outcome |
|---|---|---|
| 1. Trigger/context | Done | Новое stakeholder requirement, не дефект текущего G1; direct target commit для нового path не проверен |
| 2. Epic impact | Action-needed | Требуется отдельный Epic 14; текущие эпики viable без rollback |
| 3. Artifact conflicts | Action-needed | Publication/grants/dependency/notification/UX/test/export/upgrade impacts; найдены 4 coverage drift в `epics.md` |
| 4. Path forward | Done | Planning-only Direct Adjustment; no rollback/no MVP reduction |
| 5. Proposal components | Done | Major handoff PM/PO + Architect + QA/Security + owner |
| 6. Final review/handoff | Done for planning | Пользователь утвердил planning-only пачку 2026-11-14; Major handoff записан; `sprint-status.yaml` не редактируется |

## 2. Impact Analysis

### 2.1. Epic и story impact

| Область | Влияние | Решение |
|---|---|---|
| G1 / E04 | Employee MR/independent-review flow остаётся нужным и может завершиться неизменным | Не добавлять direct publish в WP-00–WP-05 и не переоткрывать acceptance |
| E00–E01 | Прежние baseline/contract evidence остаются исторически корректными для MR path | Новые probes/vectors выполнять позднее, не переписывать PASS |
| E02/E09 | Нужны editorial registry, personal scoped grants, self-assignment, revocation и per-Space capabilities | F02 после G1 и policy/schema ADR |
| E03 | TipTap/history/exact revisions переиспользуются | Сохранить lossless/full-diff behavior, no CRDT expansion |
| E04/E10 | MR/DecisionRecord/merge path сохраняется для employee/agent/source-managed | F03 добавляет отдельный no-MR PublicationRecord/apply/recovery |
| E05/E12 | Индекс должен обрабатывать verified exact `main` commit независимо от publication route | F05 добавляет typed dependency projections без canonical write |
| E06 | Export/backup/restore должен включать new publication/grant/dependency/outbox evidence | Позднейшие gated amendments |
| E07–E08 | Нужны feature flags, kill switches, scoped credentials и upgrade/second-client evidence | Не активировать nightly/provider по этому proposal |
| E11 | Нужны organic editor/admin/inbox/dashboard UX и reproducible overlay | F01 сначала консолидирует tracked/live implementations |
| E13 | Source-managed MR/human decision сохраняется | F07 исключает source-managed без отдельного ADR |
| Новый Epic 14 | 7 stories F01–F07; initial flow не зависит от nightly agents | F01–F05/F07 BLOCKED; F06 DEFERRED planning reserve |

Новых эпиков сверх Epic 14 не требуется. Порядок: `F01 → F02 → F03 → F04 → F05 → {F06, F07}`; F07 не зависит от F06.

### 2.2. Normative и architecture conflicts

1. **No-MR human publication:** требует replacement canonical publication record, protected Git anchor/trailers, exact parent/content verification, idempotency, target serialization, recovery/export/restore и GitLab target-writer profile. Browser/human direct GitLab push не разрешается.
2. **Personal editorial grants:** требуется versioned registry и governed assignment/revocation lifecycle. Галочка не может быть просто `users.is_editor`; self-assignment + self-publication должны быть одним явно принятым ADR решением.
3. **Global roles:** `kb_admin` и chief editor материализуются в independently authorized per-Space capabilities, без read-ACL bypass или infrastructure/GitLab admin equivalence.
4. **Automation:** semantic agents остаются proposal-only. Deterministic writer — отдельный bounded operation class с independent recomputation, service attribution и kill switch; model не сертифицирует собственный diff.
5. **Schema ownership:** Identity/`kb_authz` владеет grants, GO/`kb_ops` — publication/outbox/recovery, CI/`kb_index` — dependency projections. Cross-schema writes/FK запрещены; new migrations требуют owner approval.
6. **Cross-Space dependencies:** текущие same-Space link contracts недостаточны. До отдельного privacy/contract design cross-Space automatic processing остаётся disabled.
7. **Notifications:** нужны durable outbox, dedupe/retry/DLQ, structured issuer+subject mapping и authorized Open WebUI bridge. GO не пишет upstream notification tables напрямую.

### 2.3. UX/accessibility impact

- Employee `Отправить на согласование`, editor `Опубликовать` / `Редактировать и опубликовать`, department scope settings, chief-editor dependency dashboard и automatic-maintenance audit view.
- Full exact diff и principals остаются до publication; statuses различают draft/pending/published/indexed/conflicted/recovery/unassigned.
- Inbox сохраняет unread/read, keyboard/screen-reader/i18n/XSS-safe behavior; special message ровно `опубликовано с правками редактора`, diff в уведомлении не обязателен.
- Server-derived capabilities управляют действиями; hiding buttons не является authorization.
- Open WebUI v0.13.0 не имеет достаточного general-purpose plugin API. Packaging: repo-owned authenticated frontend module + thin BFF + enumerated compatibility patches + fail-closed manifest/upgrade tests. Автоматическая совместимость с будущими версиями не обещается.

### 2.4. Secondary artifacts и verification impact

Потребуются будущие versioned schemas/OpenAPI/events/projection mappings/export manifests, synthetic fixtures, live GitLab/IdP/PostgreSQL/browser tests, concurrency/crash/recovery, backup/restore и pristine upgrade rehearsals. Старые A17/A30/A14/A34 assertions для MR/source-managed paths сохраняются; новые ED test matrices не должны ослаблять их интерпретацию.

`operations.md`, normative `spec.md`, ADR/contracts и runbooks **не редактируются этой пачкой** из-за текущего G1 gate.

## 3. Recommended Approach — Direct Adjustment после G1

### 3.1. Выбранный путь

**Planning-only Direct Adjustment:** сохранить текущий MVP/G1 без изменений и добавить Epic 14 как отдельный future epic с явными owner/ADR/readiness gates.

| Альтернатива | Оценка | Решение |
|---|---|---|
| Direct Adjustment | Сохраняет полезный employee MR flow и создаёт отдельный future workstream; требует Major governance/design work | **Выбрано** |
| Potential Rollback | Новый product code ещё не реализован; rollback текущего MR path удалил бы необходимый fallback и не упростил задачу | Не применять |
| MVP Review / reduction | Текущий MVP достижим без Epic 14; сокращение целей не требуется, Epic 14 переносится за G1 | Не требуется |

Scope classification — **Major**, поскольку меняются canonical publication semantics, personal authority model и unattended write boundary, даже если текущая пачка содержит только planning edits.

### 3.2. Effort и timeline impact — LOW confidence, не commitment

| Work | Person-days |
|---|---:|
| Major SCP, owner ADR/spec package и fresh readiness | 10–18 |
| F01 module/pristine overlay | 12–20 |
| F02 editorial grants | 12–20 |
| F03 no-MR publication/takeover | 25–40 |
| F04 durable notifications | 15–25 |
| F05 dependency graph/triggers | 18–30 |
| F07 deterministic writer | 20–35 |
| Cross-story browser/security/fault/export/restore/upgrade acceptance | 18–30 |
| **Initial total, excluding F06** | **130–218** |
| **F06, separately activated later** | **25–45** |

При commitment capacity 19.2–20.4 person-days/two-week sprint это ориентировочно **7–12 sprints / 14–24 calendar weeks после prerequisites** для initial scope. F06 добавляет ориентировочно 1–3 sprint equivalents. Это сценарные диапазоны при предполагаемой команде из `delivery-estimates.md`, не назначение сроков/capacity. Текущий G1 и owner waiting time дополнительно и не оценены.

### 3.3. Риски

| Риск | Уровень | Mitigation |
|---|---|---|
| Второй canonical write path ослабит audit/recovery | High | Отдельный PublicationRecord/ADR, shared lock/barrier, live Git-derived reconciliation, no fake DecisionRecord |
| Personal self-grant приведёт к privilege escalation | High | Scoped versioned grants, membership/grantor checks, fresh revocation, audit, cross-department negatives |
| Agent маскирует semantic edit под deterministic link fix | High | Independent recomputation/AST whitelist, separate credential/worker, semantic infiltration negatives |
| Notification сообщит success до фактической публикации | High | Post-Git-verification outbox, dedupe/replay, no success on timeout/quarantine |
| Open WebUI upgrade удалит functionality | High | Repo-owned module/BFF, enumerated patches/hashes, pristine fail-closed rebuild, feature-disabled rollback |
| Planning generator сбросит статусы или активирует F06 | High | Не hand-edit YAML; сначала readiness, generator exclusion/fix и user-confirmed regeneration |
| Scope creep остановит текущий G1 | High | Все F01–F05/F07 BLOCKED; F06 reserve only; no current-phase implementation |

## 4. Detailed Change Proposals — batch OLD→NEW

### 4.1. `_bmad-output/planning-artifacts/epics.md`

**Проблема:** coverage review после final validation нашёл четыре несоответствия. Их нельзя оставлять с безусловным `finalValidationStatus: passed`.

**OLD:**

- Story 14.1 Requirements не содержит ED-F-07, хотя coverage table назначает её 14.1.
- Coverage `ED-F-10 | 14.5`, хотя Story 14.7 объявляет ED-F-10.
- Coverage `ED-F-11 | 14.5`, хотя Story 14.6 объявляет ED-F-11.
- Coverage `ED-F-17 | 14.1–14.7`, но Stories 14.2–14.7 не объявляют ED-F-17 в Requirements.

**NEW:**

1. В Story 14.1 Requirements добавить `ED-F-07`.
2. В Stories 14.2–14.7 Requirements добавить `ED-F-17`.
3. Заменить coverage rows:

```text
OLD: | ED-F-10, ED-F-11 | 14.5 |
NEW: | ED-F-10 | 14.5, 14.7 |
     | ED-F-11 | 14.5, 14.6 |
```

4. Перед исправлениями установить `status: draft`, `finalValidationStatus: needs-targeted-revalidation`; после reverse-check каждого ED-F/ED-UX и dependency table вернуть `status: final`, `finalValidationStatus: passed`.

**Rationale:** story-level declarations и reverse coverage должны совпадать; статус validation не может скрывать поздно найденный drift.

### 4.2. `specs/corporate-kb/tasks.md`

**OLD:** файл заканчивается `## 15. Planning assumptions`; Epic 14 отсутствует. Правило `:1195` говорит, что все новые phase tasks инициализируются TODO.

**NEW:**

1. Дополнить правило:

```text
OLD: All new phase tasks are initialized as `TODO`.
NEW: Ungated new phase tasks are initialized as `TODO`; externally gated Epic 14 rows are initialized as `BLOCKED`; deferred planning reserves create no executable task.
```

2. Добавить после `:1196` `## 16. Proposed Epic 14 backlog — planning only / BLOCKED` с:

- non-normative status boundary и ссылкой на `epics.md`/этот SCP;
- таблицей `Story | User outcome | Dependencies | Owner/design gates | ED navigation | State | Remaining evidence`;
- F01–F05/F07 со state **BLOCKED**;
- F06 только под `Deferred planning reserve — not an executable task`, без state/task assignment, schedule/provider/egress;
- точной dependency chain и evidence categories, без dates/estimates;
- запретом сокращения `Epic 14` до `E14`, поскольку E14 уже занято Phase E task.

**Rationale:** backlog виден в live tracker, но не становится текущим implementation scope или новым lifecycle state.

### 4.3. `specs/corporate-kb/planning-input.md`

**OLD:** `:5-7` ограничивает документ существующими E00–E08/T00–T20 и говорит «не список новых эпиков или stories»; Epic 14 inputs отсутствуют.

**NEW:**

1. Уточнить `:5-7`: основной пакет по-прежнему покрывает E00–E08/T00–T20; отдельный §17 добавляет non-normative proposed Epic 14 и не меняет approved scope/capacity.
2. Добавить однострочные ссылки на §17 после workstream table, dependency discussion, vertical-slice table и owner decisions, не вставляя Epic 14 в canonical tables/critical path.
3. Добавить `## 17. Proposed Epic 14 planning input — non-normative and blocked` с:

- user outcomes/non-goals, сохранением repository=Space, fresh ACL и employee MR flow;
- ED-F/ED-N/ED-A/ED-UX navigation без присвоения новых approved R/I/A;
- dependency graph и ownership Open WebUI/GO/Identity/CI/QA;
- owner inputs из ED-OPEN;
- DoR/DoD, fixtures, integration/browser/fault/restore/upgrade evidence;
- F06 deferral и separate activation decision;
- отсутствием capacity/calendar commitments.

**Rationale:** planning package описывает новый workstream, не переписывая approved critical path и normative requirements.

### 4.4. `specs/corporate-kb/traceability.md`

**OLD:** canonical matrices заканчиваются coverage audit в §6; proposed Epic 14 navigation отсутствует.

**NEW:**

1. Добавить в §6 note: proposed Epic 14 tracked separately и не меняет R/I/A counts/statuses/coverage totals; A37+ не создаётся.
2. Вставить перед link definitions `## 7. Proposed Epic 14 design navigation` с таблицей по каждому F01–F07:

- ED requirement links;
- existing R/I/A **candidate dependency/conflict navigation only**, не Full/Supporting coverage;
- reusable E09–E13/components/contracts;
- required future ADR/spec/contract decisions;
- planned evidence, backup/export/restore и upgrade impact;
- implementation state BLOCKED; F06 listed separately as deferred reserve, не active mapping.

**Rationale:** новая работа traceable без falsification утверждённой normative coverage.

### 4.5. `specs/corporate-kb/test-plan.md`

**OLD:** полный A01–A36 plan заканчивается §10; Epic 14 tests отсутствуют.

**NEW:**

1. Добавить навигационные ссылки из §5 fixtures и §9 traceability к новому proposed разделу.
2. Добавить `## 11. Proposed Epic 14 test design — DESIGN NOT EXECUTED / BLOCKED`:

- fixture families: scopes/grants, employee/editor canonical-byte pairs, publication anchors, outbox, dependency graphs, unsafe links, cross-Space negatives;
- unit/contract/browser/real GitLab/IdP/PostgreSQL/security/concurrency/crash/restore/upgrade levels;
- per-story matrices F01–F05/F07;
- exact environment/commands/results/blocked checks/sanitized evidence requirements;
- machine output `_bmad-output/test-artifacts/epic14/` и sanitized evidence `specs/corporate-kb/evidence/epic14/` только после authorization;
- F06 как reserved future test design, без registered nightly schedule или live provider claim.

**Rationale:** security/recovery/upgrade requirements попадают в plan до implementation, не создавая новых acceptance IDs или PASS.

### 4.6. `specs/corporate-kb/delivery-estimates.md`

**OLD:** существуют только historical first-two-sprint scenarios до §5; Epic 14 impact не записан.

**NEW:** добавить `## 6. Proposed Epic 14 scenario — LOW confidence, not a commitment` с диапазонами из §3.2, prerequisites, per-story ranges, cross-story acceptance, F06 exclusion, owner waiting exclusion и отсутствием displacement текущего G1.

**Rationale:** Major scope виден в capacity planning без изменения historical commitments или назначения дат.

### 4.7. `operations.md`, normative spec, ADR/contracts/runbooks

**OLD:** действующие правила MR-only/no-auto-merge и current G1 restriction.

**NEW:** **никаких правок в этой пачке.** После G1 и owner approval создать отдельные ADR/spec/contract/runbook amendments для publication records, grants, dependencies, notifications, deterministic writer, backup/recovery и operations thresholds.

**Rationale:** planning change не должен молча переписывать normative/security boundary или нарушать фазовый gate.

### 4.8. `_bmad-output/implementation-artifacts/sprint-status.yaml`

**OLD:** YAML утверждает G1/Phase B DONE, тогда как `tasks.md` сохраняет G1 IN_PROGRESS; generator validation не распознаёт nested phases, dry-run видит Epic 14/F06 как обычный backlog и сообщает dropped orphans.

**NEW:** **не редактировать вручную и не регенерировать этой пачкой.** После batch review/readiness:

- согласовать authoritative status table по evidence, предпочитая lower evidenced state;
- исправить/ограничить parser так, чтобы deferred F06 не попадал в executable backlog;
- выполнить evidence-gathering/fix flow и user-confirmed `--fresh --set` только после readiness PASS;
- явно разрешить все dropped orphans, не принимая all-backlog reset.

**Rationale:** checklist 6.4 остаётся Action-needed; невозможно безопасно обновить tracking до устранения provenance/generator drift.

## 5. Implementation Handoff

### 5.1. Scope и recipients

**Major — Product Manager/Product Owner + Solution Architect + QA/Security + owner.** Developer implementation не активируется этой пачкой.

| Роль | Ответственность |
|---|---|
| PM/PO | Batch review Epic 14, backlog sequencing, preservation of current G1/MVP, owner decision log |
| Solution Architect | После G1: canonical publication, editorial policy/grants, schema ownership, dependency/privacy, Open WebUI seam/upgrade design и ADR/spec amendments |
| QA/Security | Reverse coverage audit, negative/race/crash/recovery/upgrade matrices, live evidence gates, generator safety/readiness |
| DevOps/Open WebUI/GO/Identity owners | После разблокировки: F01–F05/F07 по stories; owning migrations/credentials/feature flags/rollback |
| Owner | Approval этого planning SCP, затем отдельные ADR/spec/source-managed/provider/budget/retention/nightly decisions |
| Developer agents | Только planning edits в этой пачке; product code не активируется до соответствующих gates |

### 5.2. Success criteria этой planning пачки

1. Исправлены все четыре ED coverage drift в `epics.md`, targeted revalidation возвращает `final`/`passed`.
2. F01–F05/F07 присутствуют в `tasks.md` как **BLOCKED**; F06 не создаёт executable task.
3. `planning-input.md`, `traceability.md`, `test-plan.md`, `delivery-estimates.md` содержат proposed Epic 14 без изменения canonical R/I/A/T/E coverage/statuses.
4. Текущие G1/WP-00–WP-05, E00–E13/T00–T20, historical evidence и deferred T19/T20 не изменены.
5. Нет новых ADR/contracts/migrations/runbooks/nightly schedules/provider/egress/production changes.
6. `sprint-status.yaml` не hand-edited; generator/status drift задокументирован как subsequent Action-needed.
7. Все изменения sanitized, без secrets/real client documents/unredacted personal data.

### 5.3. Gates перед implementation

1. Explicit user approval этого SCP и batch review stories.
2. G1 live acceptance и текущий phase gate разрешает новый workstream.
3. Owner-approved ADR/spec/contracts для F02/F03/F04/F05/F07 и fresh readiness review.
4. Live sandbox proof для direct target writer/protection/recovery; separate activation for F06 and source-managed F07 where applicable.
5. Deterministic tracking regeneration только после generator/readiness repair и user-confirmed status table.

### 5.4. Deliverables после approval

- Обновлённый `epics.md` с corrected coverage и targeted revalidation.
- Обновлённые planning/backlog appendices в пяти существующих artifacts.
- Этот finalized Sprint Change Proposal с recorded approval/applied scope.
- Явный список последующих Major architecture/security/readiness tasks вместо скрытого implementation start.

## 6. Workflow Execution Log

- **2026-11-12 — Product direction:** пользователь подтвердил editorial model, scoped/self-assigned editors, simple notifications, nightly semantic MR direction и deterministic link-fix auto-publication.
- **2026-11-12 — Requirements/epics:** ED-F-01–17, ED-N-01–12, ED-A и ED-UX-01–07 извлечены; один Epic 14 и семь stories созданы; initial validation выполнена.
- **2026-11-12 — Correct Course analysis:** изменение классифицировано как Major; выбран planning-only Direct Adjustment после G1; rollback/MVP reduction отклонены.
- **2026-11-12 — Batch review finding:** обнаружены четыре coverage drift между story Requirements и Epic 14 Coverage Verification.
- **2026-11-14 — Explicit approval:** пользователь ответил `Да` на применение только planning/backlog изменений; product implementation, ADR/contracts/migrations/runbooks, nightly/provider/egress и production не утверждались.
- **2026-11-14 — Applied:** исправлены ED-F-07/10/11/17 declarations/coverage в `epics.md`; targeted reverse validation повторена, `status: final`, `finalValidationStatus: passed`.
- **2026-11-14 — Applied:** добавлены Epic 14 backlog/planning/traceability/test/estimate sections в `tasks.md`, `planning-input.md`, `traceability.md`, `test-plan.md`, `delivery-estimates.md`.
- **2026-11-14 — States:** F01–F05/F07 — BLOCKED; F06 — deferred planning reserve without executable task. Исторические R/I/A/T/E mappings и статусы не изменялись.
- **2026-11-14 — Explicitly not modified:** normative `spec.md`, ADR/contracts, `operations.md`, product code/migrations и `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- **2026-11-14 — Handoff:** Major planning package передан PM/PO + Solution Architect + QA/Security + owner. Следующий implementation-related gate — batch review stories, G1 closure, formal ADR/spec package и fresh readiness PASS.

Correct Course workflow complete, Антон. Deliverables: finalized proposal, applied OLD→NEW planning edits и recorded implementation handoff. Success criteria и remaining gates находятся в §§5.2–5.3.
