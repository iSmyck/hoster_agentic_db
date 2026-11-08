# Sprint Change Proposal — выравнивание stories, контрактов и нормативных статусов

Дата: 2026-11-08  
Статус: **APPROVED — APPLIED after validation 2026-11-08**  
Scope classification: **Moderate**  
Recommended approach: **Direct Adjustment**  
Триггер: `implementation-readiness.md` — **FAIL**, generation of tracking **not started**.

> Блоки OLD→NEW сохранены как audit record исходных предложений. Согласованные documentation/contract/backlog правки **APPLIED** и прошли documentation validation 2026-11-08; product code, production migrations/deploy и commits не выполнялись. Повторный implementation-readiness verdict и deterministic sprint-status generation этим статусом не заявляются.

## 1. Issue Summary — проблема и основание

Implementation readiness gate от 2026-11-08 остановил подготовку к implementation и запретил генерацию `sprint-status.yaml` до устранения четырёх групп дефектов (`_bmad-output/planning-artifacts/implementation-readiness.md:3-48`).

| ID | Проблема | Доказательство | Последствие |
|---|---|---|---|
| SCP-1 | Story-level traceability неполна: в `Requirements` отсутствуют I IDs, split stories не имеют финального reverse mapping к I/A, full и supporting coverage смешаны | `implementation-readiness.md:9-15`; текущие `epics.md` и `traceability.md` | Нельзя детерминированно проверить покрытие и сформировать sprint status без ручной интерпретации |
| SCP-2 | Stories заявляют acceptance до появления необходимых capabilities | E02.1 заявляет R05/A04 до E02.2/E02.3; E03.1 и E04.1 ссылаются на A09 без merge serialization; E07.3 ссылается на A19 до second-client stories; A28 не закреплён за E04.2 | Forward dependencies и риск ошибочного закрытия A04/A09/A19/A28 |
| SCP-3 | E04.7/T07b описывает correction task/MR без versioned task contract | `implementation-readiness.md:26-30`; `epics.md:1254-1282`; существующий DocOps contract покрывает только revision-bound `valid_until` и review queue | Не определены storage, owner, actor, idempotency, lifecycle, API и evidence semantics |
| SCP-4 | Нормативные тексты противоречат owner-approved G0 | `spec.md` запрещает break-glass абсолютно, тогда как G0-D3 признаёт privileged Owner bypass; G0-D8 обещает collaboration, тогда как realtime CRDT исключён из MVP; часть live docs сохраняет G0 OPEN/editor PENDING | Нельзя однозначно реализовывать security boundary, editor scope и текущие gate statuses |

Дополнительные проявления:

- A28 должен иметь явный primary home в E04.2, где находятся exact merge, crash recovery и conclusive reconciliation (`epics.md:1038-1077`).
- A09 относится к concurrent accepts/per-target serialization, а не только к stale-save conflict в E03.1 (`epics.md:925-959`).
- A19 относится ко второму config-only клиенту в E08.4 и полному operational/G3 acceptance в E08.5, а не к внутреннему pilot hardening в E07.3 (`epics.md:1622-1662`, `1799-1866`).
- Текущие статусы T00 DONE/G0 APPROVED и TipTap selected подтверждены `g0-review.md:3-30`, но не везде синхронизированы.

Проблема относится к misunderstanding of original requirements и planning/contract drift, а не к отказу реализованного product code. Product implementation ещё не выполнялась, поэтому rollback реализации не требуется.

## 2. Impact Analysis — влияние изменения

### 2.1. Epic и story impact

| Область | Требуемое влияние | Изменение зависимостей/scope |
|---|---|---|
| E00–E01 | Дополнить story `Requirements` явными I/A links; сохранить DESIGN/DONE semantics и не выдавать baseline/harness за product acceptance | Структура эпиков не меняется; статусы A/CF остаются невыполненными |
| E02 | Сузить E02.1 до R01–R03/direct read; убрать преждевременные R05/A04; распределить identity/ACL/enforcement между E02.2, E02.3 и E04.3 | Устраняется скрытая зависимость E02.1 от последующих ACL stories |
| E03 | Убрать A09 из E03.1; сохранить A08 stale-save и A10 history/restart/revert; подтвердить WYSIWYG-only TipTap scope в E03.2 | A09 переносится в merge path; realtime CRDT не добавляется |
| E04 | Дополнить все stories I/A mappings; сделать E04.2 primary owner A09/A28; убрать преждевременный A09 из E04.1; формализовать E04.7 correction-task contract | E04.2 получает явные concurrent-accept/crash-recovery checks; T07b зависит от нового contract |
| E05–E06 | Добавить final split-story mappings T10a/b, T12a/b, T13a/b и разделить direct/supporting acceptance | Epic order и односторонний E05 → E06 artifact dependency сохраняются |
| E07 | Убрать A19 из E07.3; сохранить только necessary internal-pilot T18 scope; синхронизировать editor/operations evidence | Second-client acceptance не закрывается внутренним пилотом |
| E08 | Закрепить A19 за E08.4/E08.5; дополнить T18a/b mappings; сделать privileged Owner incident/break-glass runbook частью operational design | Полный T18/G3 по-прежнему зависит от E08.2 и E08.4; новый эпик не создаётся |
| T19/T20 | Не изменять | Остаются deferred; новые R/I/A commitments не создаются |

### 2.2. Artifact conflicts и предлагаемый периметр будущих правок

