# Final re-review — Corporate KB DB/catalog и planning/design package

Дата финальной проверки: 2026-11-06  
Scope: только ранее зарегистрированные F-01–F-20 и R-01–R-07 в актуальных `database.md`, `contracts/database-catalog.yaml`, canonical/API/event contracts и human-facing planning/design docs. Scope не расширялся.  
Режим: **review only**. Изменён только этот запрошенный review report; исходные артефакты не изменялись.

## Verdict

**NO FINDINGS — в запрошенном scope не осталось CRITICAL/HIGH/MEDIUM findings.**

Все прежние HIGH/MEDIUM findings F-01–F-18 и R-01–R-07 закрыты. Намеренный **DESIGN_NOT_EXECUTED** для T00, T01/CF, A01–A36, integrations, migrations и rehearsals не является finding и не переводился в PASS. T00 остаётся IN_PROGRESS, G0 — OPEN, owner approval отсутствует.

Два ранее известных LOW wording finding F-19/F-20 остаются LOW и не входят в запрошенный результат. Этот verdict является только результатом design review, **не integration PASS и не G0 approval**.

## Оставшиеся CRITICAL/HIGH/MEDIUM

**Нет findings.**

## Закрытие последних R-01–R-07

| ID | Статус | Проверенное доказательство |
|---|---|---|
| R-01 — recorded accepted crash window | **RESOLVED** | `openapi.yaml:2218-2297,2432-2496`: recorded accepted имеет `attempts=[]`, synthetic `no_merge_proven` отсутствует, recovery/quarantine разрешены; rejected/cancelled также не создают attempts. `projection-mapping.md:13-35` и `database.md:975,1005-1016,1083-1085` явно сохраняют `recorded + unresolved recovery + attempts=[]` без no-merge claim. T01-CF-21 содержит crash-window vector. |
| R-02 — prerequisite run readiness | **RESOLVED** | `database-catalog.yaml:1573-1594,1627-1635,1665-1675` требует validated full parent, ready descriptor, nonempty hashed evidence и validated preflight; `:1731-1765` связывает exact preflight descriptor evidence. `projection-mapping.md:66-67`, `database.md:991-992` запрещают requested/failed/unvalidated parents и `{}`. CF-12/CF-24 содержат negative vectors. |
| R-03 — valid policy и ready/exact group evidence | **RESOLVED** | `database-catalog.yaml:492-543`: parent context issuer/evaluation binding, policy `valid`, group `ready`, exact snapshot ID/issuer/captured_at/membership hash/revocation epoch. Pending/invalid/building/failed/superseded inputs запрещены contract mapping `:2211-2215`. |
| R-04 — principal/issuer/personal grant integrity | **RESOLVED** | `database-catalog.yaml:212-246` связывает membership с issuer+stable identity и поддерживает explicit `registry/external_only`; `:347-409` требует valid policy, exact identity+issuer+stable ID, ready same-issuer group snapshot и корректные personal/group subject bindings. Human mapping — `database.md:163-171,216-233,1055-1056`. |
| R-05 — activating pointer evidence | **RESOLVED** | `database-catalog.yaml:1409-1415`: activating требует distinct request/run/snapshot IDs, preflight ready, published full/non-preflight/active/serving, same SHA/closure/hashes, validated timestamps, fence, nonnull index activation timestamp и `space_activated_at=NULL`. `projection-mapping.md:59-61` согласован. |
| R-06 — merged/outstanding cursor | **RESOLVED** | `database-catalog.yaml:1153-1157`: каждый non-pending state очищает outstanding ID/SHA; merged требует merged version+hash+commit и отдельный outcome proposal. OpenAPI non-pending rules требуют `outstanding_proposal_id=null`; `projection-mapping.md:63` и `database.md:989` согласованы. CF-25 покрывает negative cases. |
| R-07 — failed/conflicted integrity evidence | **RESOLVED** | `database-catalog.yaml:798-802` требует полный note/tag object/target и canonical/note/tag hashes для `recorded/merge_attempted/merged/failed/conflicted`, с explicit invalid reason handling. `database.md:385,975,1012-1016` и rebuild rules `:1083-1085` переводят missing/mismatched integrity в `invalid`. |

## Закрытие исходных F-01–F-18

