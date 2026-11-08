---
name: Corporate KB operations design
type: deployment-and-operations-runbooks
status: design_not_executed
created: '2026-11-06'
updated: '2026-11-08'
specification_version: '1.3'
audience: Команда архитектуры, эксплуатации, security, QA и владельцы клиентского контура
---

# Corporate KB — operations для G0 и последующего планирования

## 1. Статус и правила применения

**Документ имеет статус DESIGN NOT EXECUTED.** Он описывает целевую эксплуатационную модель и будущие runbooks, но не подтверждает deployment, startup, migration, cutover, backup, restore, upgrade, outage handling, operational owner acceptance или production readiness. Отдельный G0 design approval получен и не заменяет эти rehearsals.

Pinned baseline записан в [baseline.md](baseline.md) (**DONE — G0 APPROVED**) с synthetic runtime evidence в [evidence/t00](evidence/t00/README.md). Тем не менее:

- production commands, DDL/migrations, container manifests, GitLab API calls, backup/restore scripts и destructive actions не выполняются вне sandbox и не утверждены для production;
- TipTap adapter selected и owner-approved (G0-D8), но canonical adapter/browser gate не завершены; object-store layout, models/dimensions, connector и фактический repository perimeter — owner decisions;
- не включать production user access, corpus load, external egress или платные вызовы;
- любые шаги ниже — **логические операции и control points**, а не готовые команды. Исполняемые процедуры выводятся из pinned baseline, проходят sandbox rehearsal и отдельное owner authorization.

Обязательные controls, подтверждённые T00 evidence как необходимые (не optional):

- **External migrator profile** ([evidence/t00/openwebui-toolchain.md](evidence/t00/openwebui-toolchain.md)): runtime workers только с `ENABLE_DB_MIGRATIONS=False` и non-DDL role; единственный migrator job выполняет `alembic upgrade head`, сверяет expected head `e42c8f710a36` до включения traffic; pre/post data-copy checks и rollback assessment обязательны; migration errors санитизируются (duplicate-email error содержит emails).
- **GitLab CE normal managed merge-only-GO profile** ([evidence/t00/gitlab-capabilities.md](evidence/t00/gitlab-capabilities.md)): `push_access_level=0`, `merge_access_level=40`, GO — единственный managed Maintainer, unprotect — Administrator-level, protected decision tags `kb-decisions/*` создаёт только GO; per-user protected branch grants в CE отсутствуют и не используются. Для всех non-privileged business/engineering/bot/connector/CI/source identities единственный normal post-cutover final apply — GO/MR/canonical human DecisionRecord/GO merge; routine/self-service admin break-glass product capability отсутствует.
- **Privileged admin governance (G0-D3 APPROVED):** GitLab instance/project Owners могут обойти GO вне managed path. Такой bypass — out-of-band security/integrity incident: out-of-band reconciliation обнаруживает unexpected HEAD/merge, немедленно устанавливает affected-target `recovery_required`/quarantine и managed-write freeze, сохраняет audit evidence и запускает explicit runbook §7.5. Абсолютный merge-only-GO для privileged admins не заявляется ([g0-review.md](g0-review.md)).
- **Cutover settle proof:** активация пользователей/merge только после negative push proof (GitLab protection propagation race наблюдался в sandbox).
- **Webhooks:** local-URL relaxation — sandbox-only; production требует reachable allowlisted endpoints и secret validation.

Нормативный порядок: [Architecture Spine](architecture-spine.md) AD-1–AD-16 → [spec.md](spec.md) R01–R18/I01–I14 → [ADR](adr/README.md) → [architecture.md](architecture.md), [integration.md](integration.md), [database.md](database.md), [components](components/), [contracts](contracts/README.md). Canonical↔projection mappings и DESIGN_NOT_EXECUTED consumer vectors: [projection-mapping.md](contracts/projection-mapping.md), [t01-contract-tests.yaml](contracts/t01-contract-tests.yaml). Контентный контур: [content-standard.md](content-standard.md). Сопутствующие проверки: [test-plan.md](test-plan.md), полный каталог A01–A36. Phase/evidence rules: [AGENTS.md](../../AGENTS.md) и [tasks.md](tasks.md).

Обозначения:

- **REQUIREMENT** — обязательный инвариант или SLO из spec/AD/ADR.
- **DESIGN** — предлагаемая operational последовательность.
- **UNKNOWN** — не выбранная baseline/capability/tooling/config.
- **OWNER_TBD** — численный threshold, retention, RPO/RTO, budget или window, который должен назначить владелец.
- **DEFERRED** — требует новых требований/ADR/owner decision; нельзя выполнять как обычную операцию.
- **BLOCKED** — реальная проверка или rollout недоступны до доступа/capability; mock не считается operational PASS.

## 2. Выделенная deployment topology

### 2.1. Один reusable core — отдельный контур каждого клиента

Платформа поддерживает **одну линию reusable core code**, а каждый клиент получает отдельный isolated deployment с собственными:

- Open WebUI + GO + Identity/AuthZ + source/ingestion components;
- GitLab group/projects: **ровно один repository = один Space**, отдельный repository для каждого Space;
- Open WebUI upstream zone, PostgreSQL instance, `kb_authz`, `kb_ops`, `kb_index`, CI workers и retrieval projections;
- immutable object storage для attachments/source packages;
- configuration, secret references, model connections и scoped credentials;
- backups, Git mirrors, MR metadata exports, manifests и restore environments;
- network perimeter и egress allowlist.

Каноном остаются GitLab/MR/protected tags/immutable objects и согласованные policies. PostgreSQL, CI/index, caches и vector backend не становятся общим canonical store. Между клиентами запрещены shared `kb_*` instance, mixed mirror/export/backup, общий grant context и скрытый shared credential.

### 2.2. Логические компоненты и права

| Компонент | Развёртывание и данные | Разрешено | Запрещено |
| --- | --- | --- | --- |
| Open WebUI pinned fork | Reusable core + small versioned feature seam; personal Notes/ordinary chats отдельно от managed KB | UI, sessions, managed upstream identities/grants, model connections, bounded calls | GitLab merge, `kb_*` writes, неограниченные tools, скрытый provider fallback |
| GO proposal/read | Отдельная service capability и credential | Exact canonical reads, branches, MRs, ProposalRecords, DecisionRecord notes/tags, drafts | Merge permission для proposal identity; direct `kb_authz`/`kb_index` writes |
| GO merge/recovery | Отдельная merge service identity; durable per-target barriers | Human-decision apply, merge-only-GO, fencing/reconciliation, `kb_ops` | Agent/connector/CI use; direct human merge; direct `kb_authz`/`kb_index` writes |
| Identity/AuthZ | Own managed schema и supported upstream grant seam | LDAP/OIDC sync, AuthzContext, policy/grant projections, revocation | Arbitrary upstream SQL, `kb_ops`/`kb_index` writes, email/login fallback |
| CI/index workers | Separate main reader, object reader и `kb_index` writer/pointer publisher | Exact-SHA reads, full/incremental build, validation, single pointer | Merge, canonical push, grants, preflight serving |
| Retrieval adapter | Read-only `kb_index` consumer | Scope/filter/candidate validation/fresh payload authorization | Index mutation, grant ownership, stale candidate fallback |
| Ingestion/source adapters | Selected connector per binding; source+proposal credentials | Dry-run, provenance, media/PII/security admission, proposal creation | Merge, index, grants, automatic curated overwrite/delete |
| Object storage | Per-client immutable object/version/hash layout | Versioned attachments/source packages и verified reads | Mutable URL как identity, secrets/authorization hints в object path |
| PostgreSQL | Dedicated per client; owner roles/migrations per schema | Operational/rebuildable projections и authorization metadata | Cross-schema table writes/FK; canonical history; browser/agent/connector direct DB |

### 2.3. Environments

| Environment | Назначение | Данные и доступ | Условие использования |
| --- | --- | --- | --- |
| Local/unit | Pure functions, schemas, state machines, UI components | Только generated synthetic values; external integrations mocked и явно маркированы | Не даёт real integration или G0 capability evidence |
| T00 capability sandbox | Pinned upstream/GitLab/IdP/PostgreSQL/CI checks; editor/retrieval audit | Synthetic sandbox users/groups/repositories; scoped nonproduction credentials | После доступа; иначе соответствующие проверки BLOCKED |
| Integration/fault sandbox | A01–A36, races/crashes/webhook loss/schema denial/provider failures | Отдельные synthetic repositories, DB, objects и fault controls; никаких client docs/secrets | Approved sandbox test plan; destructive faults только внутри sandbox |
| Corpus preflight/cutover staging | Dry-run, controlled import, exact SHA review, preflight non-serving index | Согласованный corpus perimeter; пользователи и serving закрыты до activation | Separate migration/import authorization и human sign-off |
| Restore/upgrade rehearsal | Clean restore, second client, rollback, cold offline start | Isolated synthetic restore target и отдельные credentials | Не подключается к production grants/egress без отдельного решения |
| Dedicated client deployment | Эксплуатация одного клиента | Production data только после всех gates и owner approvals | Не выбран и не развёрнут этим документом |
| Second client acceptance | Config-only повторение delivery | Полностью отдельные resources/secrets/backups/egress | G3; code/SBOM core остаётся общим |

