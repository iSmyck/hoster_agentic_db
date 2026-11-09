---
name: Corporate KB test plan
type: test-strategy-and-acceptance-design
status: design_not_executed
created: '2026-11-06'
updated: '2026-11-08'
specification_version: '1.3'
audience: Команда архитектуры, разработки, QA, security и эксплуатации
---

# Corporate KB — test plan для G0 и последующего планирования

## 1. Статус, границы и правила доказательств

**Все сценарии имеют статус DESIGN NOT EXECUTED.** Этот документ планирует проверки и evidence, но не сообщает о выполненных тестах, интеграциях, restore drills, operational owner acceptance или production readiness. Отдельный T00/G0 owner design approval получен и не меняет статус сценариев. Он не разрешает implementation, migrations, production corpus load, deploy, destructive cleanup, платные внешние вызовы или включение egress.

Приоритет: [Architecture Spine](architecture-spine.md) AD-1–AD-17 → [spec.md](spec.md) v1.3, R01–R18 и I01–I14 → [ADR](adr/README.md) → [architecture.md](architecture.md), [integration.md](integration.md), [database.md](database.md), [components](components/) и [contracts](contracts/README.md). Canonical↔projection rules и обязательный DESIGN_NOT_EXECUTED vector catalog: [projection-mapping.md](contracts/projection-mapping.md) и [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml). Единственный correction-task contract для E04.7/T07b: [docops-correction-task-v1](contracts/docops-correction-task.schema.json) + [API/lifecycle](contracts/docops-correction-api.md). Дополнительный контекст импорта и медиа: [content-standard.md](content-standard.md). Phase gate и evidence rules: [AGENTS.md](../../AGENTS.md) и [tasks.md](tasks.md).

Обозначения:

- **REQUIREMENT** — обязательное поведение R/I и принятых AD/ADR.
- **DESIGN** — планируемый способ проверки в этом документе.
- **UNKNOWN** — baseline, versions/editions, code paths, tooling, endpoints, connectors и параметры, которые ещё не подтверждены в T00.
- **DEFERRED** — возможности вне MVP; отсутствие теста не является разрешением реализовать их без новых требований и ADR.
- **BLOCKED** — реальная интеграционная проверка невозможна до предоставления соответствующего доступа и pinned baseline. Mock не превращает такую проверку в PASS.

Pinned baseline зафиксирован: [baseline.md](baseline.md) задаёт Open WebUI `v0.13.0` (`c38885a1…`), GitLab CE `19.5.3`, PostgreSQL `18.6` + pgvector `0.8.7`, toolchain и reproducible commands. Команды и окружение будущих прогонов выводятся из этого pinned baseline и фиксируются в evidence. **T00 DONE/G0 APPROVED; TipTap adapter selected (G0-D8)**. Final retrieval parameters, model IDs/dimensions и production limits остаются owner decisions/TBD и здесь не выбираются.

**T00 baseline evidence как вход design review:**

Собрано sanitized audit evidence ([evidence/t00](evidence/t00/README.md)); это **capability/audit результаты на synthetic sandboxes, не выполненные A01–A36 и не PASS сценариев этого плана**:

| Область | Результат | Ограничение |
| --- | --- | --- |
| GitLab CE capabilities | 42 completed probes ([gitlab-capabilities](evidence/t00/gitlab-capabilities.md)) | Нет target-branch CAS; privileged Owner bypass — G0-D3 |
| Identity adapter | Keycloak 9/9 PASS ([identity](evidence/t00/identity-capabilities.md)) | Stock OIDC 4 PASS/2 FAIL ([OIDC runtime](evidence/t00/openwebui-oidc-runtime.md)); LDAP runtime не выполнялся |
| PostgreSQL/pgvector | External migrator PASS, head `e42c8f710a36`, runtime DDL denial PASS ([toolchain](evidence/t00/openwebui-toolchain.md)) | `kb_*` schemas не созданы |
| Retrieval | pgvector deterministic gates 22/22 PASS ([benchmark](evidence/t00/retrieval-benchmark.md)) | Production quality/latency thresholds — owner TBD |
| Frontend toolchain | Vitest 4/4 и direct Vite build PASS ([toolchain](evidence/t00/openwebui-toolchain.md)) | svelte-check FAIL (5722 errors), ESLint crash, `npm run build` OOM — G0-D9 |
| Editor | TipTap adapter selected и owner-approved (G0-D8); WYSIWYG retained. Headless split: CodeMirror byte fidelity PASS / TipTap normalization-loss ([editor audit](evidence/t00/openwebui-rag-editor-audit.md)) | Browser/IME/accessibility/XSS/full managed preview — deferred T04, не PASS. Realtime collaboration/CRDT вне MVP; conflict/fresh revisions/full diff/new ProposalVersion обязательны |
| CI Runner exact-SHA | PASS | [ci-runner.md](evidence/t00/ci-runner.md), 7/7 synthetic checks |
| License | Engineering evidence записано ([license review](evidence/t00/openwebui-license-review.md)) | Legal clearance отсутствует — G0-D10 |

### 1.1. Правила результата проверки

1. `DESIGN` — сценарий описан, но не запускался; это статус всех A01–A36 сейчас.
2. `BLOCKED` — указаны недоступная зависимость/доступ, владелец блокировки и условие разблокировки; нельзя выдавать за PASS.
3. `PASS` — допустим только после фактического запуска на зафиксированном окружении с проверяемым результатом и sanitized evidence.
4. `FAIL` — фактическое поведение нарушает ожидаемый REQUIREMENT; mock failure и upstream failure разделяются.
5. `N/A` — допустимо только по согласованному ADR, например для extraction при доказанном Markdown-only workload; не выбирается для экономии проверок.
6. `VERIFIED` и `DONE` задач следуют [spec.md](spec.md): сначала реально выполненные проверки, затем критерии, review и документация. Наличие этого плана не меняет статусы T00/G0.
7. Unit mock пригоден для state machines и детерминированных алгоритмов, но не доказывает GitLab/IdP/PostgreSQL/CI/hoster.ai integration.
8. Security и merge/recovery gates не закрываются вероятностным LLM score, UI smoke или отсутствием кнопки.

### 1.2. Evidence contract для будущих прогонов

Для каждого запуска фиксировать: test ID и версию плана; Open WebUI commit/tag; GitLab version/edition; PostgreSQL/CI/toolchain; code/config/model/tool-schema versions; synthetic fixture version; exact corpus/base/proposal/merge/snapshot SHAs; commands и environment; controlled event ordering; результат; blocked checks; rollback/upgrade impact.

Машинные reports предназначены для `_bmad-output/test-artifacts`; в [evidence](evidence/) помещаются только sanitized reviewable references. Не сохранять реальные клиентские документы, tokens, passwords, private endpoints, bind secrets, raw private queries/documents/chunks, PII snippets, provider payloads или необработанные MR evidence. Git refs, IDs, hashes, timestamps и result codes сохраняются в объёме, необходимом для воспроизведения.

## 2. Цели по gates и критические stop conditions

| Gate | Планируемый объём доказательств | Запрещённое упрощение |
| --- | --- | --- |
| G0 / T00 | Pinned baseline; capability matrix; real sandbox GitLab/IdP/DB checks после доступа; editor/retrieval audit; requirement-to-test mapping A01–A36; explicit owner review record | Не закрывать G0 наличием DESIGN или ADR-файлов; не заменять недоступные capabilities предположениями |
| G1 | A01, A04–A10, A17–A18, A24, A27–A30, A33–A34, A36 в применимом vertical slice; одна страница, два независимых человека, business approver без GitLab user; revert-MR | UI-only merge, mock no-bypass, пропуск race/crash/parent/trailer/self-approval tests |
| G2 | A02–A03, A11–A16, A21–A23, A25, A31–A32, A35–A36; controlled cutover, corpus, exact+semantic retrieval, hoster endpoint, P0 suite | Preflight serving, production corpus без perimeter/sign-off, качество без corpus SHA/config/dataset |
| G3 | A14–A15, A19–A20, A33 и операциональные rehearsals; один внешний источник без auto-merge; second dedicated instance; backup/restore/upgrade | Restore по наличию dump; второй клиент через code branch; неизвестный merge outcome открыт после rebuild |
| G4 | Измеренные profile optimizations, shadow evaluation и controlled rollout по [operations.md](operations.md) | Новый engine/cache/OpenSearch без benchmark и ADR; численные цели без владельца |

**Stop conditions:** неподтверждённые required GitLab exact-SHA/parent/trailer/note/tag/export/merge-only-GO capabilities; любой direct push/merge bypass; отсутствие stable identity/group recheck; невозможность ACL/SHA-safe retrieval; cross-schema writer; cutover activation window; потеря decisions/assets closure. Соответствующий gate остаётся BLOCKED, а инвариант не ослабляется.

## 3. Стратегия по уровням тестирования