| ID | Статус | Финальное подтверждение |
|---|---|---|
| F-01 — recovery clear | **RESOLVED** | `operations.md:253-266`, `architecture.md:286-296`, `database.md:924-975`: target-wide conclusive reconciliation; invalid/terminal/supersedes без proven outcome не очищают barrier. |
| F-02 — same-decision retry | **RESOLVED** | `database.md:934-975`, `openapi.yaml:2290-2297`: guarded `failed→merge_attempted`, same decision/new real attempt, fresh preconditions; conflicted/invalid terminal. |
| F-03 — preflight→published | **RESOLVED** | `database.md:981-985`, `database-catalog.yaml:1662-1675,1763-1769`: separate request/run/snapshot IDs, same SHA/closure/hashes, preflight never active/serving. |
| F-04 — active CAS across generations | **RESOLVED** | `database.md:990-992`, `database-catalog.yaml` `publication_fences`/`active_pointers`: per-Space/profile fence/CAS без generation в lock key; stale owner zero rows. |
| F-05 — kb_index cross-Space/exact SHA | **RESOLVED** | Full composite document/snapshot/pointer bindings повторно проверены в актуальном catalog; wrong Space/repository/target/SHA/policy triple отклоняются. |
| F-06 — kb_authz cross-Space | **RESOLVED** | Composite Space/repository policy/cutover/grant bindings сохранены и дополнены valid/principal checks. |
| F-07 — barrier links | **RESOLVED** | `target_barrier_decisions`, composite decision/run/findings scopes и barrier-clear CHECK присутствуют; recorded crash recovery добавлен без synthetic attempts. |
| F-08 — cutover/source/error perimeter | **RESOLVED** | Same-perimeter request/proposal/run/snapshot bindings сохранены; outstanding/outcome references разделены. |
| F-09 — live_operational cursor | **RESOLVED** | Cursor ownership enum и events допускают только `migrated/source_managed/curated`; live operational остаётся typed read-only observation. |
| F-10 — canonical mappings | **RESOLVED** | `projection-mapping.md` и `canonical_projection_mappings` покрывают Decision/attempts/quarantine, Cutover, ProposalView, index/source states, generation/profile, AuthZ и paths. |
| F-11 — R-index drift | **RESOLVED** | Дублирующий R-index отсутствует; полный mapping находится в `traceability.md`. |
| F-12 — I-index drift | **RESOLVED** | Дублирующий I-index отсутствует; I01–I14 полностью представлены в `traceability.md`. |
| F-13 — A20 baseline gate | **RESOLVED** | `test-plan.md:337`: `Gate: G0 (baseline) + G3 (upgrade)`. |
| F-14 — G0 criteria | **RESOLVED** | `operations.md:489-495`: required capabilities не заменяются documentary waiver; connector selection не добавлен как ранний G0 dependency. |
| F-15 — tracker A links | **RESOLVED** | `tasks.md:21,23`: T02=A01,A32; T04=A08,A10; static audit подтвердил отсутствие extra direct links. |
| F-16 — semantic refs | **RESOLVED** | Несуществующий `kb_ops.documents` отсутствует; `[OPS]` указывает на существующий `operations.md`. |
| F-17 — stale ADR/contracts | **RESOLVED** | `architecture.md:426-455` ссылается на фактические ADR/contracts. |
| F-18 — operations existence | **RESOLVED** | `planning-input.md:57-65`, `tasks.md:57-60` отражают существующий `operations.md` как DESIGN NOT EXECUTED. |

## LOW вне запрошенного результата

- **F-19 — LOW, частично остаётся:** legacy `human merge` wording сохраняется в `spec.md:902,1077`; прежний `architecture.md:261` больше не содержит проблемную формулировку. Не CRITICAL/HIGH/MEDIUM.
- **F-20 — LOW, остаётся:** singular `тестовый репозиторий` в `spec.md:899,937,953`, тогда как T01 требует два repositories=Spaces. Не CRITICAL/HIGH/MEDIUM.

## Независимые read-only проверки

### Catalog, ownership и integrity

- **15 YAML/JSON contract files** успешно разобраны без установки зависимостей.
- Каталог содержит **39 tables / 63 FK**. Все FK остаются внутри своей схемы; referenced tables/columns существуют и соответствуют объявленным PK/unique.
- `cross_schema_table_writes: forbidden`, owners/writers/migration owners и retrieval read-only сохранены.
- Rebuild/security/retention metadata заполнены для всех 39 tables. Conservative recovery, fresh AuthZ, full index rebuild и Git mirror/decisions/assets/authorization backup boundaries сохранены.

### R/I/A/T/E mappings

- Traceability содержит **R=18, I=14, A=36, CF=30, T=21, E=9**.
- `test-plan.md` содержит ровно **36** сценариев A01–A36.
- Прямые R→A и T→A mappings соответствуют `spec.md` v1.3; tracker extra direct acceptance links отсутствуют. **MATRIX_AUDIT_OK**.
- CF-01–CF-30 остаются DESIGN_NOT_EXECUTED inputs, не выполненными tests.

### Ссылки и статусы

- **405 local/cross-file `$ref`** успешно разрешены.
- **351 Markdown file/anchor target** в 11 human-facing docs + projection mapping проверен; отсутствующих targets нет.
- `operations.md`, ADR-03–ADR-16, `projection-mapping.md`, `t01-contract-tests.yaml` и contracts README существуют.
- Ложных product/integration PASS, VERIFIED или DONE не обнаружено. Documentation/reference checks не выдаются за real acceptance evidence.

## Границы verdict

Product tests, migrations, JSON Schema conformance suite, sandbox GitLab/IdP/PostgreSQL/CI/hoster.ai checks, restore drills и external calls не запускались. Отсутствие findings относится только к повторно проверенным design artifacts и прежним findings; оно не снимает T00/G0 blockers и не разрешает implementation.