## 3. Configuration, secrets и credential matrix

### 3.1. Versioned configuration

| Область | Обязательное содержимое | Владелец/источник | Правило изменения |
| --- | --- | --- | --- |
| Space registry | `space_id`, 1:1 `repository_id`, target branch, default private, data profile, activation state | Versioned client config + GitLab + GO observations | Новый Space — новый repository и grants; запрет cross-Space reuse |
| Access/approval policy | Per-Space repository/bundle/access+approval revisions, group snapshot, actor+Space revocation epochs, longest-prefix approver scopes, engineering vs business roles | Git policies + external IdP groups | Независимый согласованный bundle и fresh recheck именно каждого Space; borrowed binding и page `access` запрещены |
| Identity | Provider profile, issuer, stable attribute, encrypted endpoints, group roots | Client IdP config; concrete attributes UNKNOWN до T00 | objectGUID/entryUUID или issuer-scoped `sub`; никогда email/login |
| Model connections | Main/auxiliary model IDs, connection/profile, dimensions, token context, approved endpoint/perimeter | Open WebUI/hoster.ai inventory | Только inventoried connections; все fallback заранее versioned и разрешены |
| Index profile | Chunking/extraction/embedding/rerank/OCR/index config, config hash, generation algorithm | Versioned index config | Независимо от Git generation; change → shadow/full validation и atomic pointer |
| Source registry | Source ID/binding/account ref, target Space/path, owner, modes, current policy hash | Client source config + immutable source versions | Secret reference только; one outstanding proposal; tombstone ≠ delete |
| Data/media/security | Data profile, PII disposition, media classes, admission limits, sandbox/archive rules | Owner policy + content standard | Fail closed; schema/config limits не выдавать за measured production limits |
| Offline assets | Container/package/model/OCR/extraction/reranker assets и SBOM hashes | Versioned artifact registry | Отсутствие asset блокирует readiness, не включает Internet fallback |
| Backup/restore | Ref/object/package perimeter, manifests, mirror targets, consistency policy, RPO/RTO | Owner backup policy | Без credentials в manifests; restore только clean isolated target до drill PASS |
| Runtime budgets | TTL, retries/backoff, queue sizes, timeouts, request/body/archive/media limits | OWNER_TBD после T00/measurement | Versioned config, monitoring; не придумывать значения в runbook |
| Feature seams/branding | Managed KB flags, feature file versions, branding assets/notices | Reusable core + client config | Никаких client code branches; upstream notices/licenses сохраняются |

Секреты не входят ни в одну versioned config или manifest. Конфигурация содержит opaque secret references и nonsecret metadata. Change record фиксирует actor, reason, config version/hash, affected Spaces, validation evidence и rollback reference, но не сам секрет.

### 3.2. Логические credentials и границы

Ниже перечислены **logical identities**, не утверждённые GitLab token types или secret names. Concrete upstream credential mechanisms — UNKNOWN до T00.

| Владелец/consumer | Credential или secret reference | Минимальная способность | Явно недопустимо |
| --- | --- | --- | --- |
| Browser ↔ Open WebUI | Upstream authenticated session + own-GO CSRF mechanism | Human read/propose/decision по server AuthzContext | Anonymous managed access; actor/groups/tenant как client authority; GitLab merge token |
| Open WebUI → GO | Scoped service credential с bound user context | Versioned GO read/propose/decision APIs | Direct DB/Git merge; impersonation без trusted user context |
| GO proposal/read | Proposal-scoped GitLab credential | Exact reads, branch/MR/notes/tags/proposal metadata | Merge permission; broad admin; CI/index writes |
| GO merge | Отдельный GitLab merge credential | Merge approved MR только на protected target | Выдача UI/agent/connector/CI; arbitrary user token; прямой доступ из browser |
| GO → Identity/AuthZ | Internal AuthZ API credential | Fresh AuthzContext/group/policy validation | `kb_authz` direct tables у GO; cached indefinite allow |
| Bounded agent | Server-issued agent capability + trusted run/requester context | Read/search/single-page propose | Merge, grants, export, shell, generic SQL, arbitrary Git/filesystem/Python/Tool Creation |
| Connector source reader | Source-account secret ref | Только разрешённые source objects/versions | Source admin; managed main merge; grants/index writes |
| Connector → GO | Proposal-only credential | ProposalRecord/MR и source cursor status через API | Merge, direct push, index, grants, export |
| CI Git reader | Exact-main/cutover read credential | Read exact repository snapshot и required assets | Merge, canonical branch writes, grants |
| CI object reader | Scoped object read credential | Immutable object/version/hash reads | List/export других клиентов; arbitrary bucket admin |
| CI/index DB | `kb_index_writer` и single pointer role | Own migrations/runs/snapshots/chunks/embeddings/pointer | `kb_ops`/`kb_authz`/upstream writes; merge |
| Retrieval DB | `kb_index_reader` | Scoped read-only candidates/status | Любые DB writes или pointer publication |
| Identity LDAP | Read-only bind secret ref | LDAPS/StartTLS search stable IDs/groups | LDAP writes, unencrypted bind, passwords в logs |
| Identity OIDC | Client ID/secret ref и issuer config | Selected upstream OIDC login/group profile | Dynamic unapproved issuer; `sub` без issuer scope |
| Identity DB | `kb_authz_writer` | Own grants/contexts/snapshots/migrations | `kb_ops`/`kb_index`/arbitrary upstream SQL |
| GO DB | `kb_ops_writer` | Own proposals/decisions/barriers/idempotency/inbox/reconciliation | `kb_authz`/`kb_index`/upstream writes |
| GitLab webhook | Verified webhook credential/signature secret ref | Authenticate/replay-check intake | Доверие payload actor/SHA как merge proof; secrets в event envelope |
| Ingestion object writer | Staging/immutable object write capability | Approved source package/asset writes | Canonical merge или arbitrary object deletion |
| Export operator | Human delegated full-Space/history capability | Full clone+manifests с per-batch fresh authorization | Filtered export как поддерживаемый формат; чужой Space/history |
| Backup/mirror | Separate read/write backup credentials | Explicit refs+MR metadata+assets+manifests backup и restore в designated target | Production write/merge; cross-client repositories; secrets в открытом manifest |
| hoster.ai/model connections | Open WebUI connection secret refs | Только approved models/routes | Secrets в browser/export/logs; неуказанный fallback/external PII route |

### 3.3. Secret handling policy

1. Секреты находятся только в согласованном deployment secret storage; в Git, product tables, code, images, logs, traces, MR notes/tags, model context, export и decision/asset manifests не попадают.
2. Rotation выполняется по owner-approved procedure с overlap/rollback semantics конкретного upstream; numeric rotation TTL и downtime window — OWNER_TBD. Rotation не меняет business stable IDs или DecisionRecord hashes.
3. Доступ к secret references и rotation аудируется без значения секрета. Ошибки redact credentials, query/body secrets, signed URLs и provider payloads.
4. Backup secret material не смешивается с обычным Git mirror/export. Используется отдельная approved secrets backup/recovery policy с controlled access и restore drill; plaintext secrets в package запрещены.
5. Emergency credential revocation не открывает routine direct human merge. Routine break-glass product capability отсутствует; emergency out-of-band privileged Owner action обрабатывается как incident по approved G0-D3 и §7.5.
6. При подозрении на утечку: закрыть affected privileged operations, отозвать credential через supported seam, сохранить sanitized evidence, провести Git/provider/DB audit и fresh AuthzContext; не копировать секрет в ticket/report.

## 4. Startup и readiness runbook

### 4.1. Preflight перед любым стартом

1. Подтвердить разрешённую phase и отдельное deploy authorization. Проверить pinned baseline, SBOM, licenses/branding notices и environment identity.
2. Проверить, что target — выделенный контур клиента/sandbox; synthetic fixtures отделены от client corpus. Для production corpus потребовать согласованный perimeter и sign-off.
3. Сверить reusable core/config versions, 1:1 Space/repository bindings, default-private policies, data profiles, index profile и provider inventory. Несогласованный bundle не активировать.
4. Проверить наличие secret references и доступность secret storage без печати значений. Проверить разделение proposal и merge identities.
5. Проверить, что начальное состояние имеет external merge freeze для bootstrap/recovery и `user_access_enabled=false`. Пустая БД не считается отсутствием операций.
6. Проверить egress allowlist: default disabled; только одобренные IdP/GitLab/hoster.ai/source endpoints. Отдельно подтвердить разрешение на платные/внешние calls.
7. Проверить offline assets и DB/CI/index capacity по конфигурации; thresholds capacity — OWNER_TBD. Не применять schema max lengths как resource plan.
8. Подготовить sanitized run ID, config versions/hashes, exact refs и evidence destination. Остановиться при неизвестном credential scope или cross-client resource.

### 4.2. Порядок startup/recovery