| Уровень | Назначение и обязательный объём | Среда и ограничения | Типовое evidence |
| --- | --- | --- | --- |
| Unit | Path/Unicode normalization; stable IDs/tree/cycles/orphans; patch uniqueness; canonical JSON/JCS/hash; Decision/merge state machines; source cursor; dependency closure; idempotency; policy evaluation; generation/profile ordering | Изолированные deterministic tests и mocks только внешних портов. Не утверждать upstream integration | Test report, input/output vectors, sanitized state transitions, coverage по критическим веткам без выдуманного процента |
| Contract | Все closed JSON Schemas и YAML contracts включая `document-front-matter-v2`, `authz-context-v2`, `export-manifest-v2`, `agent-tools-v2`, `docops-correction-task-v1`; local/cross-file `$ref` и `x-contract-invariants`; unknown/malformed fields; exact full SHA; UUID/time/enums; bounded cursor/truncation/errors; Proposal/Decision byte+hash equality; API↔tools↔events↔DB mappings; correction lifecycle/CAS/idempotency/no-MR/backup negatives; DB full-perimeter assertions. Обязательный каталог — [T01 CF-01–CF-30](contracts/t01-contract-tests.yaml) и [correction API](contracts/docops-correction-api.md) | Tooling выбирается из pinned T00 baseline. Schema limits — PROPOSED exchange bounds, не production SLA. Catalog и mappings — DESIGN output, не VERIFIED test. Numeric thresholds не добавлять | Schema/semantic/consumer/concurrency vectors, compatibility diff, projection roundtrips, negative matrices, sanitized error codes |
| Integration | Real GitLab exact-SHA reads/merge, MR notes/protected annotated tags/protections/webhooks/export; real PostgreSQL roles/migrations/CI; real LDAP/OIDC; object storage; selected source sandbox; real approved hoster.ai | Только после доступа и pinned baseline. Отдельный synthetic sandbox project/group и scoped credentials. Без доступа — BLOCKED | Environment/versions/commands, Git refs/parents/trailers/note IDs/hashes, role denials, event timeline, sanitized API results |
| Browser | Неинженер проходит tree→read/edit→proposal→review→decision→restore без Git/CLI; full diff; reload/double-click; explicit statuses; accessibility/keyboard; XSS-safe preview; personal Notes/ordinary chats regression | Реальное приложение и server enforcement; browser mock не закрывает G1. Business users не получают GitLab accounts | Role/action trace, screenshots без private data, exact SHA correlation, UI state/recovery observations, accessibility notes |
| Security | Deterministic negative tests для merge/push/grants, IDOR/cross-Space, all-channel bypass, prompt injection, revocation, front matter/policy tampering, malicious import, provider egress/fallback, secrets/logging | Zero unauthorized disclosures в согласованном adversarial suite. LLM robustness — дополнение, не замена deterministic checks | Attack vector, channel/credential, expected/actual denial, proof нуля `main` writes/no payload, sanitized logs |
| Fault injection | Target race; crash до/после DecisionRecord; DB barrier; request accepted+response lost; timeout; lock loss/handover/fencing; late response; crash после merge до projection; полная потеря БД; webhook/CI/provider outages; late jobs | Сначала unit state matrix, затем controlled real sandbox после доступа. Не destructive production tests | Injected point/timestamp, inflight request fingerprint, owner/fencing, Git-derived outcome, barrier age/state, one-or-zero merge proof |
| Rebuild | Полная потеря/пересборка `kb_ops`, `kb_authz`, `kb_index` по отдельности и совместно; conservative recovery; fresh contexts; full index и pointer recreation | Только clean isolated synthetic environment. External merge freeze первым; unknown outcomes не очищать | Before/after closure, scanned refs/MRs/policies/groups/assets, quarantine list, rebuild и reconciliation evidence |
| Restore | Mirror+MR notes/metadata+decision/cutover tags+manifests+objects+config/secrets policy → clean dedicated instance; explicit grants; conservative `kb_ops`; full `kb_index`; closure validation | Без доступа к GitLab metadata/object store/clean instance — BLOCKED. Не восстанавливать active pointer из непроверенного backup как истину | Package hashes, missing[], refs/decisions/assets/policies closure, parent/trailer checks, isolated grants и sanitized restore report |
| Evaluation | Expert synthetic golden set: direct read, exact/semantic retrieval, factual support, citation correctness, abstention/no-answer, conflicts, stale/private cases, proposal usefulness; cold/warm TTFT/full response и стоимость | promptfoo или согласованный adapter только после baseline; graders local/approved. Quality thresholds, corpus/concurrency, p95/p99 и budgets — owner TBD | Corpus SHA, dataset/rubric version, model/config/tool schemas, отдельные retrieval/answer/citation/abstention metrics и human review |

Дополнительные правила:

- Детерминированные A04–A15/A17/A18/A21–A36 выполняются как contract/negative/concurrency/crash/integration tests там, где поведение детерминировано.
- Реальные hoster.ai streaming/tool tests включают sequential/parallel calls, malformed args, cancellation/retry/timeouts и revocation during stream. Без реального endpoint/credentials они BLOCKED.
- Performance measurements не создают SLA: TTFT и full response, Git read/merge latency, CI lag и cold/warm стоимость фиксируются раздельно; пороги согласует владелец.
- Регулярность PR/nightly/weekly определяется после измерения длительности на pinned CI. Дорогие fault/restore/rebuild и paid/external calls не запускаются неявно.

## 4. Доступы и текущие блокировки реальных проверок

| Зависимость | Что требуется перед integration execution | Текущий статус DESIGN | Условие разблокировки |
| --- | --- | --- | --- |
| GitLab | Pinned version/edition; synthetic sandbox group/projects; scoped proposal/merge/CI/export credentials; ability to inspect notes/tags/audit/protections | **BLOCKED для real integration** | Доступ и baseline capability matrix; недоступная required capability — G0 stop/design review |
| LDAP/OIDC | Synthetic AD/OpenLDAP/OIDC users/groups; stable attributes; read-only bind/client configuration; nested groups; group mutation controls | **BLOCKED для real integration** | Доступ к sandbox IdP и подтверждённые upstream seams; нет fallback на email/login |
| PostgreSQL + CI | Isolated DB and roles; owner migration procedures; exact-main CI reader; controlled job crash/late completion; webhook transport | **BLOCKED для real integration** | Pinned deployment/toolchain и sandbox; DDL/commands только из approved baseline |
| hoster.ai studio | Approved real endpoint/model inventory/profile/egress and credentials; auxiliary models inventory | **BLOCKED для real integration** | Явное разрешение на endpoint/calls; mocks остаются только unit evidence |
| Source connector | Owner-selected SharePoint/Bitrix24/Kayako и synthetic sandbox objects/auth | **BLOCKED / UNKNOWN** | Выбор первого connector и проверка edition/API/deletions/attachments/access hints |
| Object storage | Isolated immutable/versioned bucket/container и scoped read/write/export credentials | **BLOCKED для real integration** | Согласованный layout, synthetic objects и hash/version API |
| Second client | Отдельные repositories, DB, objects, secrets, backups, egress и config | **BLOCKED для real integration** | Отдельный isolated synthetic deployment без изменения reusable core |

Недоступность одной зависимости не запрещает независимые unit/contract проверки, но область PASS явно ограничивается. Реальные клиентские документы и секреты для разблокировки не требуются: используются только synthetic fixtures.

## 5. Synthetic fixture repositories и данные

### 5.1. Обязательный периметр

Создание fixtures планируется в T01 после G0; сам этот план их не создаёт. Имена ниже — **DESIGN для synthetic tests**, не production naming/layout decision.

| Fixture repository | Ровно один Space | Назначение и содержимое |
| --- | --- | --- |
| `fixture-kb-sales` | `fixture-sales` | Curated/migrated/source-managed pages; nested tree и Cyrillic paths; stable UUID links; repeated headings; long page; same basename в разных ветках; attachments; open/rejected/draft proposals; `inbox/`, templates, service paths; archived page; access/approval policies; engineering-only CODEOWNERS |
| `fixture-kb-sales-pricing` | `fixture-sales-pricing` | Отдельный pricing corpus и attachments с другой ACL; собственные policies, history, protected refs, cutover/index/export/backup. Содержимое не копируется в общий products path |

Дополнительно для A19 используется `fixture-client-b` с собственными repositories=Spaces и конфигурацией, а не branch клиентского кода. Для cross-Space tests оба основных repository имеют независимые `main`, decision/cutover tags, CI runs, generations/profiles/pointers, mirrors и manifests.

### 5.2. Пользователи, группы и credentials

Все identities и group IDs synthetic; stable IDs условные opaque values, не email/login. Business users, включая owners/source owners, **не имеют GitLab user records**. GitLab users создаются только для engineering/service контуров.

| Synthetic actor / group | Platform/GitLab роль | Обязательные проверки |
| --- | --- | --- |
| `sales-reader` / `fixture-sales-readers` | Reader только `fixture-sales` | Read/search/chat; нет propose/write/merge/grants/export history без отдельного права |
| `sales-author` / `fixture-sales-authors` | Author `fixture-sales` | Draft/proposal; не approver собственных версий |
| `sales-approver` / `fixture-sales-owners` | Business approver по path scopes `approval-policy.yaml`; без GitLab user | Review/accept/reject/cancel; нет direct GitLab merge; group-assigned queue |
| `sales-editor` | Author/version editor `fixture-sales` | Новая ProposalVersion; self-approval запрещён даже при прежнем approver |
| `source-owner-sales` | Source owner со stable external identity; без GitLab user | Data barrier и source provenance; не заменяет business approver |
| `engineering-reviewer` | GitLab engineering user/CODEOWNERS reviewer | Engineering review only; после cutover нет direct push/merge; не даёт business approval |
| `pricing-reader`, `pricing-author`, `pricing-approver` | Соответствующие роли только `fixture-sales-pricing` | Pricing isolation; отсутствие доступа к чужому Space по умолчанию |
| `mover-user` | Групповое членство изменяется между Spaces/approver groups | Grants и review queue меняются; stable attribution сохраняется |
| `leaver-user` | Удаляется из external group во время теста | Revocation ≤30 минут; sensitive recheck; subscription closure |
| `outsider` | Нет grants | Default private и anti-enumeration `NOT_FOUND` по policy |
| `space-operator`, `export-operator` | Делегированные platform/operational capabilities | Нет direct merge; full export только при праве на Space и всю историю |
| `agent-bot` | Scoped proposal credential | Read/search/propose only; merge/export/grants/shell/SQL запрещены |
| `connector-bot` | Source read + proposal-only GO capability | Нет merge/index/grant credentials и auto-merge |
| `go-proposal-service` | Отдельная GO proposal/write identity | Branches/MR/notes/tags в разрешённом scope; merge permission отсутствует |
| `go-merge-service` | Отдельная merge service identity | После cutover единственная managed identity с normal merge permission; недоступна UI/agent/connector/CI. Privileged Owner bypass — incident с reconciliation/quarantine, не managed path |
| `ci-index-worker` | Exact-main/object read + `kb_index` writer | Нет merge/canonical push/grants; pointer только после validated run |
| `retrieval-service` | `kb_index` read-only | Нет mutations, merge или самостоятельного grant decision |
| `identity-adapter` | Managed upstream grant seam + `kb_authz` writer | Нет `kb_ops`/`kb_index` writes и arbitrary upstream SQL |

### 5.3. Контент, policies и source registry

Обязательные fixture sets:

- **F-DOCS:** root/child/orphan/cycle/duplicate-ID vectors; valid nested documents; stable rename; Unicode NFC/NFD и запрещённые `..`, separators/control chars; повторяющиеся headings; explicit long-read chunks; front-matter-v2 stable `links[]`/swapped UUID, `valid_until` future/expired/removed + exact DocOps revision, archive inverse/replacement/descendants, outer/inner origin mismatches, `DOC-0001` и attachments.
- **F-CORRECTION:** exact reported revisions и later HEAD; trusted requester/owner/user/group identities; sanitized evidence objects+hashes; optional linked MR without/with verified governed merge; open/in_review/resolved/cancelled current+event projections; stale task_version; idempotency same-key/same/different actor/route/path/payload; no-MR reason/evidence; missing/corrupt kb_ops backup и restore/reconciliation vectors. Task никогда не canonical content/DecisionRecord.
- **F-OWNERSHIP:** `curated`, `source_managed`, `migrated`; previous imported base/current curated/incoming versions; no-op hash; same-paragraph conflict; source deletion/tombstone. `live_operational` существует только как typed read-only source fixture со `snapshot_time`, без wiki front matter.
- **F-POLICIES:** valid access+`approval-policy.yaml` bundle **per Space** с одинаковыми `policy_bundle_id`, repository/Space и full access+approval revisions; independent group snapshots/revocation epochs; unique rule IDs/normalized prefixes и longest-prefix path-scoped approvers; engineering-only CODEOWNERS; audited personal exception. Negative variants: borrowed other-Space bundle/snapshot, mixed bundle/revisions, partial activation, duplicate `/`/parent-vs-`/pricing` rules, NFC/NFD/trailing separators, потерянная group/path role, page-level ACL attempt, `..`, Unicode ambiguity, self-approval и absolute↔relative roundtrip mismatch. Поле `access` встречается только в noncanonical malicious input и не должно влиять на grants.
- **F-MEDIA:** decorative; illustrative; substantive с marked automatic description и original ref; critical verified/unverified; handwritten transcribed/untranscribed; small Git asset и large immutable external object; second attachment revision; missing object; hash/size/media mismatch; mutable URL; revoked attachment.
- **F-MALICIOUS:** XSS/active HTML/MDX, hidden prompt injection, archive traversal, absolute/ambiguous paths, symlinks, `.git`/`.env`/secret-like canaries, oversized/decompression-bomb inputs, invalid UTF-8, unsupported format, duplicate IDs, unresolved required links. Все secrets/PII — synthetic canaries, не реальные значения.
- **F-PROPOSALS:** exact base/proposal pairs; human/agent/connector principals; trusted run; reviewer edit/rebase; accept/reject/cancel DecisionRecords; missing/mismatched note/tag; wrong tag target/hash; supersedes; parent/trailer corruption; idempotency replay same/different actor/route/payload; invalid+unknown, conclusive failed same-decision/new-attempt guarded retry, terminal conflicted/invalid и второй MR на том же target. Agent vectors отдельно включают WholeDocumentChange/editProposalVersion/front-matter/attachment/archive forbidden diffs и valid `AgentAnchoredPatchChange`.
- **F-INDEX:** eligible published snapshots, preflight, pending/rejected branches, inbox/templates/service paths, archive/delete, changed linked dependency, changed attachment/policy включая approval revision, full/incremental closure mismatch/missing independent proof, two generations/profiles и simultaneous old/new publication на одном Space/profile. Cutover имеет separate preflight/published request/run/snapshot IDs при одинаковых SHA/closure/hashes. Никакой ordering по lexicographic SHA.
- **F-EXPORT:** accepted recorded/merge_attempted/merged/failed/conflicted/invalid и rejected/cancelled Decisions с explicit attempt+recovery, MR note metadata/canonical hashes, protected annotated tag objects и peeled targets, real merge parents/trailers только для merged, policy/grants mapping, refs/documents/decisions/assets/authorization closure hashes, missing/rejected asset без fabricated hash и missing note/decision/batch negative variants.
- **F-EVAL:** synthetic expert golden questions для exact/semantic search, citations, no-answer, conflict, stale/private cases и single-page proposal. Реальные вопросы продаж добавляются позднее отдельным согласованным sanitized dataset, не подменяются выдуманными сейчас.

Data profiles:

- `strict` — default для основного corpus; source owner checklist + post-conversion scan + human disposition каждого synthetic PII hit; unresolved hit блокирует admission.
- `pii_permitted` — только отдельный synthetic config с явно помеченным fictitious legal-basis record и approved internal inference route. Это не юридическое заключение и не разрешение реальной обработки; внешний PII egress проверяется как запрещённый.

## 6. Матрица исполнения и управление нестабильностью

1. Сначала T00 capability checks и contract/fixture foundation; затем unit/contract; затем real integration; browser/security/fault; rebuild/restore; evaluation и operational rehearsals.
2. Каждый concurrency test использует два независимых клиента и controllable ordering; exact SHAs получают во время прогона, не выбирают по строковому порядку.
3. Каждый crash test имеет отдельный clean target, inflight request fingerprint и доказательство исхода из GitLab, а не из worker memory или HTTP status.
4. Повтор одного immutable input обязан быть идемпотентным. Изменение HEAD/policy/profile/source создаёт новый versioned input, а не мутирует старый evidence.
5. Flaky upstream и product defect разделяются. Retry не скрывает FAIL; uncertain merge не повторяется с новым decision/idempotency key.
6. Test timeout не приравнивается к отсутствию merge. Ожидание reconciliation ограничивается test harness, но quarantine в продукте не очищается по таймеру.
7. После каждого fault/rebuild/restore test проверяются соседний target/Space/client: их merges, ACL, pointers и export не изменились.
8. Численные latency/freshness/quality/capacity/retry/retention/RPO/RTO/budget thresholds отмечаются `OWNER_TBD`; не превращаются в PASS/FAIL критерии до решения владельца.

## 7. Полный сценарный каталог A01–A36

В каждом сценарии evidence является **планируемым**, не существующим отчётом. «Компоненты» перечисляют основной, но не исключительный scope. Все real-integration зависимости подчиняются разделу 4.

### A01 — Дерево, deep link, WYSIWYG и review без Git/CLI

- **Цель:** подтвердить единый бизнес-интерфейс и stable opaque UUID после rename внутри одного repository=Space.
- **Предусловия:** activated `fixture-sales`; F-DOCS; `sales-author` и `sales-approver` без GitLab users; owner-selected TipTap adapter с обязательным T04 fidelity/browser gate, не предполагаемым PASS.
- **Ключевые шаги:** открыть tree и stable deep link; изменить страницу в WYSIWYG; сохранить draft и создать MR; approver проверяет text/front-matter-v2/structure/stable links/valid_until/archive/origin/attachments/rationale/evidence и DocOps projection; выполнить rename через reviewed MR и GO merge; повторно открыть прежний ID-link. Для concurrent authors проверить conflict detection, exact/fresh revisions, full diff и новую ProposalVersion без realtime CRDT.
- **Ожидаемый результат:** весь путь выполнен без Git/CLI; UUID/parent/target links и canonical provenance сохранены; `archived ↔ archive` и revision-bound valid_until согласованы; full preview достоверен; `main` меняется только verified GO merge; statuses различают draft/in_review/published/indexed/archived без подмены proposal superseded.
- **Evidence:** role/action browser trace, exact base/proposal/merge SHAs, before/after tree/ID map, diff checklist, отсутствие business GitLab users.
- **Требования/компоненты:** R01, R02; Open WebUI navigator/editor/review, GO, Identity/AuthZ, GitLab. Levels: browser, integration, contract. Gate: G1.

#### Correction-task supporting vectors — E04.7/T07b, без нового acceptance ID

Supporting ownership: A01,A07,A22,A26,A27,A36; новые A IDs не создаются. Машинные vectors — [T01-CF-06/10/20/25](contracts/t01-contract-tests.yaml), semantic contract — [correction API](contracts/docops-correction-api.md).

- Выполнить create/get на exact revision с server-derived requester, policy owner, evidence hash и optional linked MR; проверить open/in_review/resolved/cancelled, monotonic task_version, terminal replay и отсутствие canonical status/content writes.
- Проверить same-key replay, key reuse под other actor/route/path/payload, stale CAS, invalid transition, revoked/non-owner/cross-Space access, linked MR без merge proof и no-MR resolve/cancel без reason/evidence hash: ноль task/event/content side effects.
- MR-based resolution допускается только после normal ProposalRecord/MR/human DecisionRecord/GO merge; no-MR resolution означает disposition only.
- В clean synthetic restore проверить durable kb_ops current/events/evidence/idempotency backup и linked-MR reconciliation. Git-only rebuild не fabricate/delete/resolve/cancel tasks; unavailable real check — BLOCKED.

### A02 — Direct read exact revision, bounds, cursor и stale candidate

- **Цель:** проверить canonical whole/section read без silent truncation и без подмены stale candidate историческим текстом.
- **Предусловия:** F-DOCS long page с repeated headings; две canonical revisions; active index и отдельный stale candidate.
- **Ключевые шаги:** прочитать целиком и по `heading_path+occurrence`; пройти cursor chain с character/byte/item bounds; запросить explicit historical revision; выдать stale candidate и попытаться substitute current/historical fallback.
- **Ожидаемый результат:** каждый ответ содержит full `document_revision_sha`, section, `truncation.reason`, next cursor; pages не смешивают snapshots; historical read явно помечен/авторизован; stale candidate отклонён `STALE_INDEX_CANDIDATE`/`NOT_FOUND` без silent fallback.
- **Evidence:** bounded API traces, exact revisions, cursor/scope/snapshot linkage, concatenated-read hash, negative fallback result.
- **Требования/компоненты:** R03, R11; GO canonical read, Retrieval adapter, Open WebUI. Levels: unit, contract, integration. Gate: G2.

### A03 — Exact+semantic search только eligible activated published main

- **Цель:** проверить оба retrieval modes, citations, fresh Space scope и revision validation; исключить preflight/pending/rejected content.
- **Предусловия:** activated published snapshot; separate preflight; open/rejected MR; inbox/templates/service paths; F-EVAL; approved embedding route или явный BLOCKED.
- **Ключевые шаги:** выполнить exact и semantic queries с page/subtree/Space и two-Space scopes с independent repository/policy/group/epoch bindings; проверить per-Space fan-out, полный `SearchPage.snapshots[]`, candidates и selected canonical reads; подменить/удалить один cursor descriptor; повторить до activation и после revoke; изменить `document_revision_sha` кандидата.
- **Ожидаемый результат:** только eligible active published snapshot каждого Space; citations содержат Space/stable ID/full revision/section и тот же snapshot identity; scope вычислен сервером до payload без borrowed binding; preflight и nonpublished content невидимы; stale candidate или incomplete cursor context отклонён. Quality score не подменяет deterministic checks.
- **Evidence:** snapshot/generation/profile, candidate IDs/revisions, negative corpus inventory, citation map, fresh authorization results, отдельные exact/semantic metrics.
- **Требования/компоненты:** R04, R11; Retrieval adapter, CI/index, GO, Identity/AuthZ, Open WebUI. Levels: contract, integration, security, evaluation. Gate: G2.

### A04 — Reader не получает write/privileged capabilities