| Артефакт | Конфликт | Предлагаемое действие после approval |
|---|---|---|
| `_bmad-output/planning-artifacts/epics.md` | Нет I IDs в story `Requirements`; forward acceptance claims; противоречивые admin/collab formulations | Исправить все story blocks, AC/evidence/dependencies и normative notes по §4 |
| `specs/corporate-kb/spec.md` | R05/A04 ownership не разведён на story level; абсолютный admin merge-only-GO; stale current-phase/editor statements | Уточнить normal GO path, privileged incident handling, TipTap/WYSIWYG scope и текущий G0 status без переписывания changelog |
| `specs/corporate-kb/traceability.md` | Нет final split-story mapping; G0 `(OPEN)`; stale missing-baseline/approval audit item | Добавить финальную карту E-story ↔ T-split ↔ R/I/A и F/S coverage; синхронизировать статусы |
| `specs/corporate-kb/architecture.md` | G0 OPEN, editor pending, collaboration в blocked checks; correction-task storage/API отсутствуют | Синхронизировать G0-D8/G0-D12; добавить correction-task ownership/contract; уточнить privileged incident/reconciliation |
| `specs/corporate-kb/g0-review.md` | G0-D8 использует неоднозначное «WYSIWYG/collaboration» | Сохранить Option A/TipTap, заменить collaboration на WYSIWYG editing + conflict detection/fresh revisions; CRDT остаётся вне MVP |
| `specs/corporate-kb/contracts/*` | Нет correction-task schema/API/lifecycle | Предложить два новых contract документа и расширение `openapi.yaml`, catalog/mapping/test vectors |
| `specs/corporate-kb/operations.md` | Break-glass описан как просто отключённый; stale G0 OPEN | Различить отсутствие routine/self-service break-glass и обязательный emergency privileged runbook; синхронизировать G0 |
| `tasks.md`, `adr/README.md`, `components/open-webui-fork.md`, `test-plan.md`, `planning-input.md`, `baseline.md` | В live-частях встречаются stale G0 OPEN/PENDING или editor NOT_SELECTED/pending | Синхронизировать только текущие статусы с owner-approved G0/TipTap; исторические evidence не falsify |
| `sprint-status.yaml` | Ещё не должен существовать как результат planning generation | Не создавать и не редактировать вручную до повторного readiness PASS |

### 2.3. Technical, security и UX impact

- **Product code/infrastructure:** изменений сейчас нет. Предлагаются backlog, normative docs и versioned contract changes only.
- **Data/storage:** correction task требует явно согласованного GO-owned operational record и idempotency/event semantics в `kb_ops`; он не становится canonical document или DecisionRecord. Нельзя молча называть такую запись Git-derived, если она не имеет Git anchor.
- **Security:** normal managed path остаётся GO/MR/human decision/GO merge. Privileged GitLab Owner bypass не легализуется как product path: это out-of-band incident с detection, quarantine и runbook.
- **UX:** TipTap сохраняет WYSIWYG editing. Вместо realtime collaboration используются exact revisions, stale/conflict detection, fresh base, полный diff и новая ProposalVersion.
- **MVP:** scope не сокращается. Realtime CRDT уже был вне MVP; correction contract формализует уже заявленную E04.7 functionality, а не добавляет новый product epic или новые A IDs.
- **Verification:** новые contract artifacts остаются DESIGN/PROPOSED до реальных T01/T04/T07 checks; syntactic validation не будет выдаваться за integration PASS.

## 3. Recommended Approach — Direct Adjustment

### 3.1. Выбранный путь

**Direct Adjustment:** исправить существующие stories и acceptance ownership, добавить недостающий versioned correction-task contract и синхронизировать нормативные тексты в рамках E00–E08.

Причины:

1. Проблемы локализованы в planning/contracts и не требуют фундаментальной смены Git-native architecture.
2. Epic IDs, порядок E00–E08, R01–R18, I01–I14, A01–A36 и deferred T19/T20 сохраняются.
3. Нет completed product stories или production data, которые нужно откатывать.
4. Исправления устраняют forward dependencies и делают последующую sprint-status generation детерминированной.

| Альтернатива | Оценка | Решение |
|---|---|---|
| Direct Adjustment | Medium effort / Medium risk; устраняет все FAIL findings без смены MVP | **Выбрано** |
| Potential Rollback | Нет product implementation или completed stories для rollback; откат документов вернул бы противоречия | Не применять |
| MVP Review / scope reduction | Не требуется: CRDT уже вне MVP, correction task формализует существующую E04.7 scope | Не применять |

### 3.2. Effort estimate

**Medium; ориентировочно 4–6 человеко-дней**, LOW confidence до capacity planning и не fixed commitment:

- PO/backlog realignment и все story mappings: 1.5–2 человеко-дня;
- Architect: correction-task schema/API/OpenAPI/storage/state semantics и admin boundary: 1.5–2 человеко-дня;
- QA: final R/I/A/F/S coverage, contract vectors и readiness review: 1–1.5 человеко-дня;
- Owner review и одна итерация исправлений: 0.5 человеко-дня без учёта ожидания.

### 3.3. Risk assessment

Общий риск — **Medium**.

| Риск | Уровень | Mitigation |
|---|---|---|
| Механическое добавление нерелевантных I/A создаст ложное coverage | Medium | Использовать только применимые I IDs и явные F/S labels; QA сверяет каждую строку с AC |
| Correction task станет вторым canonical write path или необъявленным durable state | High без контракта / Medium после | GO-owned API/storage, closed schema, no direct content writes, owner architecture approval, explicit backup/rebuild semantics |
| Owner bypass будет ошибочно описан как невозможный или как разрешённый обход | High без синхронизации / Medium после | G0-D3 wording, incident detection, immediate target quarantine, explicit runbook, никаких absolute-admin claims |
| Изменение G0-D8 будет воспринято как добавление CRDT | Low/Medium | Явно сохранить WYSIWYG и исключить realtime CRDT; fresh-revision conflict UX обязателен |
| Переписывание исторических evidence исказит audit trail | Medium | Менять live statuses, но не исторические PENDING/NOT_SELECTED snapshots |

### 3.4. Timeline impact

- Ориентировочная длительность документной корректировки: **3–5 рабочих дней** после owner approval при одном review cycle; ожидание решения владельца не входит.
- Начало product implementation задерживается до завершения корректировки и повторного **PASS** readiness gate.
- Календарные сроки downstream delivery не пересчитываются автоматически; после PASS план уточняется по фактической capacity.
- Rollback отсутствует; MVP scope reduction отсутствует; production migration/deploy/egress не требуются и не разрешаются этим proposal.

## 4. Detailed Change Proposals — конкретные OLD→NEW предложения

### 4.1. Единый формат Requirements и final-story traceability

**OLD — общий дефект:**

```text
Requirements: R...; UX-DR...; A...; CF....
```

I IDs отсутствуют, A IDs не разделены на direct/full и supporting, а `traceability.md` заканчивается на parent T/E mappings без полной split-story карты.

**NEW — обязательный формат для каждой story:**