| Порядок | Логическая операция | Readiness/barrier |
| --- | --- | --- |
| 1 | Установить/подтвердить bootstrap merge freeze и отключить managed user/sensitive payload access | Обязательно до DB rebuild и первого startup reconciliation |
| 2 | Запустить owner-specific PostgreSQL components; применять только approved owner migrations после baseline | Проверить writer/migration roles и отсутствие cross-schema writes/FK; non-owner migration BLOCKED |
| 3 | Запустить Identity/AuthZ; получить fresh nested groups и exact Git policy bundles | При IdP/policy mismatch закрыть privileged и private payload paths; старый context не allow |
| 4 | Запустить GO read/proposal/recovery без открытия merge targets | Восстановить unresolved DecisionRecords, target barriers и global bootstrap freeze из Git-derived evidence |
| 5 | Выполнить startup `bootstrap_merge`/target reconciliation для всех репозиториев | Unknown/inconclusive targets quarantined; merge не открывается по пустой projection или lock expiry |
| 6 | Запустить CI/object/index workers с retrieval pointer publication disabled до validation | Exact-main read only; preflight и partial runs не serving |
| 7 | Выполнить HEAD/index reconciliation; при потере `kb_index` — full rebuild по разделу 8 | No active validated pointer → `INDEX_NOT_READY`; stale mode остаётся выключен |
| 8 | Включить approved provider connections и выполнить nonsecret inventory/health checks | Нет silent fallback; при отсутствии required model/route соответствующий readiness — BLOCKED |
| 9 | Проверить GitLab protections/webhook authenticity, no-bypass matrix и freshness barriers | Non-privileged human/engineering/bot direct merge denied; CI/connector auto-merge denied; privileged Owner unexpected history вызывает incident/quarantine |
| 10 | Снять bootstrap freeze только для conclusive targets после fresh AuthZ и operational checks | Per-target recovery сохраняется независимо; один healthy target не открывает другой |
| 11 | Включить managed user access только для activated Spaces с published pointer | Cutover Space до published pointer остаётся closed; upstream personal Notes/chats не затрагиваются |
| 12 | Зафиксировать startup report и оставшиеся BLOCKED/recovery/DLQ items | Нет overall READY при скрытых failed/barrier/missing closure items |

При сбое startup сохранить fail-closed state. Не перезапускать merge calls автоматически и не открывать retrieval ради smoke test.

## 5. Corpus preflight и cutover runbook

### 5.1. Подготовка и dry-run

1. Утвердить repository perimeter, source corpus, data owner, source owner, approver groups и synthetic-vs-production classification.
2. Создать/проверить один unpublished repository=Space, собственные access/approval policies и отсутствие published index/user access.
3. Выполнить deterministic dry-run для зафиксированного `source_snapshot+config_sha256`: path→UUID, tree, stable links, provenance, attachments, errors/warnings и `canonical_writes=false`.
4. Проверить extraction/media/PII/security disposition, unresolved required links, orphan/duplicate/cycle/invalid paths, critical media и source deletion/conflicts.
5. Два независимых human reviewers проверяют import report и representative corpus diff; автоматический conversion не считается semantic equivalence proof.
6. Controlled bulk допускается только до cutover, при закрытых пользователях, отсутствии published index и отдельном migration/import authorization. Он не отменяет subsequent exact review.
7. Зафиксировать exact `cutover_sha`, full content/tree hashes, validation evidence и sign-off stable ID в CutoverRecord.

### 5.2. Cutover state machine

**Последовательность обязательна и не переставляется:**

1. **Freeze first:** включить repository/target write freeze и убедиться, что pre-cutover writes остановлены; user access остаётся закрыт.
2. **Exact HEAD:** прочитать target HEAD и потребовать `HEAD == cutover_sha`.
3. **Drift stop:** при любом изменении HEAD после sign-off или во время cutover перевести запуск в failed/stopped без published pointer/user activation. Новый CutoverRecord/sign-off/preflight обязателен.
4. **Protected baseline:** создать/проверить protected validation/cutover tag, target protections и normal managed merge-only-GO rules. CI proposal/bot и non-privileged human/engineering direct push/merge запрещены; privileged Owner bypass подлежит out-of-band incident detection/quarantine; bulk после этого не используется.
5. **Inactive preflight:** CI читает exact `cutover_sha`, создаёт отдельные preflight request/run/snapshot IDs и full exact+semantic descriptor с dependency/attachment/policy closure, включая `approval_policy_revision`, `purpose=cutover_preflight`, `is_preflight=true`, `serving_allowed=false`, `snapshot_sha=cutover_sha`.
6. **Validate preflight:** проверить eligibility, paths/IDs/stable links/media, complete closure, fresh per-Space ACL negative controls, non-null exact+semantic ready hashes и отсутствие `main` writes от CI. Preflight остаётся immutable, никогда не active и не serving.
7. **Create published pair:** GO создаёт отдельный `IndexRequested(preflight=false)`; CI создаёт отдельные published run/descriptor с новыми request/run/snapshot IDs, но `cutover_sha == main_sha == preflight.snapshot_sha == published.snapshot_sha`, одинаковыми dependency closure, policy triple и exact/semantic hashes. Полная validation повторяется; preflight identity не переиспользуется.
8. **Publish index:** единственный CI/index writer блокирует `publication_fences(space_id,profile_id)` для всех generations и в одной transaction выполняет CAS по expected current fence+pointer, latest Git ancestry и exact validated run/snapshot. Stale owner обновляет ноль rows. Только published non-preflight descriptor получает active pointer.
9. **Activate Space:** только после наблюдения validated published pointer GO активирует Space и `user_access_enabled=true`; `index_activation_observed_at <= space_activated_at`. CutoverRecord/timestamp/evidence сохраняются.
10. **Post-cutover verify:** reader/author/approver paths, direct push denial, fresh per-Space search/citation, merge-only-GO, subsequent import через MR/human DecisionRecord/GO merge и backup/mirror perimeter.
11. **Record:** сохранить CutoverRecord, exact SHA, protected refs, обе пары preflight/published request+run+snapshot IDs, generation/profile/publication fence, pointer и activation timestamps; unresolved items остаются BLOCKED.

Replay cutover возможен только для того же Space+SHA при сохранённом freeze и `HEAD == cutover_sha`; resumable states используют идемпотентный transition, а не новый implicit corpus snapshot.

### 5.3. Остановка и rollback cutover

- До protections/activation: оставить Space inactive, freeze сохранить, зафиксировать причину и повторить только согласованный pre-cutover process.
- После protections: любые canonical fixes выполняются reviewed MR/new commit + GO merge; history rewrite и новый controlled bulk запрещены.
- При preflight failure: не публиковать pointer и не активировать users; ошибочный corpus не откатывается destructive cleanup.
- После activation: эксплуатационный откат содержимого — новый revert-MR с human review; старый index/profile rollback — только validated snapshot, не canonical history rollback.
- Неизвестный merge/cutover outcome сначала reconciliation/quarantine; повторная операция не создаёт новый identity для маскировки.

## 6. Нормальные merge, index и source operations

### 6.1. Ежедневный операционный контур

Оператор наблюдает и запускает versioned workflows, но не исправляет production rows/refs вручную.

- Проверить open proposals/review queues, stale bases, `RECOVERY_REQUIRED`, quarantine age и target locks; DocOps `valid_until` scheduled/due/removed queue сверять с exact document revision, не как второй канон.
- Проверить index HEAD lag, requested/building/validating/ready/active runs, exact+semantic readiness, approval policy/dependency mismatches, DLQ, late/superseded jobs и publication fence/CAS denials.
- Проверить per-Space group/policy freshness, actor+Space revocation epochs, managed grant drift и fresh sensitive recheck errors; borrowed cross-Space binding — integrity incident.
- Проверить source `seen/proposed/merged`, outstanding proposals, conflicts/tombstones и отсутствие auto-merge.
- Проверить export closure, backup/mirror freshness, missing assets, object-hash errors, secret/log redaction и offline/provider inventory.
- Открыть incident/runbook по result code, Space/repository/target/request/run/decision/merge SHA; не включать raw private content в ticket.

### 6.2. Нормальный merge lifecycle

1. ProposalRecord и MR создаются через GO от exact base; `main` не меняется.
2. Reviewer проверяет полный diff/front matter/links/media/rationale/evidence. После нового commit/rebase approval повторяется.
3. Human accept/reject/cancel создаёт canonical DecisionRecord с одинаковым note+tag JSON/hash; `Idempotency-Key == decision_id`.
4. Для accept GO проверяет fresh authz/approver separation/policy bundle/proposal SHA/base, приобретает per-target lock и перед merge повторно требует `HEAD == base_sha`.
5. До external call одной transaction фиксируются `merge_attempted` и per-target `recovery_required` с unresolved accept link и owner/fencing.
6. GO вызывает только real merge; merged признаётся по commit, `parents[0]=base_sha`, `parents[1]=proposal_sha`, four trailers, note/tag/hash/target/actor. Затем target-wide reconciliation подтверждает outcome каждого unresolved accept; barrier очищается отдельной fenced transaction только при отсутствии unresolved/unknown/quarantined links и доказанном request completion.
7. Identical replay возвращает Git-derived outcome и создаёт ноль attempts. `failed` допустим только после completed+no-merge evidence; recovery coordinator может затем выполнить guarded same-decision/new-attempt retry с fresh preconditions и атомарно восстановленным barrier. `conflicted`/`invalid` terminal и не retryable; unknown/invalid без proven outcome не очищает barrier. Оператор никогда не советует новый decision/idempotency key после timeout.
8. Index publication — отдельная фаза; merge не ждёт и не доказывается indexing. Integrity-valid reject/cancel имеют note+tag, verified MR closure и не создают merge/`main` write; mismatched record → invalid, не normal closure.

