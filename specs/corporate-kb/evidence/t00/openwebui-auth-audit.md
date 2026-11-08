# T00 — Open WebUI auth/tool/migration audit

## Статус и рамки

- **Назначение:** sanitized reviewable evidence для **T00 baseline audit**.
- **Это не legal/security owner approval, не G0 design approval и не подтверждение runtime DONE/VERIFIED.**
- Upstream: **Open WebUI v0.13.0**, tag `v0.13.0`.
- Commit: `c38885a1a737da4968f157092f304f3b5481d0bf`.
- Checkout: `/Users/antonsmychkin/Documents/Job/corp_ai_db/_bmad-output/test-artifacts/t00/upstream/open-webui`.
- Ниже пути указаны относительно этого checkout.
- Scope: Python/frontend toolchain; LDAP/OIDC/JIT/session/CSRF; stable identity; groups/roles/grants; Python Tools и execution paths; users/groups models; Alembic ownership и multi-worker caveats.
- Метод: чтение исходников, manifests/CI и read-only Git inspection. В конце `git status --short` был пуст, `git diff --exit-code` завершился успешно.
- Не выполнялись: запуск приложения, LDAP/AD/OIDC calls, DB connections, migrations, runtime smoke, tests, lint, typecheck, build, dependency installation.
- В файле нет secrets, реальных пользователей, email, DN, tokens или production endpoints.

## Инженерный вывод

Upstream содержит пригодные для повторного использования identity/resource seams, но **не должен приниматься как готовая corporate security boundary без adapters**. Основные ограничения: отсутствие stable LDAP/OIDC principal registry, stale external group memberships, произвольный Python в server process, отсутствие action-level capability grants и небезопасный для multi-worker import-time migration owner.

## Positive seams, подтверждённые статически

| Область | Что реально есть | Доказательства |
|---|---|---|
| LDAP empty-password guard | Пустой и whitespace-only password отклоняется до пользовательского bind; код прямо описывает unauthenticated simple bind из RFC 4513. Это static mitigation для риска CVE-2026-44551, не сертификация CVE в runtime. | `backend/open_webui/routers/auths.py:412-428` |
| LDAPS/read-only bind | Поддерживаются implicit LDAPS, CA/cert validation, service bind/search и отдельный user bind. LDAP `add/modify/delete/modify_dn` в auth path не используются; read-only service account достаточен для search. StartTLS отсутствует. | `backend/open_webui/routers/auths.py:436-473`, `backend/open_webui/routers/auths.py:489-496`, `backend/open_webui/routers/auths.py:576-584` |
| OIDC/JIT controls | `sub` обязателен; OIDC signup и merge by email по умолчанию выключены; существует role/group mapping. | `backend/open_webui/utils/oauth.py:2017-2026`, `backend/open_webui/config.py:2564-2573`, `backend/open_webui/config.py:2663-2667` |
| SCIM external ID seam | Есть lookup по `provider + external_id`; пригоден только как часть pre-provisioning adapter, не как готовое LDAP/OIDC JIT связывание. | `backend/open_webui/models/users.py:471-482`, `backend/open_webui/routers/scim.py:592-616` |
| Sessions | HS256 JWT содержит `jti/iat/session_stamp`; проверяются persistent stamp, token type, MFA state и свежий User. Есть human-only dependency, но она применяется не везде. | `backend/open_webui/utils/auth.py:225-241`, `backend/open_webui/utils/auth.py:269-319`, `backend/open_webui/utils/auth.py:428-479`, `backend/open_webui/utils/auth.py:757-760` |
| Groups/grants | Локальная single-parent hierarchy и inherited memberships реализованы через recursive CTE. Group permissions additive (`True > False`). AccessGrant поддерживает user/group principals и read/write. | `backend/open_webui/models/groups.py:188-212`, `backend/open_webui/utils/access_control/__init__.py:32-44`, `backend/open_webui/models/access_grants.py:23-42` |
| Managed sharing | Sharing фильтруется по resource/audience permissions до замены grants. Это пригодный seam для manage/read, но не для execute capability. | `backend/open_webui/utils/access_control/__init__.py:218-302`, `backend/open_webui/routers/tools.py:728-780` |
| Tool read/manage controls | При загрузке saved Tool проверяются active state и read grant; при invocation повторно проверяется active state. | `backend/open_webui/utils/tools.py:353-404` |
| Deferred `call_tool` | Deferred dispatcher разрешается в конкретный target до approval staging; recursion и unavailable target отклоняются. | `backend/open_webui/utils/tool_search.py:134-164`, `backend/open_webui/utils/middleware.py:5672-5705` |
| Resource checks в built-ins | Некоторые built-ins повторно проверяют resource permission, например note write. Это положительный пример, но не общая policy. | `backend/open_webui/tools/builtin.py:79-92` |
| PostgreSQL online schema guard | Online migrations проверяют schema/revision, отклоняют чужие таблицы/history без revision и устанавливают `search_path`. | `backend/open_webui/migrations/env.py:75-106` |