```text
Requirements: R...; I...; UX-DR...; A...; CF....
Acceptance ownership: Full/direct — A...; Supporting — A....
```

Правила:

- В каждую story добавить **применимые идентификаторы из полного диапазона I01–I14 и явные A IDs**; не назначать механически все инварианты каждой story.
- Совокупность final-story mappings обязана покрывать I01–I14 и A01–A36 без потерянных split tasks.
- **F / Full/direct** означает прямой проверяемый критерий в scope данной story; **S / Supporting** — частичный или cross-cutting вклад. Ни F, ни S не означают VERIFIED/DONE.
- UX-DR и CF IDs сохраняются, кроме явно описанных ниже правок.
- В `traceability.md` добавить final-story mapping на основе следующей таблицы; parent T00–T20 navigation сохранить, но не использовать его как замену split mapping.

| Story / final task | OLD — R и A в Requirements | NEW — R; I; A ownership (UX/CF без изменений, кроме отдельных пунктов ниже) |
|---|---|---|
| E00.1 / T00 | R18; A IDs отсутствуют | R18; **I01–I14** как audit coverage; **S:** A20,A24,A34; A01–A36 только mapping-only, не product acceptance |
| E01.1 / T01 | R18; A21,A33 | R18; **I08,I09,I10,I11,I12**; **F:** A21,A33 только в contract-harness scope; остальные A01–A36 через CF-30 только supporting/design coverage |
| E02.1 / T02 | R01,R02,R03,R05; A01,A02,A04,A21,A22,A32 | **R01,R02,R03**; **I08,I09,I11,I12,I13,I14**; **F:** A01,A32; **S:** A02,A21,A22. **R05 и A04 удалить** |
| E02.2 / T03a | R05,R16; A18,A24,A26,A33 | R05,R16; **I02,I03,I04,I09,I10,I12**; **F:** A24,A26; **S:** A04,A18,A33 |
| E02.3 / T03b | R01,R05,R16; A04,A11,A18,A22,A25,A26,A30,A31,A32,A33,A36 | R01,R05,R16; **I01,I02,I03,I04,I06,I08,I09,I10,I11,I12,I13,I14**; **F:** A04,A11,A18,A25,A26,A32,A33,A36; **S:** A22,A30,A31 |
| E03.1 / T04a | R02,R09,R10; A08,A09,A10 | R02,R09,R10; **I05,I06,I14**; **F:** A08,A10. **A09 удалить из Requirements и Evidence** |
| E03.2 / T04b | R01,R02,R09; A01,A08,A23 | R01,R02,R09; **I01,I02,I03,I05,I06,I09,I14**; **S:** A01,A08,A23; realtime CRDT не добавлять |
| E04.1 / T05a | R02,R06,R07,R09,R10; A05,A08,A09,A22,A30 | R02,R06,R07,R09,R10; **I01,I02,I03,I04,I05,I06,I08,I09,I12**; **F:** A05; **S:** A08,A22,A30. **A09 удалить** |
| E04.2 / T05b | R06–R10; A06,A07,A08,A09,A27,A29,A30,A34,A36 | R06,R07,R08,R09,R10; **I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14**; **F:** A06,A07,A08,**A09**,A27,**A28**,A29,A30,A34,A36 |
| E04.3 / T06 | R05–R08,R10,R16; A04,A05,A09,A17,A18,A28,A29,A34,A36 | R05,R06,R07,R08,R10,R16; **I01,I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14**; **F:** A04,A05,A17,A18,A29,A34; **S:** A09,A28,A36 |
| E04.4 / T07 | R01,R05–R10; A01,A06,A07,A22,A23,A26,A27,A30,A36 | R01,R05,R06,R07,R08,R09,R10; **I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I12,I13,I14**; **F:** A06,A07,A22,A23,A27,A30; **S:** A01,A26,A36 |
| E04.5 / T08 | R01,R02,R03,R05,R16; A01,A02,A21,A22,A25,A32 | R01,R02,R03,R05,R16; **I06,I08,I09,I11,I12,I13,I14**; **F:** A01; **S:** A02,A21,A22,A25,A32 |
| E04.6 / T09 | R03,R05,R06,R07,R10,R16; A02,A04,A05,A17,A18,A21,A30 | R03,R05,R06,R07,R10,R16; **I01,I02,I03,I04,I06,I08,I09,I11,I12**; **F:** A02,A21; **S:** A04,A05,A17,A18,A30 |
| E04.7 / T07b | R01,R05–R10; A01,A07,A22,A26,A27,A36 | R01,R05,R06,R07,R08,R09,R10; **I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I12,I13,I14**; **S:** A01,A07,A22,A26,A27,A36; новые A IDs не создавать |
| E05.1 / T10a | R02,R04,R11,R18; A03,A12,A22,A31,A35 | R02,R04,R11,R18; **I01,I02,I08,I09,I10,I11,I12,I14**; **F:** A12,A22,A35; **S:** A03,A31 |
| E05.2 / T10b | R03,R04,R05,R11,R16,R18; A02,A03,A11,A21,A22,A25,A31,A32,A35 | R03,R04,R05,R11,R16,R18; **I01,I02,I06,I08,I09,I10,I11,I12,I13,I14**; **F:** A02,A03,A11,A21,A22,A25,A32,A35; **S:** A31 |
| E06.1 / T12a | R02,R12,R13,R15,R16,R18; A13,A16,A22,A23 | R02,R12,R13,R15,R16,R18; **I01,I02,I03,I08,I09,I12,I13,I14**; **F:** A13,A23; **S:** A16,A22 |
| E06.2 / T12b | R04,R05,R06,R09,R11,R12,R13,R18; A13,A31,A35,A36 | R04,R05,R06,R09,R11,R12,R13,R18; **I01,I02,I06,I08,I09,I10,I11,I12,I13,I14**; **F:** A13,A31,A35; **S:** A36 |
| E06.3 / T13a | R02,R05,R09,R10,R14,R18; A11,A15,A25,A27,A28,A32,A36 | R02,R05,R09,R10,R14,R18; **I05,I06,I07,I09,I10,I11,I12,I13,I14**; **F:** A11,A25,A27,A32,A36; **S:** A15,A28 |
| E06.4 / T13b | R02,R05,R09,R10,R11,R14,R18; A11,A15,A25,A27,A28,A32,A36 | R02,R05,R09,R10,R11,R14,R18; **I05,I06,I07,I09,I10,I11,I12,I13,I14**; **F:** A15,A32; **S:** A11,A25,A27,A28,A36 |
| E07.1 / T11 | R15,R16,R18; A16,A18,A20 | R15,R16,R18; **I03,I04,I09,I12,I13**; **F:** A16; **S:** A18,A20 |
| E07.2 / T14 | R01,R03,R04,R05,R11,R15,R18; A03,A18,A20,A21 + regression | R01,R03,R04,R05,R11,R15,R18; **I01–I14 в явно выбранном regression scope**; **F:** A03,A18,A20,A21; **S:** применимые A01–A36 без автоматического VERIFIED |
| E07.3 / necessary T18 | R01,R05,R14,R15,R17,R18; A01,A06,A07,A08,A09,A10,A15,A19,A20,A22,A23,A28,A33 | R01,R05,R14,R15,R17,R18; **I01–I14 по operational-hardening scope**; **S:** A01,A06,A07,A08,A09,A10,A15,A20,A22,A23,A28,A33. **A19 удалить** |
| E08.1 / T15 | R06–R10,R12,R13,R16,R18; A14,A17,A32 | R06,R07,R08,R09,R10,R12,R13,R16,R18; **I01,I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14**; **F:** A14; **S:** A17,A32 |
| E08.2 / T16 | R05,R06,R12–R16,R18; A14,A16,A23,A25,A32 | R05,R06,R12,R13,R14,R15,R16,R18; **I01,I02,I03,I04,I06,I07,I09,I10,I11,I12,I13,I14**; **F:** A14; **S:** A16,A23,A25,A32 |
| E08.3 / T17 conditional | R02,R04,R12,R13,R15,R18; A16,A22,A23 | R02,R04,R12,R13,R15,R18; **I01,I02,I03,I08,I09,I12,I13**; **F:** A16,A23 только при activated conditional scope; **S:** A22 |
| E08.4 / T18a | R05,R15,R17,R18; A19,A20,A33 | R05,R15,R17,R18; **I04,I07,I09,I10,I11,I12,I13,I14**; **F:** **A19**,A20,A33 |
| E08.5 / T18b | R05,R06,R09,R10,R11,R13,R14,R15,R17,R18; A14,A15,A19,A20,A28,A33 | Те же R; **I01,I02,I03,I04,I05,I06,I07,I09,I10,I11,I12,I13,I14**; **F:** A15,**A19**,A20,A33; **S:** A14,A28 |