- **Цель:** независимо отклонить reader writes через UI/API/tools/channels и direct push/merge/grants на GO/GitLab уровнях.
- **Предусловия:** `sales-reader`; valid read access; agent/channel/OpenAPI fixtures; protected `main`.
- **Ключевые шаги:** попытаться создать draft/proposal/decision/grant/export; вызвать те же mutations через direct/deferred/note/automation/channel/OpenAPI/`call_tool`; выполнить direct Git push и merge с reader-associated credentials.
- **Ожидаемый результат:** чтение работает только в scope; каждая mutation denied server-side; GO и GitLab независимо фиксируют denial; ноль новых writes в `main`; anti-enumeration сохранён.
- **Evidence:** channel×operation denial matrix, sanitized errors, Git ref before/after, credential scope evidence.
- **Требования/компоненты:** R05, R16; Identity/AuthZ, Open WebUI tool gateway, GO, GitLab protections. Levels: contract, integration, security. Gate: G1.

### A05 — Create/edit формирует branch+MR+append-only ProposalRecord

- **Цель:** проверить exact base/proposal diff и trusted principals до любого canonical merge.
- **Предусловия:** `sales-author`, agent run и connector source fixtures; exact `base_sha`; valid approval policy.
- **Ключевые шаги:** выполнить human create/edit, agent curated body create и `AgentAnchoredPatchChange`, connector proposal с отдельным connector credential; через direct/OpenAPI/call_tool попытаться agent `editProposalVersion`, WholeDocumentChange/front-matter/attachment/archive/access и cross-Space path/body mismatch; повторить same idempotency key с тем же и изменённым actor/route/payload; попытаться подменить author/requester/run в payload.
- **Ожидаемый результат:** созданы attributed branch commit, MR и ProposalRecord с `author_stable_id`, `version_author_stable_id`, `requester_stable_id`, actor type, trusted optional run, rationale/evidence и payload hash; `main` unchanged; forbidden agent diff/path/body mismatch отклонён без writes; global key registry безопасно возвращает same replay, changed actor/route/path/payload → `IDEMPOTENCY_KEY_REUSED`; service identity не заменяет principals.
- **Evidence:** MR/ref diff, ProposalRecord schema/hash, principal provenance, idempotency results, `main` before/after.
- **Требования/компоненты:** R06, R07; GO proposal/draft services, Open WebUI agent gateway, GitLab. Levels: unit, contract, integration. Gate: G1.

### A06 — Новый commit/rebase инвалидирует approval

- **Цель:** доказать, что approval и DecisionRecord привязаны только к exact ProposalVersion.
- **Предусловия:** reviewed proposal с accepted DecisionRecord на `proposal_sha1`; independent editor.
- **Ключевые шаги:** создать новый commit и отдельно rebase; получить `proposal_sha2` и новый ProposalRecord/version author; replay старого decision и stale edit/accept; попытаться apply без нового independent review.
- **Ожидаемый результат:** старый approval/DecisionRecord не применяется к SHA2; `PROPOSAL_VERSION_MISMATCH` либо эквивалентный conflict; ноль `main` writes; требуется новая версия и независимый approver; apply не вызывает LLM regeneration.
- **Evidence:** SHA/version/principal chain, old/new Decision anchors, denial и target ancestry, provider call inventory отсутствия apply regeneration.
- **Требования/компоненты:** R08, R10; GO proposal/decision/merge, review UI, GitLab. Levels: contract, integration, browser. Gate: G1.

### A07 — Accept/reject/cancel и reload идемпотентны

- **Цель:** проверить durable outcomes для трёх actions и безопасный replay по `decision_id`.
- **Предусловия:** три eligible proposals от одного base на независимых targets либо последовательно восстановленных fixtures; independent approver.
- **Ключевые шаги:** выполнить accept, reject, cancel с respective `Idempotency-Key == decision_id`; double-click/reload/replay same requests; replay changed payload/key; проверить notes/tags/MR state/main/export entries.
- **Ожидаемый результат:** accept имеет максимум один verified real merge; reject/cancel закрывают MR без merge/`main` write; все actions имеют canonical note+protected tag; same replay возвращает существующий Git-derived result без side effects; changed reuse отклонён.
- **Evidence:** decision IDs, note IDs/tag targets/hashes, MR states, merge count/parents/trailers, replay response equivalence.
- **Требования/компоненты:** R08, R10; GO decision/merge, review UI, GitLab, export coordinator. Levels: contract, integration, browser. Gate: G1.

### A08 — Изменение target между proposal и accept

- **Цель:** исключить silent last-write-wins при stale `base_sha`.
- **Предусловия:** proposal P1 от base B0; независимый P2, который verified merged и передвинул target на B1.
- **Ключевые шаги:** попытаться accept P1; повторить с fresh idempotency key и попытаться automatic conflict merge; создать новую ProposalVersion только от B1 и повторить independent review.
- **Ожидаемый результат:** P1 получает `STALE_BASE`; ноль новых `main` writes отклонённой операции; no auto merge/rebase; новая ProposalVersion обязательна и получает новый independent approval.
- **Evidence:** B0/B1/P1 SHAs, target ancestry before/after, stale denial, new version/diff/review chain.
- **Требования/компоненты:** R09, R10; GO merge coordinator/lock, review UI, GitLab. Levels: unit, contract, integration. Gate: G1.

### A09 — Два concurrent accepts/different proposals

- **Цель:** проверить per-`(repository_id,target_branch)` serialization и отсутствие второго apply после changed HEAD.
- **Предусловия:** два независимых клиента, PA и PB от одного base на одном target; barrier free; controlled start barrier.
- **Ключевые шаги:** одновременно accept PA/PB и replay победителя; варьировать порядок lock/precondition/merge; попытаться провести losing operation после lock handover.
- **Ожидаемый результат:** максимум один verified apply из исходного base; loser получает conflict/`STALE_BASE`/`RECOVERY_REQUIRED` по фазе и не создаёт новых `main` writes; replay победителя возвращает тот же результат; никакого last-write-wins.
- **Evidence:** клиент/event timeline, owner/fencing tokens, lock order, merge count/parents, loser denial, target barrier/reconciliation state.
- **Требования/компоненты:** R10; GO lock/fencing/merge/recovery, GitLab. Levels: integration, fault-injection, security. Gate: G1.

### A10 — Restart, history, revert-MR и attribution

- **Цель:** сохранить durable drafts и Git ancestry/principals; restore только новым reviewed revert-MR.
- **Предусловия:** durable draft, accepted publication от `sales-author`/`sales-approver`, historical revisions и unsaved browser buffer.
- **Ключевые шаги:** restart services/browser; восстановить draft; открыть business history с bounded pagination/truncation и выбрать exact revision; попытаться read/restore чужой Space/group history; создать restore к выбранной revision через revert-MR; independent review/GO merge; проверить ancestry и атрибуцию.
- **Ожидаемый результат:** durable draft сохраняется, unsaved buffer не называется durable; history list и restore используют exact selected revision без silently substituted SHA; restore создаёт новый commit/merge без history rewrite/checkout в `main`; unauthorized history/restore anti-enumerated; principals сохранены и отличаются по ролям.
- **Evidence:** restart log correlation, draft/MR/history SHAs, revert parents/trailers, author/version/requester map, no-rewrite attestation.
- **Требования/компоненты:** R09; GO draft/history/restore, Open WebUI, GitLab. Levels: browser, integration, fault-injection. Gate: G1.

### A11 — Revoke private access до переиндексации

- **Цель:** прекратить все новые private payloads и live subscriptions после revocation, не ожидая index update.
- **Предусловия:** активные search/tree/stream/export sessions; stale index ещё содержит private candidates/attachments.
- **Ключевые шаги:** отозвать Space/group/policy grant и увеличить именно per-Space revocation epoch при неизменном соседнем Space; передать `kb.access.revoked.v1`; запросить tree/titles/snippets/chunks/files/history/decisions/export/tools; продолжить multi-Space cursor/stream; попытаться selected read и provider call.
- **Ожидаемый результат:** fresh deny применяется до payload и до model только затронутого actor/Space binding; contexts/cursors с полным per-Space descriptor+epoch set invalidated, subscriptions закрыты; stored index ACL не является allow; historical/revoked content не выдаётся; anti-enumeration сохранён.
- **Evidence:** revocation epoch/timeline, per-channel denial matrix, subscription close, provider payload absence, index unchanged proof.
- **Требования/компоненты:** R05, R11; Identity/AuthZ, Retrieval, Open WebUI, GO/export. Levels: integration, security, fault-injection. Gate: G2.

### A12 — Late generation, archive, CI outage и webhook loss

- **Цель:** сохранить active pointer и canonical history при event/index failures; восстановить freshness по ancestry reconciliation.
- **Предусловия:** active snapshot S1; новый merge S2 и archive/delete S3; controlled lost/duplicate/out-of-order webhooks и delayed S1 job.
- **Ключевые шаги:** потерять/продублировать события; остановить CI; возобновить; завершить late S1 после S2/S3; поставить old S1 и new S2 publishers одновременно перед publication barrier с разными generation locks, но одним Space/profile; подать stale/current fences и неверный ancestry/run; запустить HEAD/index reconciliation; проверить archive/delete и retry/DLQ.
- **Ожидаемый результат:** canonical merges не откатываются; old/new publishers сериализуются одной `(space_id,profile_id)` fence/CAS register для всех generations; stale owner/ancestry/run обновляет ноль rows, late S1 `superseded`, pointer не откатывается; S2/S3 validated published runs активируются в ancestry order; lost event обнаружен reconciliation; archive удалён из нового snapshot; DLQ виден; SHA sorting не используется.
- **Evidence:** exact HEAD/ancestry generations, run/pointer timeline, event dedupe/retry/DLQ, archived candidate denial, CI outage interval.
- **Требования/компоненты:** R11; GO event/reconciliation, CI/index writer, Retrieval. Levels: integration, fault-injection, rebuild. Gate: G2.

### A13 — Nested dry-run, controlled bulk и post-cutover rerun

- **Цель:** доказать deterministic import без writes и строгий cutover boundary; повтор без duplicates только через GO/MR после cutover.
- **Предусловия:** F-DOCS/F-MEDIA nested package, same basename/Cyrillic/links/anchors/provenance; unpublished repository, затем activated copy.
- **Ключевые шаги:** дважды dry-run same source/config; изменить config/source; проверить canonical writes отсутствуют; выполнить controlled pre-cutover package только при closed users/no published index; cutover; rerun/resume same и changed source после cutover.
- **Ожидаемый результат:** same input воспроизводит path→UUID/manifest; dry-run не создаёт branch/MR/main/index/merged cursor; losses/errors/security/PII/media видимы; pre-cutover bulk не выходит за unpublished; post-cutover changes создают MR+human decision+GO merge, без duplicates/overwrite/direct push.
- **Evidence:** manifests/hashes, canonical inventory before/after, source maps, import idempotency timeline, MR/proposal и cutover SHA chain.
- **Требования/компоненты:** R12; Ingestion/dry-run, GO import/cutover/proposals, CI/index, GitLab. Levels: unit, contract, integration, fault-injection. Gate: G2.