## STOP / ADAPTER findings

### ADR-04 — execution capability boundary: STOP

**Подтверждённые проблемы**

- Сохранение Tool выполняет произвольный Python через `exec` в server process; sandbox/restricted builtins отсутствуют: `backend/open_webui/utils/plugin.py:208-250`.
- Tool Creation доступен и через Workspace API, и как built-in side effect: `backend/open_webui/routers/tools.py:500-549`, `backend/open_webui/tools/builtin.py:3870-3908`.
- AccessGrant содержит только `read/write`, а не `execute`, HTTP-action или другие capabilities: `backend/open_webui/models/access_grants.py:23-42`.
- Default mode — `full`; automations и channels принудительно обходят per-call ask approval: `backend/open_webui/main.py:1240-1250`.
- Native execution централизован в `execute_tool_call`, но legacy handler вызывает callable отдельно: `backend/open_webui/utils/middleware.py:3092-3184`, `backend/open_webui/utils/middleware.py:1102-1144`.
- Direct/browser dispatch и OpenAPI/MCP производят side effects и не должны считаться безопасными только из-за tool listing/filter: `backend/open_webui/utils/middleware.py:3155-3170`, `backend/open_webui/utils/tools.py:1797-1908`.

**Требуемый adapter/design gate**

- Единый deny-by-default capability resolver после deferred target resolution и до side effect.
- Обязательные enforcement points: `execute_tool_call` и legacy `tool_call_handler`; exposure filtering в `get_tools` считать только дополнительной мерой.
- Отдельные policy для automation/channel/background execution, direct/browser dispatch и OpenAPI operation/action mapping.
- Произвольный Python запретить в corporate deployment либо исполнять только в отдельном изолированном vetted executor.
- Per-call approval не считать доказательством capability authorization.

### ADR-10 — LDAP/OIDC identity: STOP

**Подтверждённые проблемы**

- LDAP principal связывается по email, не по stable directory identifier: `backend/open_webui/routers/auths.py:586-597`.
- Search attributes не включают `objectGUID`/`entryUUID`; таких обработчиков в backend не найдено: `backend/open_webui/routers/auths.py:475-487`.
- При нескольких LDAP matches берётся `entries[0]`, без reject на ambiguity: `backend/open_webui/routers/auths.py:489-500`.
- Nested AD matching rule `1.2.840.113556.1.4.1941` и recursive group traversal не найдены. LDAP DN группы сводится к CN, что не является stable group identity: `backend/open_webui/routers/auths.py:391-400`, `backend/open_webui/routers/auths.py:525-568`.
- Пустой LDAP/OIDC group set не вызывает revocation: `backend/open_webui/routers/auths.py:631-639`, `backend/open_webui/utils/oauth.py:1803-1819`.
- OIDC identity хранится как `provider:sub`, где provider — alias вроде `oidc`, а не persisted issuer: `backend/open_webui/models/users.py:450-469`, `backend/open_webui/config.py:2818-2839`.
- DB uniqueness для `(issuer, sub)` или `(provider, sub)` отсутствует; lookup использует первый результат: `backend/open_webui/models/users.py:459-469`.
- StartTLS не реализован; поддерживается только implicit LDAPS.