Обязательные reverse mappings, которые должны появиться в `traceability.md` без сокращений «etc.»:

- **T03a/T03b:** E02.2/E02.3 соответственно; R05/R16 и A04/A24/A26/A33/A36 разнесены по identity, policy и enforcement scope.
- **T04a/T04b:** E03.1/E03.2; A09 не имеет acceptance ownership в этих stories; editor conflict проверяется через A08, а concurrent accepts — через E04.2 с supporting enforcement в E04.3.
- **T05a/T05b:** E04.1/E04.2; A05 закреплён за ProposalVersion lifecycle, A09/A28 — за exact merge/recovery.
- **T07/T07b:** E04.4/E04.7; T07b получает только supporting existing A IDs и ссылки на новый correction contract.
- **T10a/T10b:** E05.1/E05.2; build/preflight отделены от serving/pointer lifecycle.
- **T12a/T12b:** E06.1/E06.2; dry-run/admission отделены от cutover/activation.
- **T13a/T13b:** E06.3/E06.4; portable export отделён от mirror/backup/clean restore.
- **T18 necessary/T18a/T18b:** E07.3/E08.4/E08.5; A19 назначен только E08.4/E08.5.

### 4.2. E02.1 — удалить преждевременную full authorization

**Story/Section:** E02.1/T02, `Requirements`, первый Acceptance Criterion, Evidence.

**OLD:**

```text
Requirements: R01, R02, R03, R05; ... A01, A02, A04, A21, A22, A32 ...

Then the server returns authorized parent/child relationships ...
And unauthorized tree titles, paths and content are denied before exposure,
including cross-Space IDOR and anti-enumeration NOT_FOUND cases ...
```

**NEW:**

```text
Requirements: R01, R02, R03; I08,I09,I11,I12,I13,I14; ...
Full/direct: A01,A32. Supporting: A02,A21,A22.

Then the server returns parent/child relationships, stable opaque document IDs,
breadcrumbs and stable-ID deep links from Git metadata within the explicit
synthetic read scope supplied by the E01 harness, preserving UUID after rename/move.
Full Identity/AuthZ policy enforcement, unauthorized title/path/content denial,
cross-Space IDOR and anti-enumeration acceptance are not closed by this story.
Exact-revision whole/section direct read with bounds, cursor and explicit truncation
remains in scope.
```

**Evidence OLD:** «... Unicode/path vectors and negative ACL results».  
**Evidence NEW:** «... Unicode/path vectors and structural cross-Space fixture checks; full negative ACL evidence принадлежит E02.2/E02.3 и E04.3».

**Распределение full ACL:**

- **E02.2/T03a:** stable identity, nested group snapshots, trusted actor и отсутствие business GitLab users — prerequisites для authorization.
- **E02.3/T03b:** full per-Space policy evaluation для tree/titles/read/files/history/search/export/tools до payload, включая IDOR/anti-enumeration, revocation и policy revisions.
- **E04.3/T06:** full server/GO/GitLab enforcement против write/merge/grants bypass на всех каналах, включая A04.
- **E02.1:** только R01–R03 direct-read/document-model scope; R05/A04 не заявляются и не отмечаются complete downstream.

**Rationale:** устраняется forward dependency E02.1 → E02.2/E02.3 без изменения правильного порядка E02.1 → E02.2 → E02.3.

### 4.3. A09, A28 и A19 — acceptance realignment

#### A09 — concurrent accepts, а не stale-save only

**OLD — E03.1 и E04.1:**

```text
E03.1 Requirements/Evidence: ... A08,A09,A10 ...
E04.1 Requirements/Evidence: ... A05,A08,A09,A22,A30 ...
UX-DR12 Проверка: A08/A09/T04 ...
```