### 6.3. Нормальный index lifecycle

1. Webhook authenticates/replay-checks, затем GO читает current Git state; payload actor/SHA не является proof.
2. Для observed exact eligible HEAD создаётся deduplicated IndexRequested с `main_sha+main_generation_id+index_profile_version` и preflight flag.
3. CI читает exact snapshot, разрешает documents/links/assets/shared policy inputs, строит inactive exact+semantic projections и dependency closure.
4. Incremental run публикуется только при equivalence полному closure full snapshot на том же SHA; иначе расширяется closure или выполняется full rebuild.
5. Validator проверяет both projections, eligibility, policy/media/ACL conditions и readiness. Partial run не active.
6. Single pointer writer блокирует per-`(space_id,profile_id)` fence для всех generations и атомарно делает CAS по expected current fence+pointer, latest ancestry и exact validated run/snapshot; stale owner получает zero rows, older job становится `superseded`. Active допустим только для published non-preflight snapshot; ordinary run требует active-Space evidence, controlled cutover — pointer до Space activation. Retrieval делает per-Space fan-out и повторно проверяет собственный active snapshot, full document revision, fresh per-Space ACL и полный cursor descriptor set.
7. Lost/duplicate/out-of-order events разрешаются periodic HEAD reconciliation, bounded retry/DLQ; canonical Git history не изменяется.
8. Новый model/chunking/extraction profile строится как shadow/new snapshot; старый active не мутируется. Переключение — только после owner-approved quality/operational evidence.

### 6.4. Source sync lifecycle

`observed → seen durable → proposal pending → human review → verified merge → merged` с отдельными no-op/conflict/retry/DLQ/tombstone. `proposed` никогда не становится `merged` после MR creation, timeout или index completion. На один source object — один outstanding proposal; новые versions получают superseding diff, не параллельный MR. Curated changes сохраняются через previous imported base; удаление источника — tombstone/review, не автоматическое удаление страницы. `live_operational` остаётся typed read-only источником со `snapshot_time`.

## 7. Recovery, quarantine, outages и reconciliation

### 7.1. Target recovery/quarantine runbook