### A14 — Ownership modes, curated conflict/deletion и source cursors

- **Цель:** исключить overwrite/silent delete/auto-merge и ложный `merged`; сохранить typed read-only `live_operational`.
- **Предусловия:** F-OWNERSHIP; previous imported base/current curated/incoming versions; два workers и новые source versions во время outstanding.
- **Ключевые шаги:** выполнить no-op, nonconflicting и same-paragraph curated updates; source deletion; local edit source_managed; deterministic source update без human decision; два concurrent watchers; crash до MR/после MR до cursor/после merge до cursor; typed live read и timeout.
- **Ожидаемый результат:** curated правки сохранены, conflict/tombstone явны; source_managed local edit отклонён и update требует human DecisionRecord + final merge только GO; максимум один outstanding per source object; `seen/proposed/merged` продвигаются только durable evidence; live read возвращает bounded snapshot_time без wiki/MR/index/cursor и не маскирует stale как current; migrated old source не writer.
- **Evidence:** three-way diffs, MR/decision/merge chain, outstanding count, cursor transitions/recovery, live operation request/response и no-side-effect inventory.
- **Требования/компоненты:** R13; Ingestion/source adapters, GO source-sync/proposals/recovery, Identity/AuthZ. Levels: unit, contract, integration, fault-injection. Gate: G2/G3 для real connector.

### A15 — Полный export и clean restore closure

- **Цель:** проверить clone+decisions+assets manifests и mirror/metadata restore без потери канона, decisions, policies, grants или cross-Space isolation.
- **Предусловия:** F-EXPORT; accepted/rejected/cancelled records; immutable assets; export operator с правом на всю историю; clean isolated second instance; negative missing asset/note variants.
- **Ключевые шаги:** выполнить fresh authorized `export-manifest-v2` с per-batch recheck; проверить единый `git_clone_with_manifests`, explicit refs/peeled tag objects/raw hashes/manifests/closure; для accepted recorded/merge_attempted/failed/conflicted/invalid потребовать explicit outcome+attempt+recovery без merge, для rejected/cancelled verified closure, только merged — parents/trailers/raw commit; восстановить в clean instance с external merge freeze; явно map policies/groups; conservative rebuild `kb_ops`; rebuild `kb_authz`; full rebuild `kb_index`; повторить с missing/rejected asset/note/decision/batch.
- **Ожидаемый результат:** documents/tree/links/origin/valid_until/revisions/content hashes совпадают; note+tag+supersedes+canonical_json hashes сходятся; accepted-before-merge и reject/cancel не имеют merge evidence; exported assets immutable hashes совпадают, missing/rejected не имеют fabricated hash; secrets/private chats отсутствуют; любой missing input даёт `complete=assets_complete=false` либо соответствующий decisions/authorization failure, непустой `missing[]` и запрет `ExportJob.ready`; unknown merge targets остаются quarantined; другой Space/client не раскрыт.
- **Evidence:** package/closure hashes, refs/decision/assets/policy manifests, Git-derived recovery report, rebuild comparisons, role/isolation checks, sanitized restore drill.
- **Требования/компоненты:** R14; GO export/rebuild, GitLab metadata, Identity/AuthZ, CI/index, object storage, operations. Levels: contract, integration, rebuild, restore, security. Gate: G2 export, G3 full drill.

### A16 — Approved inference, profiles, egress и fallback

- **Цель:** проверить все chat/task/title/summary/extraction/embedding/reranker/OCR/vision calls через approved inventory без secrets и unplanned fallback.
- **Предусловия:** pinned Open WebUI/model connections; synthetic strict и pii_permitted configs; real approved hoster endpoint или BLOCKED; provider failure/malformed stream fixtures.
- **Ключевые шаги:** выполнить streaming sequential/parallel read/propose; malformed/unknown/oversized args; cancellation/disconnect/retry/timeout; primary provider 4xx/5xx; попытаться скрытый SDK fallback/external PII egress; revocation during stream; cold offline startup.
- **Ожидаемый результат:** только inventoried routes в selected profile; auxiliary calls подчиняются тем же правилам; malformed input не исполняется; retry только same approved route/idempotency; нет unplanned provider/model/perimeter fallback; secrets/raw payloads отсутствуют в logs/export; stream closes on revoke; missing offline route → BLOCKED readiness, не silent external processing.
- **Evidence:** provider inventory/connection IDs (не endpoints/secrets), request/run/tool traces, egress deny log, fallback attempts/results, redaction scan, offline asset/config hashes.
- **Требования/компоненты:** R15; Open WebUI model connections, bounded tools, CI/index, Ingestion, Identity/AuthZ. Levels: contract, integration, security, fault-injection, evaluation. Gate: G2.

### A17 — All-channel bypass и direct human/bot merge

- **Цель:** доказать normal managed merge-only-GO и отсутствие auto-merge на уровне capabilities и GitLab, не только tool schema, плюс обязательное обнаружение privileged Owner out-of-band bypass.
- **Предусловия:** protected `main`; human engineering, agent, connector, CI и GO proposal credentials; отдельный synthetic privileged Owner incident fixture; direct/deferred/note-attached/ordinary/native/temporary chats, automation, channels, external OpenAPI, `call_tool`.
- **Ключевые шаги:** по матрице каналов вызвать accept/reject/cancel/merge/grants/arbitrary Git/shell/SQL/Tool Creation/bulk/subtree/attachment operations; выполнить direct push/merge каждой non-GO non-privileged identity; попытаться source_managed auto-merge и CI post-merge `INDEX.md` push. Отдельно смоделировать unexpected privileged Owner history в synthetic sandbox и проверить reconciliation, incident и affected-target quarantine без history rewrite.
- **Ожидаемый результат:** разрешены только bounded read/search/propose; privileged calls denied независимо Identity/GO/GitLab; только GO managed identity может normal real merge после human decision; auto-merge и direct non-privileged human/engineering/bot merge невозможны; `INDEX.md` не создаёт bypass commit. Privileged Owner bypass не маркируется GO merge и приводит к incident/quarantine.
- **Evidence:** channel×capability×identity matrix, protected rule denial, target refs before/after, privileged-Owner unexpected-HEAD detection/quarantine record, tool/provider logs без секретов.
- **Требования/компоненты:** R06, R16; Open WebUI, GO, Identity/AuthZ, GitLab protections, CI, connectors. Levels: integration, security, browser. Gate: G1 blocker.

### A18 — Prompt injection и trusted execution context

- **Цель:** не позволить документу/source/tool output изменить actor/run/groups/tenant/policy/scopes/tools/provider или опубликовать содержимое.
- **Предусловия:** F-MALICIOUS prompt-injection documents и source responses; admin/owner requester variants; all-channel calls.
- **Ключевые шаги:** внедрить инструкции «ignore approval», self-asserted actor/groups/tenant/run/policy, requests для shell/SQL/export/merge/fallback; выполнить read/search/propose и streaming malformed args; проверить server context/credentials/main/provider inventory.
- **Ожидаемый результат:** содержимое обрабатывается как данные; trusted context не меняется; model scope только сужает effective scope; privileged capabilities отсутствуют независимо от chat role; нет payload другим users/Spaces и нет `main` writes; единственный возможный write — новый reviewed proposal.
- **Evidence:** sanitized attack IDs (без опасного payload в reports), trusted context before/after, denied tool calls, egress/main diff, authorization results.
- **Требования/компоненты:** R05, R16; Open WebUI agent gateway, Identity/AuthZ, GO, Retrieval, model connections. Levels: security, integration, evaluation. Gate: G1/G2.

### A19 — Второй клиент без code branch

- **Цель:** доказать config-only delivery и полную изоляцию клиентов для ADR-17 `shared` и `dedicated` GitLab profiles.
- **Предусловия:** один reusable core artifact; `fixture-client-b` config/repositories; отдельные DB/index/objects/secrets/client backup packages/egress; общий hardened GitLab с двумя synthetic client groups для `shared` и отдельный synthetic GitLab instance для `dedicated`.
- **Ключевые шаги:** развернуть second synthetic application instance без изменения core в обоих профилях; проверить отсутствие GitLab resources/RBAC ownership в application release; выполнить smoke/cutover/export/backup и Shared coordinated-upgrade rehearsal; попытаться использовать credentials/cache/grants/IDs первого клиента; сравнить code/SBOM/seam registry и config deltas.
- **Ожидаемый результат:** нет клиентской code branch, shared canonical repository/history, cross-client credentials или client backup packages; каждый клиент имеет independent repositories=Spaces, PostgreSQL/index/objects/secrets/backups/egress; managed credentials ограничены `(tenant_id,space_id,repository_id,capability)`; `dedicated` дополнительно имеет отдельный GitLab instance; cross-client и same-client wrong-Space access denied; backup/restore независим per Space; differences ограничены versioned config/adapters.
- **Evidence:** deployment manifests/RBAC без GitLab ownership и секретов, code/config diff, instance/profile/resource/credential inventory, cross-client denial, isolated backup/export reports, Shared upgrade coordination evidence.
- **Требования/компоненты:** R17; deployment/configuration, Open WebUI, GO, Identity, CI/index, object/backup perimeter. Levels: integration, security, restore. Gate: G3.

### A20 — Personal Notes и ordinary chats regression

- **Цель:** подтвердить, что managed KB opt-in не мигрирует и не меняет личные Notes/ordinary chats или их privacy.
- **Предусловия:** synthetic upstream users с personal Notes, private/ordinary chats и existing model connections; managed feature flag off/on; upgrade candidate после T00.
- **Ключевые шаги:** снять baseline поведение; включить managed KB; выполнить document/review/search flows; выключить/включить flag и провести upgrade rehearsal; проверить Notes/chats data, grants и per-user visibility; попытаться private Note→managed import.
- **Ожидаемый результат:** personal Notes/chats не мигрируют, не меняют канон и не наследуют managed grants; per-user privacy сохраняется; Note→managed возможен только через отдельный reviewed MR; нет side effects от feature flag.
- **Evidence:** upstream regression results, before/after sanitized schema/content counts/hashes, grant diff, feature-flag and MR traces.
- **Требования/компоненты:** R01, R17; Open WebUI upstream/feature seam, Identity/AuthZ, GO. Levels: browser, integration, upgrade regression. Gate: **G0/T00 baseline behavior на pinned upstream**, последующие feature-flag regression по scope T14 и G3 upgrade rehearsal T18; ни одна часть не выполнена этим планом.