**NEW:**

```text
E03.1: A08,A10; stale-save conflict only.
E04.1: A05; supporting A08,A22,A30; no concurrent-merge acceptance.
E04.2: A09 Full/direct и primary ownership, совместно с exact merge/per-target serialization.
E04.3: A09 Supporting для adversarial fencing/race enforcement.
UX-DR12 Проверка: A08/T04 для editor conflict; A09 проверяется в E04.2/E04.3.
```

В E04.2 добавить явный AC:

```text
Given two accepted decisions for different exact proposals targeting the same
(repository_id,target_branch),
When their applies become concurrent,
Then per-target serialization and the final HEAD==base_sha recheck permit at most
one verified apply; the loser receives conflict/STALE_BASE with zero new main writes,
and replay/reconciliation cannot create a second apply.
```

#### A28 — primary crash-recovery owner E04.2

**OLD:** A28 присутствует в E04.3/E06.3/E06.4/E07.3/E08.5, но отсутствует в E04.2.

**NEW:**

- добавить **A28 Full/direct** в E04.2 `Requirements` и `Evidence`;
- явно связать существующий crash-after-GitLab-merge-before-projection AC с A28;
- оставить E04.3 fencing/quarantine, E06.3/E06.4 export/restore и E07.3/E08.5 operational rehearsals как supporting coverage;
- обновить A28 final-story mapping: `T05b/E04.2 primary; T06/E04.3 enforcement; T13a/T13b and T18 supporting`.

#### A19 — second client только в E08.4/E08.5

**OLD — E07.3:**

```text
Requirements: ... A15,A19,A20 ...
Evidence: necessary T18 pilot scope supporting A15,A19,A20,A28,A33 ...
```

**NEW:**

```text
Requirements: ... A15,A20 ... — A19 отсутствует.
Evidence: necessary internal-pilot scope supporting A15,A20,A28,A33;
no second-client/A19 completion claim.
```

**NEW — final A19 mapping:**

- **E08.4/T18a:** A19 Full/direct — second config-only dedicated client, resource isolation и отсутствие code fork;
- **E08.5/T18b full/G3:** A19 Full/direct — итоговая operational/G3 проверка уже развёрнутого второго клиента;
- **E07.3:** A19 отсутствует в Requirements, Evidence и acceptance ownership.

### 4.4. E04.7/T07b — correction-task contract до tracker entry

#### 4.4.1. Contract artifacts

**OLD:**

- E04.7 создаёт business-approver correction task и optional correction MR (`epics.md:1268-1271`).
- Существуют только DocOps `valid_until`/review-queue metadata.
- Нет task schema, task lifecycle, storage ownership, create/get/resolve/cancel API и idempotency contract.

**NEW — предложить к созданию после approval:**

1. `specs/corporate-kb/contracts/docops-correction-task.schema.json` — closed `docops-correction-task-v1`, `additionalProperties:false`.
2. `specs/corporate-kb/contracts/docops-correction-api.md` — нормативные lifecycle, actor/owner, storage, idempotency, errors, authorization, evidence и MR-linking rules.
3. Расширить `specs/corporate-kb/contracts/openapi.yaml` endpoints и schemas из таблиц ниже.
4. Обновить contract catalog/README, projection mapping, architecture/spec data ownership, traceability `[CORR]` links и существующие CF-06/CF-10/CF-20 design vectors; новые A IDs не создавать.

#### 4.4.2. Минимальная schema

| Поле | Предлагаемый contract |
|---|---|
| `schema_version` | Literal `docops-correction-task-v1` |
| `task_id` | Server-generated UUID, не переиспользуется |
| `space_id`, `repository_id`, `document_id` | Согласованный repository=Space binding и opaque document UUID |
| `document_revision_sha` | Полный lowercase exact Git SHA сообщённой ревизии; не перепривязывается молча при новом HEAD |
| `state` | `open`, `in_review`, `resolved`, `cancelled` |
| `requester_stable_id` | Stable external actor из trusted server context; client/LLM не задаёт actor |
| `owner` | `{kind:user|group, stable_id}` из действующей approval policy; не из front matter и не из model arguments |
| `evidence_sha256` | SHA-256 нормализованного sanitized evidence payload; обязателен при create и при no-MR resolution |
| `linked_mr` | Optional/null: `{proposal_id,proposal_sha,merge_commit_sha?}`; не заменяет ProposalRecord/DecisionRecord |
| `idempotency_key`, `payload_hash` | Связь с verified actor + normalized operation/route + concrete path + payload hash |
| `task_version` | Monotonic server version/CAS для resolve/cancel и предотвращения lost update |
| `created_at`, `updated_at` | UTC RFC 3339 server timestamps |
| `resolved_at`, `cancelled_at` | Nullable/conditional по state |
| `resolved_by_stable_id`, `cancelled_by_stable_id` | Nullable/conditional stable actors из trusted context |

Дополнительные правила:

- Task является **GO-owned operational record** в `kb_ops`, с append-only task events/current projection и общей idempotency registry. `kb_ops` остаётся единственным writer через GO.
- Task не является canonical document, ProposalRecord, DecisionRecord или новым canonical document status. Его durability, backup, retention и rebuild/reconciliation semantics должны быть явно добавлены в architecture/database design; отсутствие Git anchor не скрывается формулировкой «Git-derived».
- Если correction меняет canonical content, требуется обычный E04.1/E04.2/E04.4 MR/human decision/GO merge. Task/API никогда не редактирует и не архивирует документ напрямую.
- Если документ уже изменился, task сохраняет исходный `document_revision_sha`; correction MR создаётся от fresh HEAD с явным diff/conflict review. Silent rebase/rebind запрещён.
- Queue/get/events используют fresh per-Space AuthzContext, policy bundle/revisions и anti-enumeration. Evidence hash не позволяет восстанавливать private payload в logs/telemetry.

#### 4.4.3. OpenAPI endpoints