**Требуемый adapter/design gate**

- Persisted unique mapping `(directory/tenant, objectGUID или entryUUID) → internal user_id` для LDAP и `(issuer, sub) → internal user_id` для OIDC.
- Reject на duplicate LDAP entries, identity collision и cross-issuer collision; email linking только по отдельной явной политике.
- Stable `group objectGUID → local group_id`, transitive closure с cycle handling либо проверенная внешняя flattening-проекция.
- Source-aware reconciliation: пустой external set должен отзывать managed memberships, не удаляя unmanaged/manual groups.
- StartTLS требует отдельной реализации и synthetic AD interoperability evidence, если является обязательным требованием.

### ADR-12 — business approval: STOP

**Подтверждённые проблемы**

- Stock approve/reject разрешён только владельцу chat/message: `backend/open_webui/utils/tool_approval.py:80-86`.
- Решение сохраняется как `approved=True` без отдельного approver, времени, immutable hash вызова и policy/group snapshot: `backend/open_webui/utils/tool_approval.py:105-135`.
- Resolve endpoint использует `get_verified_user`, а не human-only guard: `backend/open_webui/main.py:1883-1899`.
- Cookie принимается как bearer credential, но app-level CSRF token/Origin validation в auth/approval path не найден: `backend/open_webui/utils/auth.py:386-406`. SameSite default `lax`, Secure default `false`: `backend/open_webui/env.py:781-790`.

**Требуемый adapter/design gate**

- Независимый human approver, отличный от initiator; запрет automation/API/subagent credentials.
- Immutable evidence: approver, timestamp, exact tool/action/arguments hash, policy and group snapshot, request/correlation ID.
- Отдельные CSRF/Origin controls и production Secure cookie policy.
- Не использовать stock `approved=True` как доказательство business approval.

### ADR-15 — PostgreSQL migration ownership: STOP

**Подтверждённые проблемы**

- `alembic upgrade head` вызывается при импорте `open_webui.config`: `backend/open_webui/config.py:63-81`.
- `ENABLE_DB_MIGRATIONS` по умолчанию включён: `backend/open_webui/env.py:149-152`.
- Uvicorn допускает несколько workers; каждый worker/replica потенциально импортирует config и запускает migrations: `backend/start.sh:94-110`.
- В online migration path нет single-runner/advisory lock: `backend/open_webui/migrations/env.py:75-108`.
- Offline path не задаёт `search_path`/`version_table_schema`, поэтому небезопасно предполагать custom-schema ownership: `backend/open_webui/migrations/env.py:38-48`.
- ACL migration пропускает malformed/failed grant backfill и затем удаляет source `access_control` columns: `backend/open_webui/migrations/versions/f1e2d3c4b5a6_add_access_grant_table.py:132-143`, `backend/open_webui/migrations/versions/f1e2d3c4b5a6_add_access_grant_table.py:188-223`.
- Duplicate normalized emails останавливают unique-index migration: `backend/open_webui/migrations/versions/f0bd01a18a3d_add_unique_normalized_user_email_index.py:59-75`.
- Legacy `oauth_sub` переносится в JSON и удаляется; multi-provider downgrade не полностью обратим: `backend/open_webui/migrations/versions/b10670c03dd5_update_user_table.py:181-216`, `backend/open_webui/migrations/versions/b10670c03dd5_update_user_table.py:219-236`.

**Требуемый adapter/design gate**