### A21 — Exact codes, Cyrillic/Unicode, headings, long pages и patch ambiguity

- **Цель:** проверить closed contracts и точную адресацию без silent loss/ambiguity.
- **Предусловия:** F-DOCS с Cyrillic paths, NFC/NFD, repeated headings, same basename, long page и exact code strings; malformed schema vectors.
- **Ключевые шаги:** выполнить [T01 CF-01–CF-30](contracts/t01-contract-tests.yaml) consumer vectors и валидировать front-matter-v2/authz-v2/export-v2/agent-tools-v2/API/events/projection mappings; unknown/additional fields, short/mixed-case SHA, invalid UUID/time/path/range/truncation; ImportManifest validated+errors/blocked+empty errors и mismatched import mode/proposal linkage; `truncated=false` с non-none reason/cursor и `truncated=true` с reason=none/null cursor; evidence `end_line<start_line`; direct read repeated heading occurrence; exact/semantic search exact codes; valid agent и forbidden whole/ambiguous anchored patches; rename/swapped stable links; `/`, `/pricing`, `/approval-policy.yaml` absolute↔relative roundtrips.
- **Ожидаемый результат:** valid inputs проходят со stable IDs/citations и explicit canonical↔projection mapping; malformed/unknown/inconsistent inputs получают declared machine errors и zero writes; paths нормализованы по правилам и traversal/duplicates отклонены; zero/multiple matches → `PATCH_AMBIGUOUS` без canonical write; long read имеет explicit truncation с согласованными reason/cursor; `access`, links и valid_until не влияют на ACL; unavailable real checks остаются BLOCKED.
- **Evidence:** contract vectors/results, normalized paths, patch match counts, read/search revisions и no-write proof.
- **Требования/компоненты:** R02, R03, R04; contracts, GO validation/read/patch, Retrieval, Open WebUI. Levels: unit, contract, integration. Gate: G2.

### A22 — Open MR/evidence/attachments/unverified media не утекают

- **Цель:** исключить неpublished или непроверенное содержимое из index/чужих answers и независимо авторизовать review payload.
- **Предусловия:** open/rejected MR с rationale/evidence/attachments; F-MEDIA critical/handwritten/substantive; authorized и unauthorized reviewers/readers.
- **Ключевые шаги:** построить published index; search по уникальным маркерам open/rejected/evidence/media; запросить review как authorized approver и как outsider; попытаться получить attachments по ссылке/ID и через model tool; построить answer по automatic description.
- **Ожидаемый результат:** pending/rejected/evidence/attachments отсутствуют в published projections; `inbox/templates/service` исключены; critical/untranscribed media не индексируется; decorative исключены; substantive auto description помечено и ссылается на original; review/evidence/files доступны только после отдельной свежей авторизации.
- **Evidence:** eligible/excluded inventory, query/answer negatives, review authorization matrix, attachment/media admission and citation results.
- **Требования/компоненты:** R05, R07, R11; Identity/AuthZ, review UI, CI/index, Retrieval, Ingestion/media. Levels: integration, browser, security, evaluation. Gate: G2.

### A23 — Malicious import и preview security

- **Цель:** отклонить XSS/executable/traversal/symlink/secrets/oversized/decompression inputs до corpus и preview.
- **Предусловия:** F-MALICIOUS; fail-closed bounded test config; dry-run staging и WYSIWYG/review preview.
- **Ключевые шаги:** подать каждый malicious fixture по отдельности и вложенным архивом; попытаться обойти checks через Unicode/collision/second extraction route; открыть preview; проверить staging escape, canonical writes, logs/evidence/provider payload.
- **Ожидаемый результат:** `SECURITY_REJECTED`/подходящий validation error до canonical writes; нет executable preview/XSS, path escape или secret disclosure; unsupported/oversize не считается success; PII/secrets canaries не попадают в logs/export/model; blocked files не индексируются.
- **Evidence:** malicious vector→error map, canonical/staging boundary checks, sanitized preview security result, log/export redaction scan.
- **Требования/компоненты:** R12, R16; Ingestion intake/extraction, Open WebUI preview/editor, GO, CI/index. Levels: unit, contract, integration, browser, security. Gate: G2.

### A24 — LDAP/OIDC login, empty password и JIT без GitLab user

- **Цель:** проверить pinned upstream authentication, stable IDs и обязательные negative controls.
- **Предусловия:** synthetic AD/OpenLDAP/OIDC profiles по поддерживаемому scope; read-only encrypted bind/client; nested groups; empty/invalid credential cases.
- **Ключевые шаги:** login valid users в каждом выбранном provider profile; empty LDAP password (CVE-2026-44551 regression), invalid credentials; resolve objectGUID/entryUUID/issuer-scoped sub и nested groups; JIT first login; inspect GitLab business users и review queue.
- **Ожидаемый результат:** valid login нормализует stable identity/groups; empty/invalid credentials отклонены без authentication bypass; read-only LDAPS/StartTLS работает в выбранном profile; JIT создаёт только upstream identity/managed grants, не GitLab user; queue назначена группе; отсутствие stable attribute → BLOCKED, не email fallback.
- **Evidence:** pinned versions/seams, auth result matrix, stable attribute mapping, nested membership snapshot, GitLab user absence proof, sanitized logs без passwords.
- **Требования/компоненты:** R05, R16; upstream Open WebUI auth, Identity/AuthZ, IdP, GO approval policy. Levels: contract, integration, security. Gate: G0 capability/G1.

### A25 — Revocation SLO ≤30 минут и sensitive recheck

- **Цель:** измерить полный путь group removal → denied private access/search/tools/history/export и ближайший merge/export/private-page recheck.
- **Предусловия:** `leaver-user` с active sessions, live subscription, open MR ready for merge и multi-batch export; background refresh configured ≤15 минут; monotonic timestamps.
- **Ключевые шаги:** зафиксировать `T0` удаления из AD-группы; попытаться merge/export/private payload сразу и при следующем sensitive recheck; наблюдать periodic refresh; после revocation повторить tree/search/tools/history/files/export/stream; проверить provider outage отдельно.
- **Ожидаемый результат:** merge/export/private payload denied при ближайшем recheck с нулём `main` writes/no export payload; все новые private payloads прекращаются не позднее `T0+30m`; group refresh интервал не превышает 15 минут; subscriptions закрыты, cursors/contexts invalid; provider outage не даёт бессрочный cached allow; уже доставленный текст не объявляется reversible.
- **Evidence:** T0/recheck/deny/subscription timestamps, measured propagation duration, per-channel result matrix, `main`/export unchanged proof.
- **Требования/компоненты:** R05, R11; Identity/AuthZ, IdP, GO, Retrieval, Open WebUI, export. Levels: integration, security, fault-injection. Gate: G2; fixed SLO, не OWNER_TBD.

### A26 — Rename login/email и mover

- **Цель:** сохранить stable attribution/history и обновить Space grants/review queue по группам.
- **Предусловия:** synthetic user с ProposalRecords/Decisions/history; переход `mover-user` между access/approver groups; login/email rename.
- **Ключевые шаги:** переименовать login/email без изменения stable ID; прочитать старые proposals/decisions/history; изменить группы; refresh/recheck; проверить старую/новую group review queue с overlapping `/` и `/pricing` approver rules, exact base/proposal и bounded pagination; попытаться queue/read protected object другой группы/Space; выполнить новое предложение и решение eligible approver.
- **Ожидаемый результат:** stable ID и связи не перепривязываются по строковому login; исторические principals неизменны; mover получает новые scopes/queue и теряет старые по policy; очередь использует только longest-prefix `/pricing` rule без union с parent `/`, показывает exact reviewed SHA и не требует GitLab user; protected object anti-enumerated; новые записи используют тот же stable ID.
- **Evidence:** before/after stable identity map, immutable Proposal/Decision hashes, grant/queue diff, access denial/allow results.
- **Требования/компоненты:** R05; Identity/AuthZ, IdP, Open WebUI, GO/review. Levels: integration, browser, security. Gate: G2.

### A27 — Canonical DecisionRecord note+tag, corruption и supersedes

- **Цель:** проверить одинаковый canonical JSON/hash для accept/reject/cancel в MR note и protected annotated tag на exact proposal; invalid/recovery/export semantics.
- **Предусловия:** F-PROPOSALS с тремя actions; JCS/hash contract; real GitLab note/tag capability или BLOCKED; corrupted note/tag/hash/target/note-ID vectors.
- **Ключевые шаги:** создать Decisions и сравнить bytes/record/canonical JSON/body hashes/tag peeled target/note ID; для accept проверить merge linkage; удалить/изменить каждое representation в sandbox без ослабления protections при недоказанном external outcome; попытаться второй MR и снять barrier через invalid/supersedes; исправить через новый UUID со `supersedes_decision_id`; выполнить export-v2 accepted-before-merge/rejected/cancelled.
- **Ожидаемый результат:** note и tag содержат одинаковый полный JSON с `record_sha256`; tag — `kb-decisions/<uuid>` на `proposal_sha`; missing/mismatch/wrong target/hash/linkage → `DECISION_INVALID`, не merged; при unknown external outcome unresolved link+quarantine сохраняются и second MR denied независимо от invalid/supersedes; старый JSON не редактируется; decisions manifest содержит note+tag+explicit outcome+attempt+recovery, merge только для proven merged и verified reject/cancel closure.
- **Evidence:** canonical bytes/hashes, note IDs/tag object+target, protection denial, quarantine/recovery records, supersedes chain, export closure.
- **Требования/компоненты:** R08, R09, R14; GO decision/recovery/export, GitLab, review UI. Levels: unit, contract, integration, fault-injection, restore. Gate: G1/G3.

### A28 — Crash после merge до projection и полная crash matrix

- **Цель:** восстановить Git-derived outcome без duplicate и удерживать per-target `recovery_required` до conclusive reconciliation.
- **Предусловия:** accepted DecisionRecord note+tag; durable `merge_attempted`+barrier; controlled GitLab merge с response lost и GO crash после принятия merge до DB projection; второй MR на том же target.
- **Ключевые шаги:** выполнить все строки раздела 8 и [T01-CF-18/21/23](contracts/t01-contract-tests.yaml); для основного случая найти merge по decision/proposal; проверить parents/trailers/note/tag/actor; записать Git-derived `merged`; попытаться второй merge до/после reconciliation; повторить original decision; отдельно получить conclusive failed и guarded same-decision/new-attempt retry, invalid+unknown и terminal conflicted.
- **Ожидаемый результат:** существующий commit обнаружен и подтверждён, второго merge нет; projection восстановлена из Git; index request/reconciliation инициирован отдельно; второй MR blocked до target-wide доказанного merged/no-merge для каждого accept и request completion; failed retry возможен только после completed+no-merge evidence/fresh preconditions с атомарно восстановленным barrier, conflicted/invalid не retryable; identical replay создаёт ноль attempts; до/после проверяется tuple `(decision.state,attempt.state,target_barrier,target_barrier_decisions)`.
- **Evidence:** crash/inflight timeline, exact merge commit/parents/trailers/note/tag, barrier/fencing state, merge count, index request, replay equivalence.
- **Требования/компоненты:** R09, R10, R18; GO merge/recovery/reconciliation, `kb_ops`, GitLab, CI/index. Levels: unit, integration, fault-injection, rebuild. Gate: G1 blocker/G3 rebuild.