| Operation | Предлагаемый endpoint и semantics |
|---|---|
| Create | `POST /api/kb/v1/spaces/{space_id}/docops/correction-tasks` — обязательные `Idempotency-Key`, exact document revision и `evidence_sha256`; server определяет requester/owner; создаёт `open`, либо `in_review`, если валидный optional `linked_mr` уже существует |
| Get | `GET /api/kb/v1/spaces/{space_id}/docops/correction-tasks/{task_id}` — авторизованный exact task/state/owner/revision/evidence-hash/linked-MR view; чужой Space даёт safe `NOT_FOUND`/FORBIDDEN по policy |
| Resolve | `POST /api/kb/v1/spaces/{space_id}/docops/correction-tasks/{task_id}/resolve` — owner-only mutation с `Idempotency-Key`, `task_version`; optional linked MR; MR-based resolution только после verified governed outcome, no-MR resolution требует reason + evidence hash |
| Cancel | `POST /api/kb/v1/spaces/{space_id}/docops/correction-tasks/{task_id}/cancel` — уполномоченный requester/owner по policy, `Idempotency-Key`, `task_version`, reason/evidence hash по contract; canonical content не меняется |

Все mutations:

- повтор с тем же verified actor/route/path/payload возвращает существующий результат без второго side effect;
- reuse key с другим actor/route/path/payload → `IDEMPOTENCY_KEY_REUSED` и ноль writes;
- path/body `task_id` и `space_id` обязаны совпадать до side effect;
- stale `task_version`, revision/policy mismatch и invalid transition дают unified error без mutation;
- ошибки используют существующие `FORBIDDEN/NOT_FOUND`, `IDEMPOTENCY_KEY_REUSED`, `REVISION_CONFLICT`, `POLICY_REVISION_MISMATCH`, `AUTHZ_CONTEXT_STALE`, `INVALID_STATE`, `UPSTREAM_UNAVAILABLE`.

#### 4.4.4. Lifecycle

```text
open --durable valid linked MR--> in_review
open/in_review --authorized conclusive resolution--> resolved
open/in_review --authorized cancellation--> cancelled
resolved/cancelled --terminal; no reopen through replay-->
```

- `resolved` и `cancelled` terminal; повтор той же операции возвращает existing record.
- `in_review` не означает corrected/published; linked MR сам по себе не доказывает merge.
- `resolved` с content correction требует verified GO merge; no-MR resolution не создаёт видимость исправления канона.
- Task states не смешивать с DocOps `scheduled/due/in_review/resolved/removed` и Proposal states.

#### 4.4.5. E04.7 Acceptance Criteria OLD→NEW

**OLD:**

```text
Then it creates a business-approver task bound to that exact document revision,
and its correction follows the normal ProposalRecord/MR/human-decision/GO-merge path.
```

**NEW:**

```text
Then GO creates a docops-correction-task-v1 through the contracted create endpoint
with server-derived requester and policy-derived owner, exact document_revision_sha,
evidence_sha256 and optional linked_mr; initial state is open, or in_review when a valid
linked MR is already durable; identical replay returns the same task and key reuse with
another actor/payload creates zero writes.
And get/resolve/cancel enforce per-Space authorization, task_version and the
open/in_review/resolved/cancelled state machine; a content correction becomes resolved
only after the normal ProposalRecord/MR/human-decision/GO-merge evidence, while neither
the task nor expiry directly edits, publishes or archives canonical content.
```

#### 4.4.6. Tracker gate

**OLD:** E04.7/T07b существует в epics, но contract отсутствует; readiness требует не добавлять T07b в tracker.

**NEW:** только после того как schema, API doc и OpenAPI create/get/resolve/cancel contracts созданы и прошли design/reference validation:

1. обновить E04.7 и traceability `[CORR]` links;
2. добавить T07b в `tasks.md` с корректным TODO/BLOCKED state и dependencies;
3. не добавлять T07b в `sprint-status.yaml` вручную — он попадёт туда только при последующей deterministic generation после readiness PASS.

### 4.5. Admin/Owner bypass — normal GO path и out-of-band incident

#### 4.5.1. Нормативная формулировка spec/epics

**OLD — характерные противоречия:**

```text
spec.md §5: Instance admin ... break-glass в MVP отключён и не является
исключением из merge-only-GO.

spec.md T06 / epics non-goals: direct human/service merge закрыт для всех;
admin break-glass отключён; только GO имеет merge permission.

epics.md E04.3: privileged GitLab Owner bypass documented ... and MVP break-glass
remains disabled.
```

**NEW:**

```text
Для всех обычных business/engineering/source-managed identities и всех managed
каналов единственный нормальный post-cutover final-apply path — GO/MR/canonical
human DecisionRecord/GO merge. Routine/self-service admin break-glass product
capability в MVP отсутствует.

Привилегированный GitLab instance/project Owner может технически обойти protected
rules вне GO. Такой bypass не является approved managed path и не используется как
доказательство абсолютного merge-only-GO для admins. Он классифицируется как
out-of-band security/integrity incident: out-of-band reconciliation обнаруживает
неучтённый HEAD/merge, немедленно устанавливает affected-target
recovery_required/quarantine, блокирует новые managed merges, сохраняет audit evidence
и запускает explicit break-glass/incident runbook.
```

Применить эту формулировку к `spec.md` §5/T03/T06/T18/non-goals, `epics.md` E04.3/E07.3/E08.5/non-goals и соответствующим architecture statements. R06/I02/I04 не интерпретировать как ложное физическое обещание про privileged Owner; agent/connector/LLM auto-merge остаётся абсолютно запрещён.

#### 4.5.2. E04.3 AC OLD→NEW

**OLD:**

```text
GitLab and GO independently deny every path and only the GO merge service identity
can create the verified merge commit ... privileged GitLab Owner bypass is documented
... and MVP break-glass remains disabled.
```

**NEW:**

```text
For every non-privileged business/engineering/bot/connector/CI/source identity,
GitLab and GO independently deny direct push, direct merge and auto-merge; only the
GO merge service identity can create a managed verified merge after canonical decision.
If a privileged GitLab Owner bypasses this boundary out of band, reconciliation detects
the unexpected target history, does not label it a GO merge, raises an integrity
incident and quarantines the affected target until conclusive reconciliation and
reviewed remediation complete. Restricted privileged accounts, audit and the explicit
G0-D3 break-glass runbook are mandatory governance controls.
```