Нормативные crash phases находятся только в [integration.md §7](integration.md#7-crash-recovery-и-timeout-reconciliation-spec-71-73); здесь — operational actions, не вторая normative crash table. Триггеры: crash, timeout, lost response, lock loss, changed HEAD, note/tag/trailer/parent mismatch, partial DecisionRecord, unknown outcome после rebuild или любое недоказуемое состояние.

1. **Не повторять merge.** Сохранить/установить durable per-target `recovery_required`; blocked scope — все новые merges на `(repository_id,target_branch)`, включая другие MRs. Не затрагивать соседний target/Space и не использовать его evidence.
2. Назначить recovery owner с новым fencing token. Старый owner не может update result/clear barrier после loss; lock expiry не снимает recovery.
3. Собрать sanitized inflight metadata: decision/proposal IDs, base/proposal SHAs, request fingerprint, attempt/owner/fencing и phase. Не включать raw payload/provider response.
4. Выполнить target-wide scan **всех** unresolved accepted DecisionRecords, MRs, source/target refs, merge ancestry, notes/tags и GitLab audit trails. Сверить full Space/repository/target perimeter каждого barrier link/run/finding.
5. Для accepted candidate проверить note+tag same canonical JSON/record/canonical hashes, tag target, merge parents и `Decision-ID`/`Decision-Note-ID`/`Decision-Hash`/`Approved-by`.
6. Классифицировать каждый unresolved accept и сохранить `(decision.state,attempt.state,barrier,barrier_decisions)`:
   - **merged:** все Git proofs совпадают; записать Git-derived `verified_merged` без повторного merge;
   - **failed:** только `request_state=completed + no_merge_proven=true + reconciliation evidence`; unknown/timeout не переводить в failed;
   - **conflicted:** terminal Git-derived conflict с completed+no-merge evidence; `retryable=false`, новая reviewed ProposalVersion обязательна;
   - **invalid:** terminal integrity classification, `retryable=false`; correction — новый UUID со supersedes. При unknown external outcome link остаётся unresolved/unknown и target quarantined; supersedes сам по себе не доказывает no-merge;
   - **quarantined:** outcome недоказуем; `merge_attempted + recovery_required + target_quarantined`, recovery сохраняется бессрочно до evidence/owner resolution.
7. После conclusive failed и target-wide clear только recovery coordinator может запустить guarded retry: новый `attempt_id`, тот же `decision_id`, exact base/proposal, fresh policy/group/HEAD preconditions и атомарно восстановленный barrier/link **до** нового call. Identical HTTP replay создаёт ноль attempts; conflicted/invalid retry запрещён.
8. Обновить projections только с current fencing; для merged отдельно инициировать index reconciliation.
9. Снять target recovery отдельной fenced transaction только когда **каждый** accept target имеет доказанный `verified_merged` либо `verified_not_merged`, request completion подтверждён и unresolved/unknown/quarantined links отсутствуют. `invalid`, `failed`, `conflicted`, terminal state или supersedes сами по себе barrier не снимают. Merged/failed/conflicted сериализуются с recovery flags=false только после этого clear; unknown invalid его сохраняет.
10. Зафиксировать reconciliation run/findings, exact refs, result и оставшиеся quarantine. Нет generic TTL auto-clear.

Test injection и tuple assertions находятся в [test-plan.md §8](test-plan.md#8-детерминированная-crashfault-матрица); component-local invariants — [architecture.md §7.7](architecture.md#77-crash-recovery--локальные-component-invariants) и [GO §7.7](components/git-orchestrator.md#77-crash-recovery--локальные-go-invariants).

### 7.2. GitLab outage runbook

1. Определить затронутые repositories/targets и фазу: до нового call, request in-flight, после observed merge, во время reconciliation/export/backup.
2. Остановить новые merge/cutover operations для affected targets; не переключаться на alternate repo и не разрешать direct human merge.
3. Для in-flight/timeout установить или сохранить `recovery_required`; не классифицировать как failed/not merged по transport error.
4. Fresh canonical read/export/source operations, требующие GitLab, завершаются sanitized `UPSTREAM_UNAVAILABLE`/BLOCKED. Stale index mode остаётся disabled; уже activated read может работать только в пределах отдельно разрешённой fresh AuthZ и actual available data, без выдачи stale как current.
5. CI не делает canonical push. Новые index requests дедуплицируются по exact observed HEAD; не выдумывать новый SHA из webhook hint.
6. После восстановления выполнить target-wide MR/main/audit reconciliation: accepted request мог завершиться merge во время outage. Проверить late response, ancestry, parents/trailers/note/tag и все unresolved operations.
7. Возобновить head/index/source/backup reconciliation и только затем по одному открыть conclusive targets. Зафиксировать outage interval, affected scopes, backlog и unresolved quarantine.

### 7.3. IdP, provider и object-storage outages

- **IdP outage:** merge/export/private payload при истёкшем group freshness fail closed; periodic retry не продлевает allow бессрочно. Stable identity attribution не переписывается.
- **hoster.ai outage:** не переключаться на неуказанного provider/model или external perimeter. Read-only canonical operations не зависят от model; generation/embedding readiness соответствующего профиля BLOCKED.
- **Object-storage outage:** missing/unverified asset блокирует affected dependency closure/full export complete claim; mutable URL не используется как обход. Документный merge может быть канонически независим, но index/export должен явно отразить missing input.
- **Secret-storage outage:** не выводить secrets в config/logs и не использовать cached broad credential; sensitive operation BLOCKED по policy.

### 7.4. Reconciliation scheduler и run types

| Run | Trigger | Обязательный scope/output |
| --- | --- | --- |
| `bootstrap_merge` | Startup, пустая/потерянная БД, restore | Global freeze, все unresolved accepted Decisions/targets, conservative barriers |
| `target_merge` | Timeout, lock loss, crash, mismatch, manual incident | Полный unresolved set target, MR/main/audit ancestry и note/tag/trailer proofs |
| `head_index` | Scheduled, webhook loss, CI recovery, late job, restore/rebuild | Current HEAD, Git ancestry generation, active pointer/profile, missing runs/DLQ |
| `source_sync` | Scheduled, source connector recovery, source webhook loss | Immutable versions, registry mappings, seen/proposed/merged и outstanding MR evidence |
| `restore` | Clean restore/rebuild | Package closure, refs/decisions/assets/policies/grants и conservative unknown outcomes |

Periodic intervals, retry/backoff и freshness кроме нормативных group refresh ≤15 минут/revocation ≤30 минут — OWNER_TBD. Reconciliation evidence содержит refs/counts/result codes, но не document text/raw notes/provider payloads. Run row не является merge proof.

### 7.5. Privileged GitLab Owner out-of-band incident / emergency break-glass

G0-D3 остаётся APPROVED и не переоткрывается. Routine/self-service break-glass product capability отсутствует. Эта процедура — DESIGN NOT EXECUTED для обязательного emergency governance, а не разрешение выполнить реальный incident action, production change, history rewrite или direct managed merge.

1. **Restricted account inventory:** вести instance/project Owner accounts, назначенных ответственных и periodic access review; минимизировать privileges и исключить shared credentials.
2. **Emergency authorization:** для преднамеренного emergency действия получить отдельный authorization record вне этого proposal; зафиксировать actor, reason, exact repository/target/SHAs, timestamp и audit refs. Не выдавать routine admin action за GO merge.
3. **Detect:** out-of-band reconciliation сравнивает unexpected target HEAD/merge history, MR/note/tag/trailer/audit evidence с GO records. Неизвестный или несоответствующий commit не маркируется GO merge.
4. **Freeze/quarantine:** немедленно включить managed-write freeze и affected-target `recovery_required`/quarantine, остановить новые managed merges и сохранить неизменяемые audit refs. Соседние targets изолируются по evidence, а не глобально без необходимости.
5. **Reconcile:** выполнить Git-derived reconciliation всех unexpected commits и unresolved accepts; зафиксировать proven/unproven outcomes и оставить unknown target quarantined.
6. **Remediate:** подготовить reviewed remediation/revert-MR через normal human decision/GO merge там, где применимо; history rewrite и destructive cleanup запрещены. Не очищать barrier по terminal label или TTL.
7. **Credential review:** проверить privileged access/session/audit trail и выполнить rotation по отдельной security procedure при подозрении на компрометацию; secrets не попадают в incident evidence.
8. **Close:** owner-reviewed incident closure требует conclusive target-wide evidence, fresh AuthZ, завершённого remediation и подтверждённого recovery. Quarantine снимается только после этого; reopen сам по себе не доказывает corrected content.

## 8. Полный rebuild `kb_ops`, `kb_authz`, `kb_index`

### 8.1. Общий протокол

1. Объявить rebuild incident, зафиксировать config/model/index versions и доступный Git/source/object evidence.
2. Внешним deployment control установить global merge freeze; закрыть privileged payloads и, при потере AuthZ, все private payloads. Не полагаться только на DB lock.
3. Сохранить sanitized pre-rebuild diagnostics без destructive cleanup. Rebuild выполняется только owner component своей схемы по approved migration procedure.
4. Не восстанавливать transient merge status, AuthzContext или active pointer как canonical truth.
5. После каждого schema rebuild выполнить соответствующий reconciliation и negative security checks. Открывать targets/users постепенно после полного safety closure.

### 8.2. `kb_ops`: Git-derived projections

1. Внешний merge freeze уже активен. Создать conservative target barriers для всех targets; отсутствие evidence для unresolved operations означает `recovery_required`.
2. Сканировать все GitLab MRs/source branches/protected decision tags/MR notes/merge commits/main ancestry и source registry.
3. Пересоздать proposals и immutable ProposalVersions/ProposalRecords с trusted principals/version authors/requesters/runs.
4. Пересоздать accepted/rejected/cancelled Decisions из note+tag; несовпадение/отсутствие — invalid, не merged.
5. Для accepts восстановить outcomes из real merge parentage/trailers и GitLab audit. Transient attempts/idempotency history могут быть восстановлены не полностью; Git-derived dedupe обязателен.
6. Выполнить target-wide reconciliation всех unresolved operations и source cursors. `proposed` не повышать до `merged` без verified merge.
7. Открывать merges по одному target после conclusive results и fresh AuthZ; unknown targets остаются quarantined.

### 8.3. Correction tasks: отдельный non-Git-derived backup и restore

`docops-correction-task-v1` current projections, append-only events, restricted evidence и idempotency history не выводятся из Git/MR и не входят в Git-derived rebuild §8.2. Это отдельный GO-owned operational backup perimeter внутри `kb_ops`, а не canonical content, ProposalRecord или DecisionRecord.

1. **Separate backup:** по owner-approved cadence/consistency policy сохранять correction-task current projections, append-only events, restricted evidence и idempotency records отдельным durable backup с Space/repository perimeter, backup position, hashes и event-sequence metadata. Git mirror/metadata backup не заменяет этот backup; plaintext secrets и raw private payloads запрещены.
2. **Admission:** при restore проверить backup completeness, schema/tool versions, Space/repository binding, hashes и event sequence. Missing/corrupt/incomplete backup оставляет affected correction scope unavailable/quarantined и требует incident review по [correction contract](contracts/docops-correction-api.md); не объявлять восстановление из Git-only evidence.
3. **Operational restore:** восстановить current/events/evidence/idempotency только из этого backup через GO-owned procedure с external merge freeze. Не fabricate/delete/resolve/cancel tasks и не переписывать event history; terminal states не переоткрываются replay.
4. **Linked-MR reconciliation:** после §8.2 сверить каждый optional linked MR с restored ProposalRecord, canonical DecisionRecord и verified GO merge/outcome. Linked MR сам по себе не доказывает corrected/published; missing/mismatched evidence сохраняет task open/in_review или quarantined по contract, без автоматического resolve/cancel.
5. **No second canonical write path:** backup/restore/reconciliation и correction API не редактируют, публикуют или архивируют canonical content. Любое content correction идёт только через обычный MR/human DecisionRecord/GO merge; Git-only rebuild не воссоздаёт и не удаляет correction lifecycle.
6. **Evidence:** отдельно записать backup/restore hashes, event-sequence/perimeter checks, linked-MR reconciliation outcomes, blocked scopes и отсутствие canonical writes вне governed MR path.

### 8.4. `kb_authz`

1. Закрыть privileged operations и все private payload paths; прежние AuthzContexts/sessions не восстанавливать как действующие разрешения.
2. Создать `spaces`, identities/group snapshots/policy snapshots из deployment registry, fresh IdP nested groups и exact Git policy revisions с composite Space/repository references.
3. Активировать только полностью согласованные access+approval bundles **per Space**; current/previous cutovers и grants из другого Space отклоняются. Восстановить actor revocation epoch и independent per-Space policy/group/epoch bindings в `authz_contexts` + `authz_context_spaces`; top-level shared bundle не создавать.
4. Пересчитать effective grants и сравнить desired/observed managed upstream grants через supported seam. Не выполнять arbitrary upstream SQL.
5. Инвалидировать полный per-Space cursor descriptor/policy/group/epoch set и live subscriptions, выдать новые `authz-context-v2` и проверить fresh deny/anti-enumeration/cross-Space borrowed binding.
6. Разрешить GO merge recovery только с новым AuthzContext и exact per-Space group/path/longest-prefix approver checks. Revocation propagation не ждёт index.

### 8.5. `kb_index`

1. Stale mode выключен; до нового validated pointer retrieval отвечает `INDEX_NOT_READY`.
2. Для activated Spaces выбрать exact eligible current main; для cutover preflight — exact `cutover_sha`, без serving.
3. Восстановить Git ancestry generations и versioned index profile config; не сортировать по lexicographic SHA и не смешивать generation с profile.
4. Выполнить full run: parse eligible Markdown/front matter, stable IDs/tree/links/parentage, provenance, immutable attachment versions/hashes, media admission и shared policy inputs.
5. Построить полный dependency closure, chunks, exact и semantic projections. Embeddings только через approved inference/offline assets; нет скрытого платного/external fallback.
6. Проверить full/incremental equivalence только как последующую оптимизацию; initial restore pointer создаётся из full validated run.
7. Проверить both exact+semantic readiness, `document_revision_sha` отдельно от `snapshot_sha`, ACL negative controls, archived/pending/rejected exclusions и cross-Space isolation.
8. Единственный pointer writer использует fresh per-Space/profile fence/CAS для всех generations и создаёт новый active pointer только после expected fence/current pointer/latest ancestry/exact validated run checks; stale owner обновляет ноль rows. Старые/late runs superseded; active pointer backup сам по себе не активируется. Для cutover сначала создаётся отдельный published non-preflight request/run/snapshot с новыми IDs и тем же SHA/closure/policy/hashes; preflight остаётся non-serving, затем pointer предшествует Space activation.

## 9. Backup, export closure и snapshot consistency

### 9.1. Обязательный backup perimeter

| Объект | Что сохранять | Критические проверки |
| --- | --- | --- |
| Git mirror | Все target/source refs, protected cutover/validation refs, explicit annotated decision tag refs, commit/tag objects | `object_sha`, peeled `proposal_sha`, raw object SHA-256, refs manifest; mirror не становится write-source без restore procedure |
| MR notes/metadata | DecisionRecord note bodies/IDs, ProposalRecord metadata, MR source/target/SHAs/state и доступные audit metadata | Full Decision-Note-ID linkage, same JSON/hash, GitLab API capabilities и pagination T00 |
| Decisions manifest | Accepted recorded/merge_attempted/merged/failed/conflicted/invalid и rejected/cancelled records, notes/tags/canonical hashes, supersedes, explicit publication outcome+attempt+recovery; merge parents/four trailers/raw hash только для proven merged | Accepted-before-merge не требует merge; reject/cancel имеют verified closure; corruption не скрывается и не становится normal closure |
| Documents/refs manifest | Stable IDs, paths/parent IDs, document revision/content hashes, stable links/origin/valid_until и snapshot/tree SHA | Нет silent truncation/omitted history; explicit refs closure; DocOps projection совпадает с canonical revision |
| Assets manifest + object storage | `object_id/version/sha256`, immutable bytes, media verification/admission, original references, export status | Exported object hash = attachment hash+actual bytes и обязателен только для exported; missing/rejected явны, не имеют fabricated hash и делают complete=false с nonempty missing; mutable URL недостаточна |
| Policies/grants mapping | Access/approval revisions/hashes, bundle ID, group→grant mapping и config version | Fresh external groups не сериализуются как секреты; restore требует explicit mapping и validation |
| Client config | Nonsecret registry/provider/index/source/offline/backup configs и SBOM/seam versions | Config hashes, no secret values/private endpoints в публичном evidence |
| Secrets | Только отдельный approved encrypted secrets backup/recovery mechanism | Не входят в Git mirror/manifests/logs; доступ и restore отдельно аудируются |
| Open WebUI state | Users/sessions/chats/models по отдельной pinned upstream procedure | Не выдавать за full Space export; privacy и upstream backup отдельно проверяются |
| `kb_ops` Git-derived projections | MR/notes/tags/history/source registry rebuild inputs и conservative recovery state | Backup status не доказывает merge outcome; restore начинает с global freeze и conservative barriers по §8.2 |
| Correction-task non-Git-derived operational state | **Отдельный durable backup** current projections, append-only events, restricted evidence и idempotency records с Space/repository perimeter, hashes и event-sequence metadata по §8.3 | Не заменяется Git mirror/metadata backup; restore проверяет hashes/sequence/perimeter и выполняет linked-MR reconciliation без fabrication/deletion/resolve/cancel и без второго canonical write path |
| `kb_index` | Optional immutable backend snapshots/artifacts для ускорения | Не доверять active pointer без full validation; RPO/versions/profile/ACL совместимость обязательна |

Full Space export (`git_clone_with_manifests`) не является полным platform backup: он не содержит secrets/private chats и не заменяет upstream users/sessions/models/secrets procedures. Filtered history export — отдельный DEFERRED privileged workflow.

### 9.2. Snapshot consistency protocol

1. Зафиксировать per-Space `repository_id`, exact `snapshot_sha`, target branch, generation ID и policy/config versions. Multi-Space export не смешивается в один неявный snapshot.
2. Сохранить explicit refs с object IDs и peeled targets. MR notes/metadata/decision manifests связываются с exact proposal/decision/merge IDs, не с «текущим» mutable MR state.
3. До и после metadata/object export наблюдать HEAD/ref versions и immutable object hashes. При drift обозначить package incomplete и создать новый согласованный snapshot; не выдавать смешанные refs за один момент времени.
4. Access+approval policies должны образовывать один согласованный bundle. Grants mapping и source config хешируются по версии, а не по mutable current display name.
5. Каждый asset проверяется по immutable version+SHA-256. `closure.complete=true` допустимо только при `decisions_complete=assets_complete=authorization_complete=true`, пустом `missing[]`, всех assets `exported` с совпадающим actual-bytes hash и совпадении всех refs/decisions/outcomes/attempts/recovery/documents/policies hashes. Accepted без proven merge сохраняется с recovery evidence, не с fabricated merge.
6. Optional DB snapshots координируются отдельными owning components; не заявлять distributed ACID snapshot между GitLab, PostgreSQL и object storage без подтверждённого механизма. Correction backup имеет собственный non-Git-derived position/hash/event-sequence perimeter и не приравнивается к Git snapshot или Git-derived `kb_ops` rebuild.
7. Backup cadence, acceptable drift window, metadata consistency mechanism, RPO/RTO и retention — OWNER_TBD после T00. До этого drill не объявляется соответствующим production objectives.

### 9.3. Export operating rule

Перед началом и перед каждым payload/batch заново проверяются право на Space **и всю историю**, group/export capability, fresh per-Space policy и actor+Space revocation epochs. После потери права прекратить выдачу/следующие batches и не возвращать новый export payload. Full `export-manifest-v2` использует единый format `git_clone_with_manifests`, включает canonical repository refs и decisions/assets/policies/documents manifests с explicit decision outcomes/recovery, исключает secrets/private chats/чужой client corpus и содержит closure report. `ExportJob.state=ready` допустим только при manifest с `complete=decisions_complete=assets_complete=authorization_complete=true`, пустым `missing[]`, всеми assets `exported` и успешной per-batch authorization. Terminal `incomplete` содержит `complete=false` и error/missing evidence, `failed` не выдаёт complete claim; missing/rejected input не скрывается.

## 10. Restore drill runbook

Выполняется в clean isolated dedicated synthetic environment; реальная drill без доступа к clean GitLab/metadata/object store — BLOCKED.

1. **Scope/freeze:** назначить restore run ID и target client; включить external merge freeze, закрыть users/privileged payloads, проверить отсутствие связи с другим клиентом.
2. **Package admission:** проверить manifest hashes, tool/schema versions, explicit refs, decisions/assets/documents/policies closure и `missing[]`. Incomplete package не считается successful restore.
3. **Secrets/config:** восстановить nonsecret config и secret references через отдельную secrets policy; не печатать и не копировать values в reports.
4. **Git/mirror restore:** восстановить repositories/refs/objects в designated isolated GitLab perimeter, MR notes/metadata и protected annotated tags по supported T00 procedure; не ослаблять protected refs для удобства.
5. **Objects:** восстановить immutable object versions и сверить SHA-256/size/media bindings; missing asset оставляет closure failed/BLOCKED.
6. **Policies/grants:** явно сопоставить stable external groups и policy bundles в isolated IdP/upstream; не создавать personal grants по email и не наследовать production access молчаливо.
7. **Git-derived `kb_ops`:** conservative rebuild по §8.2, external freeze сохраняется, unknown merges quarantined.
8. **Correction operational state:** отдельно от Git-derived rebuild восстановить correction-task current/events/evidence/idempotency из durable non-Git-derived backup по §8.3, проверить hashes/event sequence/perimeter и выполнить linked-MR reconciliation. Git-only rebuild не создаёт и не удаляет task lifecycle; restore/reconciliation не fabricate/delete/resolve/cancel tasks и не создаёт второй canonical write path.
9. **`kb_authz`:** fresh IdP/policy rebuild и новые contexts; все old sessions/cursors invalid.
10. **`kb_index`:** full validated rebuild и новый pointer; preflight/backup pointer не serving.
11. **Verify:** сравнить docs/tree/links/parentage/revisions/content hashes; ProposalRecords/Decisions/note+tag/supersedes; real accepted parents/trailers; rejected/cancelled no-merge; assets; policies/grants; correction current/events/evidence/idempotency и linked-MR outcomes; no secrets/private chats/cross-client leakage и no canonical writes вне MR/human DecisionRecord/GO merge.
12. **Negative controls:** direct non-privileged human/bot merge denied, self-approval denied, cross-Space IDOR denied, revoke immediate, late job не откатывает pointer, replay не создаёт duplicate; unexpected privileged Owner history обнаруживается и quarantined как incident. Missing/corrupt correction backup оставляет affected scope BLOCKED/quarantined и не восстанавливается из Git-only данных.
13. **Reopen:** только после conclusive target и linked-MR reconciliation, fresh AuthZ, active index и owner review. Targets открываются отдельно.
14. **Evidence:** записать environment/commands из baseline, elapsed restore/recovery durations, exact SHAs/configs, closure, отдельные correction backup/restore/hash/event-sequence/linked-MR результаты и blocked checks. Сравнение с RPO/RTO выполняется только после owner thresholds; до этого результат — measured DESIGN rehearsal, не production compliance.

Повторить drill для независимых потерь: только Git-derived `kb_ops`, только отдельный correction-task non-Git-derived backup, только `kb_authz`, только `kb_index`, затем для полной потери БД и полного clean-instance restore. Во всех случаях пустая projection не открывает merge, а отсутствие correction backup не восполняется фабрикацией из Git.

## 11. Retention и hard purge

Retention values не выбраны. Владелец должен отдельно определить сроки и юридические/security требования для:

- proposal branches/MRs/ProposalRecords/MR notes/decision tags/audit trails;
- rejected/cancelled/superseded decisions и source tombstones;
- chats, uploaded files, source packages, object versions, mirrors, backups и exports;
- group snapshots, AuthzContexts, grants, revocation и managed grant sync history;
- webhook inbox/outbox, idempotency records, merge attempts, reconciliation runs/findings;
- correction-task current projections, append-only events, restricted sanitized evidence и terminal/open lifecycle records;
- index runs/snapshots/chunks/embeddings/profiles, exact/semantic projections и DLQ;
- operational telemetry, sanitized evidence, model/evaluation artifacts и SBOM history.

Правила:

1. Active recovery barriers, unresolved quarantine, active retry/DLQ, open/in_review correction tasks, their evidence и incomplete restore/export closure нельзя удалять по generic TTL.
2. Очистка current index или удаление файла из `main` не является privacy purge: старые Git commits, forks/mirrors/backups/object versions остаются отдельным perimeter.
3. Git history rewrite, filtered history export, global hard purge, destructive cleanup и новые routine break-glass capabilities — **DEFERRED до отдельных ADR, юридического/owner решения и специального verified runbook**. Emergency G0-D3 out-of-band privileged incident governance обязателен по §7.5 и не откладывается.
4. Canonical decisions в Git не зависят от удаления rebuildable DB row. Operational retention не должна стирать единственное доказательство unresolved outcome.
5. Этот документ не содержит purge/delete commands и не разрешает их выполнение.

## 12. Upgrade, rollback, seam registry, SBOM и branding

### 12.1. Перед upgrade

1. Зафиксировать current/target Open WebUI commits, GitLab version/edition, PostgreSQL/CI/index, source connector, model connections/index profiles и config/schema versions.
2. Обновить SBOM: reusable core, pinned upstream/plugins, direct/transitive dependencies, extraction/OCR/reranker/offline model assets и tool schemas. Проверить licenses, notices и supply-chain evidence.
3. Проверить client-specific feature files и branding. Не удалять upstream license/copyright notices; не объявлять автоматический rebrand. Logo/text/domain остаются versioned client config.
4. Вести **seam registry** для каждого изменения upstream: code file/line, purpose, upstream owner/dependency, required tests, owner, migration/rollback risk, config flag и removal/upgrade condition.
5. Проверить не затрагиваются ли personal Notes/ordinary chats; включить A20 regression. Копирование upstream backend ради KB запрещено.
6. Выполнить backup/restore readiness и проверить exact refs/decision/assets closure до upgrade. Upgrade не должен требовать history rewrite.
7. Согласовать maintenance window, external merge freeze, expected user impact, rollback triggers и owner approval. Численные windows — OWNER_TBD.

### 12.2. Upgrade rehearsal и выполнение

1. Развернуть candidate на отдельной isolated instance с тем же reusable core и synthetic client config.
2. Выполнить owner-specific migrations независимо для upstream, `kb_authz`, `kb_ops`, `kb_index`; cross-component migration/writes BLOCKED.
3. Выполнить cold offline startup, contracts/schema compatibility, provider inventory, startup reconciliation и риск-ориентированные A01–A36.
4. Обязательно проверить merge recovery/idempotency/parents/trailers/note+tag, self-approval/no-bypass, LDAP/OIDC/empty password, fresh ACL/revocation, exact/semantic retrieval, dependency closure, export closure и restore.
5. Для index/model change построить shadow/new profile, измерить quality/latency/cost отдельно и переключить только validated pointer.
6. Зафиксировать actual commands/environment в run evidence, результаты и blocked capabilities. Не закрывать upgrade при mock-only GitLab/IdP/hoster checks.
7. При production upgrade после отдельного authorization включить freeze, выполнить approved owner procedures, reconciliation и staged activation; post-upgrade direct merge denial обязателен.

### 12.3. Rollback

- **Application code/config:** вернуть совместимый pinned artifact/config через deployment procedure, сохранив external freeze до startup reconciliation. Не откатывать canonical Git history.
- **Content mistake:** новый revert-MR/new commit + human review; никаких reset/force-push/history rewrite.
- **Database:** только owning component и заранее проверенная backward/forward migration procedure; unknown merge outcomes остаются recovery required. Не разрешать cross-schema repair SQL.
- **Index/model profile:** активировать ранее validated совместимый snapshot либо построить новый full; не смешивать dimensions/profile/generation и не считать old backup pointer доказательством.
- **GitLab outage во время rollback:** следовать разделу 7.2; late accepted merge обнаруживается reconciliation.
- **Credentials:** rotation и application rollback разделяются; не восстанавливать скомпрометированный секрет из старого backup ради rollback.
- **After rollback:** повторить startup/no-bypass/ACL/recovery/readiness checks и записать config/SBOM/seam diff. Rollback не считается успешным по одному process health check.

## 13. Monitoring, metrics и alerts

### 13.1. Общие labels и telemetry policy

Допустимые correlation labels: `space_id`, `repository_id`, `target_branch`, `request_id`, `run_id`, `proposal_id`, `decision_id`, `merge_commit_sha`, generation/profile, component, actor type и result code. High-cardinality/private IDs включаются только в restricted telemetry по owner policy.

Запрещены в metrics/logs/traces: raw document/chunk/query/rationale/evidence text, provider payloads, secrets, tokens/passwords, signed URLs, PII snippets и полное содержимое MR notes. Long text хранится в Git/object storage, не в telemetry. Dashboard/export аудируются так же, как runtime retrieval.

### 13.2. Metrics и alert conditions

| Область | Метрики/наблюдения | Alert condition и владелец threshold |
| --- | --- | --- |
| Merge correctness | Outcome by result code; merge count per decision/proposal/target; parent/trailer/note/tag mismatch; Git read/merge latency | Любой mismatch/duplicate conclusive merge — immediate integrity alert. Latency p95/p99/timeout budget — OWNER_TBD |
| Serialization/recovery | Lock wait, owner/fencing changes, stale-owner denied updates, `recovery_required` count/age, quarantine findings | Наличие `recovery_required` — immediate operational alert с target runbook; age/escalation window — OWNER_TBD, auto-clear запрещён |
| Decisions | Note/tag write/read failures, hash/target/linkage errors, supersedes/invalid count | `DECISION_INVALID` или missing representation — immediate blocker для affected target |
| Identity/AuthZ | Group snapshot age/success, context denial/stale/revoked, grant drift, sensitive recheck failures | Group refresh >15 минут и revocation propagation >30 минут — REQUIREMENT alerts; остальные freshness budgets — OWNER_TBD |
| Revocation | Time from detected removal to per-channel deny/subscription close, open subscriptions after revoke, provider calls after revoke | Превышение 30 минут — REQUIREMENT alert; новый private payload после completed revoke — immediate security incident |
| Retrieval/index | HEAD lag, queue/run state, exact+semantic readiness, active snapshot age, stale candidate rejection, truncated/error responses | No active pointer/`INDEX_NOT_READY` для activated Space — readiness alert; freshness/latency/quality thresholds — OWNER_TBD |
| Dependency/publication | Closure mismatch, missing assets/shared inputs, late/superseded jobs, pointer fencing conflicts, profile/generation mismatch | Любой non-equivalent/partial publish attempt или late pointer rollback — immediate integrity alert |
| Events/CI | Webhook authenticity/replay rejects, dedupe, retry/DLQ, CI outage, job duration, missed HEAD reconciliation | DLQ/auth reject spike и missed reconciliation — alert; numeric rate/backlog/retry thresholds — OWNER_TBD |
| Source sync | Seen/proposed/merged lag, outstanding count, curated conflicts/tombstones, duplicate proposal attempts | >1 outstanding per source object или auto-merge attempt — immediate correctness alert; lag budgets — OWNER_TBD |
| Export/backup | Per-batch authorization failures, closure/missing count, mirror freshness, package hash failure, backup age, restore drill result | Missing closure/hash failure/unauthorized batch — immediate alert и no complete claim. Backup age/RPO/RTO — OWNER_TBD |
| Model/inference | TTFT и full response отдельно, retry/cancel/malformed args, route/model inventory, fallback attempts, cold/warm cost | Любой unapproved route/fallback/secret/PII egress — immediate security alert. p95/p99 TTFT/full/cost budgets — OWNER_TBD |
| Browser/UX | Canonical read failure/latency, tree/search/read/proposal errors, preview reliability, truncation/retry rates | Unreliable preview merge attempt — immediate merge blocker. UX performance budgets — OWNER_TBD |
| DB/schema security | Cross-schema denied writes, non-owner migration, role drift, migration status, read-only violations | Любая successful non-owner/cross-schema write — immediate security/integrity incident; capacity thresholds — OWNER_TBD |
| Offline/supply chain | Missing assets/SBOM hash mismatch, cold-start download attempts, license/branding/seam drift | Любая unapproved network fetch или missing required offline asset — readiness BLOCKED/alert |
| Telemetry security | Redaction failures, secrets/raw content detected by synthetic canaries, restricted dashboard/export access | Любое confirmed secret/private payload disclosure — immediate security incident; suite target zero disclosures |

### 13.3. Threshold register для владельца

До назначения владельцем не используются как PASS/FAIL: index freshness/lag, p95/p99 Git read/merge latency, TTFT/full response, session/AuthzContext TTL кроме SLO revocation, retry/backoff budgets, queue/DLQ age, corpus size/concurrency/resource limits, search recall/answer quality, backup frequency, RPO/RTO, retention, cost budgets, restore/upgrade windows и alert aggregation windows.

Фиксированные требования, которые не заменяются OWNER_TBD: group refresh ≤15 минут; revocation ≤30 минут; zero unauthorized disclosures в согласованном adversarial suite; ровно один repository=Space; normal managed merge-only-GO после human approval для non-privileged identities; privileged Owner bypass обнаруживается reconciliation и quarantined как incident; preflight/partial index не serving; recovery не очищается по TTL.

## 14. Cold offline startup

1. Заранее опубликовать в approved offline perimeter все pinned container images/dependencies, Open WebUI/GO/components, CI tooling, selected extraction/OCR/reranker assets и main/auxiliary models с SBOM/hashes/licenses.
2. Проверить, что GitLab, IdP, PostgreSQL, object storage и hoster.ai/private inference endpoints находятся в разрешённом доступном perimeter; offline не означает mock integration PASS.
3. Отключить Internet egress полностью; разрешить только approved internal routes. Очистить caches в rehearsal environment, чтобы выявить скрытые downloads.
4. Выполнить startup по разделу 4 с external merge freeze/users closed. Любая попытка download/update/model fallback фиксируется и блокирует readiness.
5. Проверить version/hash каждого artifact/model, provider inventory, dimensions/config, DB owner migrations и offline model calls без секретов в telemetry.
6. Выполнить exact+semantic preflight и full index только из локально доступных assets. Missing model/OCR/extraction/index dependency → BLOCKED для соответствующего route, не silent external processing.
7. Выполнить canonical read/propose/human decision/merge/recovery, fresh IdP AuthZ/revocation и export closure в offline sandbox.
8. Зафиксировать network deny evidence, asset/SBOM hashes, cold-start timings и blocked capabilities. Numeric cold-start threshold — OWNER_TBD; нулевые unapproved external calls — security requirement.

## 15. Operational acceptance G1–G4

Ниже — критерии приёмки и фактический G0 record, не отметки operational execution. **T00 DONE/G0 APPROVED**; G1–G4 остаются незакрытыми DESIGN, real integrations без доступа — BLOCKED.

### 15.1. G0 readiness перед implementation

- [x] Owner design review и T00 capability matrix фактически завершены; selected pins/baseline и команды задокументированы. **DONE:** [baseline.md](baseline.md), [capability matrix](evidence/t00/capability-matrix.md) и reproducible commands записаны; owner review APPROVED 2026-11-08 — [g0-review.md](g0-review.md). **T00 DONE, G0 APPROVED**; operational rehearsals остаются DESIGN_NOT_EXECUTED.
- [x] Подтверждены required GitLab exact-SHA/merge parents/trailers/note+tag/protection/webhook/export capabilities для G0. **Synthetic capability evidence accepted:** 42 completed probes ([gitlab-capabilities](evidence/t00/gitlab-capabilities.md)); target-race привёл к nonconforming merge, поэтому GO lock/barrier обязателен. Ограничения зафиксированы и owner-approved (нет target CAS, privileged Owner bypass/G0-D3, settle proof, webhook allowlist). Это не product integration PASS; redesign сохраняет R/I и требует ADR+owner review и повторное real capability evidence.
- [x] Подтверждены upstream auth/group/session/CSRF seams, DB role/migration boundaries и editor/retrieval reuse для G0. **Accepted with mandatory adapters/deferrals:** static seams, external migrator и runtime DDL denial подтверждены; stock OIDC имеет 2 security FAIL; TipTap adapter selected (G0-D8), browser checks deferred to T04 и не PASS; realtime CRDT вне MVP; CSRF/Origin controls — обязательный adapter (ADR-12). First source connector остаётся owner decision T16/G3.
- [x] A01–A36, CF-01–CF-30, projection mappings, crash/fault matrix, topology, credentials, backup/rebuild/restore и monitoring приняты как testable design на G0 без перевода DESIGN в VERIFIED. Correction-task contract добавлен как последующий DESIGN, не executed test.
- [x] Для каждого недоступного sandbox/integration check статус BLOCKED/deferred с владельцем и условием разблокировки зафиксирован. **Текущие follow-up:** browser editor checks deferred to T04, OpenLDAP runtime 8/8 PASS с production AD/live-SLO follow-up, hoster.ai endpoints UNKNOWN/T11 BLOCKED. CI Runner exact-SHA/no-write — PASS 7/7 ([ci-runner.md](evidence/t00/ci-runner.md)).

### 15.2. G1 — управляемая одна страница

- [ ] Неинженер выполняет read/edit/propose/review/decision/revert без Git/CLI; два независимых human users, business approver без GitLab account.
- [ ] DecisionRecord note+tag, exact proposal invalidation, self-approval denial, idempotency и real merge parents/trailers проверены.
- [ ] Concurrent accepts, target race/fencing, crash/timeout/lost response и recovery/quarantine не дают duplicate/last-write-wins; invalid+unknown сохраняет second-MR denial, conclusive failed guarded same-decision retry отделён от terminal conflicted/invalid.
- [ ] Direct human/engineering/bot/CI merge и all-channel bypass для non-privileged identities отклонены на серверном/GitLab уровнях; privileged GitLab Owner bypass обрабатывается отдельно как out-of-band incident с reconciliation, affected-target quarantine/managed-write freeze и G0-D3 runbook по §7.5, а не как ordinary denial или approved managed path.
- [ ] Startup external freeze, `kb_ops`/`kb_authz`/`kb_index` ownership, monitoring recovery alerts и sanitized evidence работают на pinned sandbox.
- [ ] Нет production user access до published active index и fresh AuthZ.

### 15.3. G2 — corpus, cutover, search и inference

- [ ] Dry-run/controlled import, content/media/PII/security reports и exact sign-off воспроизводимы; no canonical writes в dry-run.
- [ ] Cutover drift останавливается; freeze→protections→inactive preflight→separate same-SHA published request/run/snapshot→per-Space/profile fence/CAS pointer→Space activation соблюдены; preflight никогда не active/serving.
- [ ] Exact+semantic per-Space search работает только на eligible activated published main; citations/revisions/independent bindings/dependency+approval closure/concurrent CAS late jobs проверены.
- [ ] Revocation ≤30 минут и group refresh ≤15 минут подтверждены real sandbox timers и sensitive rechecks; payload/subscriptions/provider paths закрываются.
- [ ] Approved hoster.ai profile/egress/no-fallback и cold offline inventory проверены; unavailable real endpoint остаётся BLOCKED.
- [ ] Full export closure, cross-Space isolation, policy mismatch between review/merge/export и A01–A36 P0 suite проходят на зафиксированном corpus SHA.
- [ ] Owner назначил требуемые quality/latency/capacity/cost thresholds; measurements не подменены желаемыми значениями.

### 15.4. G3 — second client и операционная устойчивость

- [ ] Second dedicated instance развёрнут config-only без client code branch; resources/secrets/backups/egress полностью изолированы.
- [ ] Один выбранный external source работает в безопасном ownership mode без auto-merge; cursors/conflicts/tombstones/one-outstanding проверены.
- [ ] Полный mirror+MR notes+decision tags+manifests+objects+config/secrets policy restore выполнен в clean instance с closure/negative controls; отдельный non-Git-derived correction backup/restore и linked-MR reconciliation проверены без fabrication/deletion и второго canonical write path.
- [ ] Независимые rebuilds и полная потеря БД сохраняют conservative recovery; unknown outcomes не открываются; Git-only rebuild не воссоздаёт и не удаляет correction tasks.
- [ ] Upgrade/rollback rehearsal, seam registry/SBOM/branding, personal Notes/ordinary chats regression и cold offline startup завершены.
- [ ] RPO/RTO/retention и operational security acceptance получили owner decisions; hard purge/history rewrite остаются отдельным DEFERRED контуром.

### 15.5. G4 — измеренная оптимизация

- [ ] Любой profile/cache/retrieval/index change имеет baseline measurement, versioned config и owner-approved quality/latency/cost result.
- [ ] Incremental closure эквивалентен full на том же SHA; shadow/new profile не мутирует active snapshot.
- [ ] Model/config fallback входит в inventory и проходит offline/egress/PII checks; rollback переключает только validated compatible snapshot/artifact.
- [ ] Нет изменений reusable core под отдельного клиента и нет ослабления merge/AuthZ/schema/cutover gates.

## 16. Owner decisions и обязательные блокеры планирования

До соответствующих gates владельцы должны явно выбрать/подтвердить:

1. Pinned Open WebUI commit, GitLab version/edition, PostgreSQL/CI/index baselines и фактические startup/migration/backup commands.
2. Repository perimeter, source corpus, target Spaces/groups/paths и business owners без GitLab users.
3. Первый внешний connector, object storage, source ownership/deletion behavior и data profile/legal approval.
4. IdP profiles/stable attributes, upstream group/grant/session/CSRF mechanisms и scoped service credentials.
5. hoster.ai main/auxiliary inventory, approved endpoints/models/dimensions/fallback, offline assets и egress/paid-call authorization.
6. Deployment/runtime manifests, resource/capacity budgets, monitoring thresholds, maintenance windows и incident escalation owners.
7. Backup cadence/consistency mechanism, RPO/RTO, retention, restore scope и secret recovery policy.
8. Отдельные ADR для filtered export/history rewrite/hard purge/новых routine break-glass capabilities и любых новых canonical/index boundaries. G0-D3 emergency out-of-band incident runbook уже approved и не требует переоткрытия.

Отсутствие решения фиксируется как UNKNOWN/BLOCKED, а не заменяется предположением, молчаливым default или утверждением об успешной проверке.