### A29 — Target race, fencing и losing operation

- **Цель:** закрыть TOCTOU между precondition check и merge; stale owner не должен менять result/barrier после lock loss.
- **Предусловия:** два GO owners/clients и PA/PB; controllable pause после HEAD check и перед merge/after barrier; fencing tokens.
- **Ключевые шаги:** изменить HEAD в паузе через другой serialized GO path; передать lock новому owner с inflight old request; попытаться old-owner projection update/barrier clear и новый merge; завершить late response; reconcile.
- **Ожидаемый результат:** непосредственный pre-merge `target HEAD == base_sha` recheck предотвращает второй apply; loser получает conflict и ноль новых `main` writes; stale fencing update затрагивает ноль rows и не снимает barrier; новый owner блокирует все target merges до target-wide conclusive reconciliation; unknown остаётся quarantined.
- **Evidence:** pause/event timeline, old/new owner/fencing tokens, affected-row results, Git ancestry/merge count, quarantine/reconciliation findings.
- **Требования/компоненты:** R10, R16; GO lock/fencing/merge/recovery, `kb_ops`, GitLab. Levels: integration, security, fault-injection. Gate: G1 blocker.

### A30 — Self-approval author/requester/version editor

- **Цель:** отклонить все три совпадения и редактора собственной версии независимо от UI/CODEOWNERS.
- **Предусловия:** proposals, где approver = original author; = requester; = version editor; совпадение нескольких ролей; прежний approver редактирует новую версию; valid independent approver control.
- **Ключевые шаги:** попытаться accept каждой ролью через UI/API/agent/deferred/OpenAPI; изменить группы/path rule как privileged fixture, не actor payload; проверить eligible independent approver и engineering CODEOWNERS-only review.
- **Ожидаемый результат:** каждое self-approval → `APPROVER_CONFLICT`/forbidden с нулём `main` writes; version editor не утверждает собственную версию даже при прежнем approval; CODEOWNERS не даёт business rights; independent fresh-group/path approver проходит.
- **Evidence:** principals×approver matrix, denial across channels, unchanged target, valid control merge и separate business/engineering role map.
- **Требования/компоненты:** R05, R08; Identity/AuthZ, GO decision/merge, review UI, approval policy, GitLab. Levels: contract, integration, browser, security. Gate: G1.

### A31 — Cutover HEAD drift и порядок activation

- **Цель:** остановить activation при drift и доказать freeze→exact HEAD→tag/protection→inactive preflight→published pointer→Space/user activation.
- **Предусловия:** dry-run и human sign-off/CutoverRecord на exact SHA; unpublished main без users/published index; controlled pre-protection bulk fixture; drift variants после sign-off/freeze; crash/replay points.
- **Ключевые шаги:** запустить cutover; проверить write freeze первым; изменить HEAD после sign-off и отдельно после freeze; попытаться activation/preflight retrieval/user access; после successful preflight создать отдельный `IndexRequested(preflight=false)` и published run/descriptor; сравнить request/run/snapshot IDs, SHA/closure/policy/hashes и повторную full validation; попытаться активировать preflight либо изменить SHA; повторить same Space+SHA при unchanged frozen HEAD; после успешного cutover попытаться direct push/human/bot merge.
- **Ожидаемый результат:** drift останавливает process без published pointer/user activation; требуется новый CutoverRecord/sign-off/preflight; replay допустим только same Space+SHA при сохранённом freeze/HEAD; preflight `serving_allowed=false`, immutable и никогда active; published non-preflight имеет новые request/run/snapshot IDs, но тот же `cutover_sha=main_sha=snapshot_sha`, closure, approval policy revision и exact/semantic hashes; единственный writer публикует pointer через per-Space/profile CAS до GO Space activation; direct push/merge после cutover denied; исправления — reviewed/revert MR, не history rewrite/bulk bypass.
- **Evidence:** sign-off/CutoverRecord SHA, HEAD drift timeline, protections/tag refs, preflight non-serving checks, pointer/activation ordering, direct-write denials.
- **Требования/компоненты:** R05, R11, R12; GO cutover, GitLab protections, CI/index, Identity/AuthZ, Ingestion. Levels: integration, security, fault-injection, browser. Gate: G2 blocker.

### A32 — Строгая cross-Space isolation

- **Цель:** не раскрыть другой Space через tree/titles/snippets/chunks/files/history/decisions/export/tools, clone/mirror/late jobs.
- **Предусловия:** `fixture-sales` и `fixture-sales-pricing` с разными ACL; users только одного Space; shared test runner и two late index jobs; export/mirror operators с ограниченными правами.
- **Ключевые шаги:** подставить чужие document/proposal/decision IDs и cursor; search/read/history/files/decisions/export/tools; изменить path/front matter; завершить late jobs в обратном порядке; создать clone/mirror/manifests каждого Space; попытаться получить full export без history permission; выполнить [T01-CF-22/27](contracts/t01-contract-tests.yaml) с borrowed policy/cutover/grant, document/snapshot/pointer repository-target-SHA mismatch, cross-Space outstanding proposal/error и swapped resolved-link UUID.
- **Ожидаемый результат:** только effective Space доступен; anti-enumeration сохраняется; folders/path approver scopes не создают page ACL; `access` не меняет grants; full-perimeter composite FK/transaction rejects corrupted associations; pointers/locks/generations независимы; clone/mirror содержит только собственные refs/history/assets; filtered export не выдаётся за supported full export.
- **Evidence:** cross-Space IDOR matrix, ref/repository inventories, pointer timelines, export closure/perimeter, anti-enumeration responses.
- **Требования/компоненты:** R02, R05, R11, R14; Identity/AuthZ, GO, CI/index, GitLab, export/backup. Levels: contract, integration, security, restore. Gate: G2/G3.

### A33 — Schema write denial и migration ownership

- **Цель:** доказать single writer/migration owner для upstream/managed grants/`kb_authz`/`kb_ops`/`kb_index` и read-only retrieval.
- **Предусловия:** isolated PostgreSQL с approved logical roles; component credentials; owner migration procedures из baseline; cross-schema fixture rows/contracts.
- **Ключевые шаги:** каждым component попытаться INSERT/UPDATE/DELETE/DDL в чужих zones и managed upstream grants вне supported seam; retrieval mutation; cross-schema FK/write; запустить/повторить owner migrations по supported procedure и non-owner migration; проверить rebuild semantics и audit details.
- **Ожидаемый результат:** только upstream components пишут upstream; только Identity пишет managed grants через seam и `kb_authz`; только GO — `kb_ops`; только CI/index — `kb_index`/pointer; retrieval read-only; cross-schema writes/FK отсутствуют/отклонены DB roles; non-owner migration denied; no arbitrary upstream SQL; secrets/raw content отсутствуют в audit.
- **Evidence:** component×schema×operation denial matrix, DB role/migration inventory, sanitized DB errors, FK/catalog assertions, rebuild ownership report.
- **Требования/компоненты:** R05, R11, R17, R18; PostgreSQL, Identity/AuthZ, GO, CI/index, Retrieval, upstream Open WebUI. Levels: contract, integration, security, rebuild. Gate: G1/G3.

### A34 — Squash/rebase/FF, parent/trailer/note/tag mismatch

- **Цель:** признавать merged только реальный merge commit с exact parentage и полной Decision linkage.
- **Предусловия:** real GitLab capability matrix; accepted DecisionRecord; variants squash, automatic rebase, fast-forward, swapped/wrong/missing parents и каждого trailer/note/tag/hash/Approved-by.
- **Ключевые шаги:** запросить каждый запрещённый merge mode; подменить/повредить merge metadata в controlled sandbox при недоказанном external outcome; выполнить reconciliation и replay; попытаться снять barrier по HTTP success/DB status/invalid/supersedes и запустить второй MR.
- **Ожидаемый результат:** squash/rebase/FF rejected в managed path; first parent обязан быть `base_sha`, second — `proposal_sha`; `Decision-ID`, `Decision-Note-ID`, `Decision-Hash`, `Approved-by` и note/tag/target/actor совпадают; любой mismatch → не merged; invalid+unknown сохраняет unresolved link, quarantine и second-MR denial, terminal/supersedes сам по себе barrier не очищает; replay не создаёт второй merge/attempt.
- **Evidence:** merge modes/denials, raw parent/trailer hashes (sanitized refs), note/tag comparison, reconciliation outcome и barrier state.
- **Требования/компоненты:** R08, R09, R10; GitLab, GO decision/merge/reconciliation, `kb_ops`. Levels: unit, contract, integration, fault-injection, security. Gate: G0 capability/G1 blocker.

### A35 — Preflight non-serving и incremental dependency closure

- **Цель:** запретить retrieval из preflight/partial index и publication incremental без full equivalence.
- **Предусловия:** exact cutover preflight; active published baseline; linked docs/shared metadata/attachment/policy inputs; full и incremental runs на одном `main_sha`; late generation/profile runs.
- **Ключевые шаги:** вызвать search/get active на preflight; попытаться активировать preflight и published с другим SHA; проверить separate same-SHA published pair; построить incremental с изменённым linked document, attachment, media admission и approval policy revision; удалить часть transitive closure или independent full-run evidence; попытаться pointer publish; расширить closure/full rebuild; одновременно запустить old/new generation/profile publishers со stale/current fences.
- **Ожидаемый результат:** preflight `is_preflight=true`, `serving_allowed=false`, retrieval `INDEX_NOT_READY`, никогда active; separate published non-preflight имеет новые request/run/snapshot IDs, тот же SHA/closure/policy/hashes и повторную full validation; active требует ready exact+semantic non-null hashes; incomplete/non_equivalent/missing independent proof → `DEPENDENCY_CLOSURE_MISMATCH`, pointer unchanged; после expansion/independently proven equivalence run может быть активирован single writer; concurrent old/new использует одну Space/profile fence/CAS, stale write ноль rows, late run `superseded`.
- **Evidence:** snapshot/purpose/state, serving denials, full/incremental dependency hashes/missing inputs, exact+semantic readiness, pointer/generation/profile timeline.
- **Требования/компоненты:** R04, R11, R12; CI/index planner/validator/pointer, GO cutover/events, Retrieval, Ingestion attachments. Levels: unit, contract, integration, fault-injection, rebuild. Gate: G2 blocker.