#### 4.5.3. G0-D3 и operations runbook

**G0-D3 остаётся approved authority и не переоткрывается.** В downstream governance и `operations.md` предложить явный runbook со следующими шагами:

1. restricted privileged account inventory и периодический review;
2. отдельное emergency authorization record без presumption, что proposal разрешает реальный incident action;
3. фиксация actor, reason, exact repository/target/SHAs, timestamp и audit refs;
4. immediate managed write freeze + `recovery_required`/quarantine affected target;
5. Git-derived reconciliation всех unexpected commits и unresolved accepts;
6. reviewed remediation/revert-MR там, где это применимо, без history rewrite;
7. credential/access review или rotation по security procedure;
8. owner-reviewed incident closure и снятие quarantine только после conclusive evidence.

**OLD:** «break-glass отключён» как единственное operational правило.  
**NEW:** «routine/self-service break-glass feature отключён; emergency out-of-band privileged procedure документирована, аудируется, приводит к incident/quarantine и не является нормальным merge path».

### 4.6. Collaboration — TipTap WYSIWYG без realtime CRDT

#### 4.6.1. G0-D8

**OLD — `g0-review.md` D8 и Option A:**

```text
TipTap adapter: preserve WYSIWYG/collaboration; add canonical serializer ...
Keep WYSIWYG and collaboration ...
```

**NEW:**

```text
TipTap adapter: preserve WYSIWYG editing; add canonical serializer, front-matter
boundary, immutable attachment metadata, full source diff and
browser/IME/accessibility/XSS gates. Realtime collaborative editing/CRDT remains
out of MVP. Concurrent authors receive conflict detection, exact/fresh revisions,
full difference review and a new ProposalVersion instead of shared realtime state
or automatic conflict merge.
```

Owner selection **Option A — TipTap adapter** не меняется. После owner confirmation оформить это как clarification утверждённого D8, сохранив approver/date audit и ссылку на данный proposal; агент сам не продлевает APPROVED.

В Option B убрать связку «no WYSIWYG/collaboration» как единый признак: отличие Option B — отсутствие WYSIWYG, а realtime CRDT вне MVP для всех опций.

#### 4.6.2. Spec/epics/architecture

**OLD:** G0-D8 обещает collaboration, тогда как `spec.md` §7.2 и `epics.md` E03.2 исключают CRDT; architecture называет collaboration blocked browser check.

**NEW:**

- `spec.md` §3.1/§7.2: TipTap adapter сохраняет WYSIWYG editing; realtime collaborative editing/CRDT вне MVP; второй редактор получает `STALE_BASE`/«Документ изменился», fresh revision и новую ProposalVersion.
- `epics.md` UX-DR7/UX-DR12 и E03.2: оставить lossless WYSIWYG/canonical serializer и явно указать, что collaboration не является T04 acceptance; проверяются conflict detection и fresh revisions.
- `architecture.md` §13.2: убрать realtime collaboration из списка BLOCKED MVP browser checks; оставить WYSIWYG/raw preview, IME, accessibility, XSS и full managed preview как deferred T04 gate.
- `test-plan.md`, `tasks.md`, `components/open-webui-fork.md`: синхронизировать editor scope; не требовать collaboration PASS для MVP.
- Исторические stop conditions не удалять: обязательное realtime collaboration в будущем по-прежнему требует отдельного ADR и переоценки Git-native канона.

**Rationale:** сохраняется утверждённый TipTap и весь WYSIWYG scope; устраняется только противоречивая формулировка, без скрытого MVP scope reduction или expansion.

### 4.7. Status synchronization — G0 APPROVED и TipTap selected

| Артефакт/место | OLD | NEW |
|---|---|---|
| `traceability.md:9` | `g0-review.md (OPEN)` | `g0-review.md (APPROVED; T00 DONE, G0 APPROVED 2026-11-08)`; synthetic evidence по-прежнему не product acceptance |
| `traceability.md:190` | Отсутствуют baseline, pinned refs и owner G0 approval | Baseline/pinned refs и owner G0 approval имеются; отсутствующие product/integration acceptance inputs перечислены отдельно и остаются BLOCKED/DESIGN |
| `architecture.md:449` | UNKNOWN включает editor direction | Editor direction resolved: TipTap adapter, G0-D8 APPROVED; owner thresholds, hoster inputs и legal review остаются открытыми |
| `architecture.md:459` | `editor не выбран ... G0-D8 pending` | `TipTap adapter selected and owner-approved at G0-D8; canonical adapter и T04 browser gate не завершены` |
| `architecture.md:506` | Editor direction — три не выбранные опции; collaboration BLOCKED | TipTap выбран; T04 WYSIWYG/browser gates deferred; realtime CRDT вне MVP, а не BLOCKED MVP item |
| `architecture.md:512` | Owner G0 approval — OPEN | Owner G0 approval — APPROVED, ссылка на `g0-review.md`, 2026-11-08 |
| `spec.md:6,723` | Текущий статус proposed/только T00/G0; ревизия не закрывает G0 | Current status: T00 DONE/G0 APPROVED; backlog readiness correction в работе; implementation только по dependencies и после PASS; production не разрешён. Changelog не переписывать |
| `spec.md:784` | Редактор/component UNKNOWN T00 | TipTap adapter selected G0-D8; lossless adapter/browser validation остаются T04 |
| `adr/README.md` | `редактор не выбран`, `g0-review.md OPEN` | TipTap selected, G0 APPROVED; individual ADR Proposed/Accepted statuses не менять автоматически |
| `operations.md:501` | Owner review отсутствует, G0 OPEN | Owner review получен, G0 APPROVED; operational rehearsals остаются DESIGN_NOT_EXECUTED |
| `tasks.md:163` | Owner G0 approval record отсутствует/OPEN | Owner approval получен, ссылка на `g0-review.md` APPROVED; другие task states не менять без evidence |
| `components/open-webui-fork.md:7` | Editor direction остаётся owner decision | TipTap selected; adapter/browser work не PASS |
| `test-plan.md:40` | Выбор — G0-D8; collaboration BLOCKED | TipTap selected; T04 browser checks pending; realtime CRDT out of MVP |
| `planning-input.md` current-risk statements | Owner G0 approval отсутствует | Пометить риск как resolved 2026-11-08 либо явно обозначить текст историческим planning input, не текущим tracker |
| `baseline.md` current pin note | G0 owner review required | G0 owner review APPROVED; deferred legal/production gates сохраняются |