- Один explicitly authorized migration job; runtime workers с `ENABLE_DB_MIGRATIONS=False` и DB role без DDL.
- External expected-head/readiness check: простого отключения migrations недостаточно для fail-closed запуска.
- Data-copy rehearsal: duplicate identity counts, User/Auth checks, полный legacy ACL → access_grant diff, lock/duration and rollback assessment.
- Production migrations не разрешать на основании этого static audit.

## Влияние v0.13.0 migrations на T00 baseline

- В pinned checkout статически найдено **69 migration files**.
- Линейная цепочка заканчивается на `e42c8f710a36_add_notification_inbox`: `backend/open_webui/migrations/versions/e42c8f710a36_add_notification_inbox.py:1-11`.
- Других `down_revision=e42c8f710a36` не найдено. Это static graph inspection, не выполненный `alembic heads/current`.
- Baseline должен фиксировать фактический DB head/schema и именно эту upstream chain; более ранний предполагаемый head использовать нельзя.

## Toolchain и реальные команды

- Python `>=3.11,<3.13`; Docker runtime Python 3.12: `pyproject.toml:121-132`, `Dockerfile:58-59`.
- Frontend Docker/CI использует Node 22; версия пакета `0.13.0`: `Dockerfile:27-29`, `package.json:2-4`.
- Активный backend CI на Python 3.11/3.12:

```bash
pip install "ruff>=0.15.5"
ruff format --check . --exclude .venv --exclude venv
ruff check --select=F --ignore=F401,F403,F405,F541,F811,F841 --output-format=github .
```

Источник: `.github/workflows/backend.yaml:20-43`.

- Frontend unit test command:

```bash
npm run test:frontend
```

Это `vitest --passWithNoTests`: `package.json:26-28`, `.github/workflows/frontend.yaml:49-65`.

- Декларированный Svelte/TypeScript check:

```bash
npm run check
npm run lint:types
```

Обе команды вызывают `svelte-kit sync && svelte-check --tsconfig ./tsconfig.json`: `package.json:16-21`.

- Backend regression workflow делегирует выполнение внешнему `open-webui/tests/.github/workflows/regression.yml@main`; локальной pinned backend test command нет: `.github/workflows/regression.yaml:17-32`. Для воспроизводимого runtime evidence внешний tests repository также должен быть pinned.
- Полноценный Python typecheck в manifests/CI не найден.
- `npm run lint:frontend`, `npm run format`, `npm run i18n:parse` и pre-commit hooks могут изменять файлы; в read-only audit они не выполнялись.

## Разделение static audit и будущего runtime evidence

**Этот файл подтверждает только code/manifest inspection.** Он не утверждает успешные LDAP bind, OIDC callback, CSRF rejection, tool execution denial, migration upgrade или multi-worker safety.

Позднейшие проверки должны использовать только synthetic AD/OIDC/users/groups и изолированную DB copy:

- машинные fixtures, commands, environment и raw logs:  
  `/Users/antonsmychkin/Documents/Job/corp_ai_db/_bmad-output/test-artifacts/t00/openwebui-auth-runtime/`;
- sanitized reviewable summaries и ссылки на raw artifacts: отдельные файлы в  
  `/Users/antonsmychkin/Documents/Job/corp_ai_db/specs/corporate-kb/evidence/t00/`.

До появления таких artifacts соответствующие проверки остаются **NOT RUN / BLOCKED**, а не PASS. Raw logs перед публикацией в evidence должны быть очищены от secrets, cookies, tokens, реальных emails, DNs, пользователей, групп и endpoints.

## Финальная классификация

- **REUSE после design adapter:** session/user models, local group hierarchy, read/write grants, managed sharing, OIDC/SCIM building blocks, native/deferred tool resolution, online schema guard.
- **STOP/ADAPTER для ADR-04/10/12/15:** обязательные ограничения перечислены выше.
- **T00 evidence only:** не legal approval, не G0 approval, не production authorization и не runtime verification.