### A36 — Policy bundle/revision mismatch и revocation между review и merge/export

- **Цель:** остановить sensitive operation при несогласованном bundle или утрате group/path role; ноль `main` writes и ноль export payload.
- **Предусловия:** reviewed proposal и multi-batch export; F-POLICIES mixed IDs/revisions/partial bundle; approver/export actor с removable group/path grants.
- **Ключевые шаги:** после review подменить per-Space access/approval revision, `policy_bundle_id`, group snapshot или actor/Space revocation epoch; попытаться merge/export; отдельно удалить approver/external group/longest-prefix path role между review и apply и между export batches; попытаться использовать старый AuthzContext/cursor и borrowed binding другого Space.
- **Ожидаемый результат:** `POLICY_REVISION_MISMATCH`, `APPROVER_CONFLICT`, `AUTHZ_CONTEXT_STALE`/`GROUP_SNAPSHOT_STALE` либо forbidden по фазе; нет decision apply/`main` writes или export payload; partial/borrowed bundle не активируется; long operation делает fresh recheck именно нужного per-Space binding перед каждым payload/batch; предыдущий полностью согласованный policy сохраняется без расширения прав или union с parent prefix.
- **Evidence:** review→operation timeline, bundle/revision hashes, group snapshot/revocation epoch, denied merge/export results, main/ref и export-empty proof.
- **Требования/компоненты:** R05, R08, R10, R14; Identity/AuthZ, GO decision/merge/export, GitLab, Open WebUI. Levels: contract, integration, security, fault-injection. Gate: G1/G2/G3.

## 8. Детерминированная crash/fault матрица

Нормативная crash-фазовая таблица находится только в [integration.md §7](integration.md#7-crash-recovery-и-timeout-reconciliation-spec-71-73). Здесь — **test actions и assertions**, а не вторая нормативная таблица; component-local invariants — [architecture.md §7.7](architecture.md#77-crash-recovery--локальные-component-invariants) и [GO §7.7](components/git-orchestrator.md#77-crash-recovery--локальные-go-invariants), operational actions — [operations.md §7.1](operations.md#71-target-recoveryquarantine-runbook).

Каждая строка выполняется сначала как unit state test, затем как controlled real sandbox test после доступа. Обязательные общие assertions: не более одного conclusive merge для `(repository_id,target_branch,proposal_sha)` и одного `decision_id`; нет optimistic `merged`; stale owner не снимает barrier; соседний target продолжает контролируемую работу, затронутый target блокирован полностью; unknown/invalid без доказанного outcome не очищается rebuild/restart/TTL/supersedes. До/после каждого recovery и guarded retry сохраняется tuple `(decision.state,attempt.state,target_barrier,target_barrier_decisions)` и request/no-merge/reconciliation evidence; identical replay создаёт ноль attempts. Соответствующие machine vectors — [T01-CF-18/21/23](contracts/t01-contract-tests.yaml).

| Точка crash / сбой | Начальное доказанное состояние | Внедрение и ключевые проверки | Обязательный результат восстановления | Запрещённый результат |
| --- | --- | --- | --- | --- |
| До записи DecisionRecord note/tag | Merge call ещё не допускался. Полного note+tag нет; если осталось одно representation, decision partial/invalid | Crash до note, между note и tag, после tag до complete verification. Повторить human apply с тем же idempotency context после fresh checks; попытаться merge по partial record | `main` unchanged; canonical record либо создаётся заново корректно по idempotency protocol, либо partial/mismatch переводится в invalid recovery. Исправление — новый UUID со supersedes, не edit старого JSON | Merge по одному representation; признание partial accepted; редактирование canonical JSON |
| После durable DecisionRecord, до merge | Note+tag существуют на `proposal_sha`; merge commit/request completion/no-merge не доказаны; DB row может отсутствовать | Crash после record до DB transaction и до external call. Новый owner сначала сканирует unresolved accepts target; попытаться другой merge | Перед любым новым merge восстановлен `recovery_required`. Найти существующий merge по decision/proposal. Только после `request_state=completed + no_merge_proven=true` решение может стать `failed`; recovery coordinator затем выполняет guarded retry с новым `attempt_id`, **тем же** `decision_id`, fresh preconditions и атомарно восстановленным barrier; identical replay создаёт ноль attempts | Новый decision ID для сокрытия retry; другой merge target до reconciliation; failed/quarantine clear по отсутствию DB row |
| После DB `merge_attempted`+barrier, до external call | `recovery_required` durable; call ещё не отправлен по controlled evidence | Crash сразу после commit barrier; lock handover; попытаться снять barrier новым owner | Target остаётся blocked. Controlled no-call/completion и Git no-merge evidence фиксируются в attempt/reconciliation; только conclusive failed допускает same-decision/new-attempt retry после fresh preconditions и target-wide clear, с barrier восстановленным до call | Очистка barrier из-за lock expiry; смена decision/idempotency key; retry из unknown или terminal conflicted/invalid; немедленный новый merge |
| Во время GitLab merge call / timeout | Request мог быть accepted; `merge_attempted` и barrier уже durable; outcome unknown | Задержать response, потерять response после accept, timeout до/после merge, lock loss и late response. Запустить target-wide MR/main/audit reconciliation | Все новые merges target blocked. `merged` только после commit ancestry + first/second parents + four trailers + note/tag/hash/actor. Conclusive failed после completed+no-merge допускает guarded same-decision retry; недоказуемый outcome остаётся merge_attempted+quarantined | Blind retry; `failed` по timeout; merged по HTTP 2xx без Git proof; auto-clear по TTL; merge другого MR после handover |
| `invalid` + unknown external outcome | Note/tag/trailer/parent mismatch установлен, но merge/no-merge не доказан | Повредить integrity evidence, создать supersedes/new UUID, попытаться второй MR и очистить terminal invalid/barrier | Decision `invalid`, terminal и `retryable=false`; target barrier decision link остаётся unresolved/unknown, quarantine и second-MR denial сохраняются до target-wide доказанного merged/no-merge для каждого accept | Очистка по terminal label/supersedes; нормальный reject/cancel closure по mismatched record; guarded retry из invalid |
| После принятия merge GitLab, до DB projection | Merge commit и note+tag — канон; projection отсутствует/устарела | Crash GO после GitLab success до response/projection; restart новым owner; replay исходного decision | Найти и проверить commit, записать Git-derived `merged`/`verified_merged` без второго external call; barrier завершить только после target-wide проверки; инициировать/reconcile index отдельно | Повторный merge call; failed из-за отсутствующей row; ожидание index для признания canonical merge |
| Полная потеря БД / всех projections | Пустая БД не доказывает ни success, ни отсутствие call; GitLab/source registry остаются каноном; старые AuthzContexts invalid | Удалить isolated DB projections; попытаться merge/read privileged payload сразу; выполнить rebuild `kb_ops`, `kb_authz`, `kb_index` и restore reconciliation | Внешний global bootstrap merge freeze и privileged/payload closure первыми. `kb_ops`: conservative barriers и Git-derived target reconciliation. `kb_authz`: fresh IdP+Git policy contexts/grants. `kb_index`: full validated rebuild/new pointer. Targets открываются по одному после conclusive evidence | Merges из-за пустой БД; доверие transient projection/backup status; stale index serving; очистка unknown recovery |

Дополнительные обязательные fault vectors:

- request accepted + response lost, затем late duplicate response;
- lock expiry без crash, owner fencing race и stale update затрагивающий ноль rows;
- note/tag/trailer/parent corruption во время reconciliation;
- GitLab unavailable до нового call и во время reconciliation;
- CI outage, lost/duplicate/out-of-order webhook, late index job, partial exact/semantic projection и simultaneous old/new Space/profile publication со stale fence;
- IdP/provider/object-storage outage во время sensitive recheck/export batch/index rebuild; per-Space policy/group/epoch substitution и missing approval revision;
- crash source sync до MR, после MR до `proposed`, после verified merge до `merged`; live_operational попытка получить document/proposal/index/cursor effect;
- cutover crash между preflight и separate published request/run/snapshot, между pointer CAS и Space activation; preflight никогда не становится active;
- export accepted-before-merge, missing/rejected asset/decision/batch и incomplete manifest не получает ready/complete claim.

## 9. Сквозная трассировка R01–R18, I01–I14, T01 и tasks

Дублирующие R/I navigation indexes здесь не поддерживаются. Единственный согласованный source — [traceability.md](traceability.md):

- [R01–R18 matrix](traceability.md#2-матрица-r01r18) — нормативные R→A связи spec, включая R04 без A02, R05 с A31, R11 с A22 и R18 без A34;
- [I01–I14 matrix](traceability.md#3-матрица-i01i14) — полный invariant coverage без независимого сокращённого списка;
- [A01–A36 coverage](traceability.md#4-acceptance-by-acceptance-coverage-a01a36) — прямые R/I/components/contracts/T/E связи каждого сценария;
- [T01 CF-01–CF-30 и v2 coverage](traceability.md#41-t01-cf-01cf-30-и-v2-contract-coverage) — semantic/consumer vectors и [projection mappings](contracts/projection-mapping.md);
- [T00–T20/E00–E08 coverage](traceability.md#5-полное-t00t20-и-e00e08-coverage) — прямые task acceptance links; live statuses только в [tasks.md](tasks.md).

Полный сценарный каталог раздела 7 и fault matrix раздела 8 сохраняются без сокращений. Эти ссылки — навигация DESIGN, не executed test matrix и не G0 PASS.

## 10. Definition of Done для будущего выполнения плана

Сценарий может быть отмечен VERIFIED только при наличии фактического результата на требуемом уровне, environment/commands, exact versions и sanitized evidence. DONE дополнительно требует связанные критерии задачи, code/design review, обновлённые ADR/contracts/operations и указанный upgrade/rollback impact. BLOCKED реальных интеграций остаётся явным; waiver не создаётся молчаливо.

Для release candidate обязательны: deterministic merge/push/ACL/schema/cutover/export/recovery gates; воспроизводимый corpus SHA и fixture/dataset versions; отсутствие secrets/private payloads в artifacts; зарегистрированные owner thresholds там, где они требуются; явный owner gate review. Этот документ сам по себе не является таким review или evidence.