Особые правила:

- `evidence/t00/independent-review.md` с историческим G0-D12 **PENDING** и `evidence/t00/openwebui-rag-editor-audit.md` с исходным harness **NOT_SELECTED** не переписывать задним числом: это point-in-time evidence. Текущие live docs обязаны ссылаться на последующий `g0-review.md` APPROVED и TipTap selection.
- Не менять A01–A36/CF-01–CF-30 на VERIFIED, не помечать deferred T04/T11/T13/T16/legal gates как PASS и не утверждать production readiness.
- Не заменять individual ADR statuses общим G0 APPROVED.

## 5. Implementation Handoff — передача и критерии завершения

**Handoff status: APPROVED — APPLIED after validation.** Документные изменения и доступные проверки завершены 2026-11-08. Повторный implementation-readiness gate и последующая deterministic sprint-status generation остаются отдельными gated actions и не маркируются выполненными этой записью.

### 5.1. Scope classification

**Moderate:** требуется backlog reorganization и согласованный contract change с участием PO/DEV, Architect и QA. Major replan, новый эпик, product rollback и MVP scope reduction не требуются.

### 5.2. Handoff recipients

| Роль | Фактический handoff / остаток |
|---|---|
| Owner | Proposal, correction-contract/storage direction и формулировки G0-D3/G0-D8 **APPROVED**; self-approval агентом не использовалось |
| Product Owner | Story Requirements/F/S mappings, acceptance ownership E02.1/A09/A19/A28 и backlog sequence **APPLIED** |
| Solution Architect | Correction-task schema/API/OpenAPI, storage/lifecycle/idempotency semantics и admin incident/runbook alignment **APPLIED** |
| Developer agent | Только согласованные documentation/contract/backlog edits **APPLIED**; product code не изменён |
| QA / readiness reviewer | Полный R/I/A/T-split reverse mapping, contract vectors, forward claims, stale statuses и documentation checks **VALIDATED**; новый readiness gate — отдельный PENDING |
| PO + sprint planning | Только после нового PASS запустить `bmad-sprint-planning` и deterministic `sprint-status.yaml` generation; сейчас **NOT RUN** |

### 5.3. Обязательная последовательность — фактическое состояние

1. **APPROVED:** owner approval данного proposal получен; OLD→NEW ниже сохранены как исходный audit record.
2. **APPLIED:** нормативные G0-D3/G0-D8 decisions и current statuses синхронизированы в spec/epics/architecture/traceability.
3. **APPLIED:** correction-task schema, `docops-correction-api.md` и OpenAPI create/get/resolve/cancel contract подготовлены, включая storage и state semantics.
4. **APPLIED:** story-level I/A/F/S mappings и AC/evidence corrections применены во всех E00.1–E08.5.
5. **APPLIED:** `traceability.md` final-story mappings обновлены для всех split tasks, включая обязательные T03a/b, T04a/b, T07b, T13a/b, T18a/b, а также T05a/b, T10a/b и T12a/b.
6. **APPLIED:** operations governance/break-glass runbook design и live stale statuses обновлены, исторические evidence сохранены.
7. **APPLIED:** T07b добавлен в tracker с корректными dependencies/state только после появления correction contract.
8. **VALIDATED:** documentation/schema/OpenAPI/reference checks выполнены без mocked integration PASS; machine output не добавлялся в reviewable docs.
9. **PENDING / NOT CLAIMED:** повторный implementation-readiness gate запускается отдельно; настоящий APPLIED статус не подменяет его verdict.
10. **NOT RUN:** `bmad-sprint-planning` и subsequent deterministic sprint-status generation разрешены только после **PASS**. `sprint-status.yaml` вручную не создавался и не генерировался при FAIL.

### 5.4. Success criteria

- Все четыре findings из `implementation-readiness.md` закрыты без новых противоречий.
- Каждая story содержит применимые I01–I14/A IDs и отдельные Full/direct/Supporting acceptance links; reverse mapping не содержит пропущенных split IDs.
- E02.1 не заявляет R05/A04; A09 имеет primary home E04.2 и supporting enforcement в E04.3, A28 имеет primary home E04.2, A19 — только E08.4/E08.5.
- Correction contract полностью определяет create/get/resolve/cancel, idempotency, exact revision, stable actor, evidence hash, owner, optional linked MR, storage и states `open/in_review/resolved/cancelled`; T07b добавлен в tracker только после него.
- Normal GO merge boundary и privileged Owner out-of-band incident/quarantine/runbook описаны без абсолютного admin merge-only-GO claim.
- TipTap/WYSIWYG сохранён; realtime collaborative editing/CRDT явно вне MVP; conflict detection/fresh revisions обязательны.
- Live statuses соответствуют T00 DONE, G0 APPROVED и TipTap selected; исторические evidence и deferred gates не искажены.
- Документная валидация применённых изменений — **PASS**: JSON/YAML/front matter parse, Markdown links/anchors и consistency assertions.
- Повторный readiness verdict и последующая **детерминированная генерация sprint status** не заявляются выполненными; они остаются отдельными gated actions после нового readiness PASS, не ручной правкой статусов.

### 5.5. Change Navigation status

- Триггер, evidence, epic/artifact impact и path forward: проанализированы в §1–§3.
- Direct Adjustment: выбран; rollback и MVP reduction: отклонены как неприменимые.
- Detailed OLD→NEW proposals: подготовлены в §4.
- Owner approval для реализации предложений: **APPROVED**.
- Согласованные documentation/contract/backlog updates: **APPLIED after validation**.
- Повторный readiness gate и deterministic sprint-status generation: **PENDING / NOT CLAIMED**; ручной `sprint-status.yaml` не создавался.
- Фактические изменения product code, production migration, deploy, push, destructive cleanup и paid external calls: **N/A / не выполнялись**.

**Фактический результат: proposal APPROVED, согласованные изменения APPLIED after validation. Следующий отдельный результат — новый implementation-readiness verdict; PASS и последующая deterministic sprint-status generation заранее не заявляются.**
