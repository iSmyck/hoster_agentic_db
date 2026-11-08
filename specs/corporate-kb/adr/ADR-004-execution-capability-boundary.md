# ADR-04 — Execution capability boundary

**ID/Title:** ADR-04 / Граница исполняемых полномочий человека, агента и сервисов  
**Status:** **Proposed** для G0 design review; T00 audit подтвердил upstream STOP и обязательность adapter (см. Verification). Не считается production approved. Нормативные запреты R06/R16 и I02–I06/I12 остаются обязательными критериями проектирования.  
**Date:** 2026-11-06; дополнено T00 evidence 2026-11-08  
**Requirements/AD links:** R01, R03, R05–R10, R15, R16; I02–I06, I12; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-2, AD-3, AD-5, AD-6; [spec.md](../spec.md): T00, T03, T05, T06, T09.

## Context

Отсутствие merge в schema инструмента само по себе не является security boundary. Полномочия могут появиться через native/custom tools, deferred calls, note chat, automation, channels, external OpenAPI, browser credentials или чрезмерный GitLab token. Документы и tool output недоверенны: prompt injection не должна превращаться в merge, grant или arbitrary execution.

Open WebUI нужно сохранить как продуктовую оболочку без переписывания upstream auth/chat/RAG. При этом merge credential должен быть физически отделён от agent process, browser, CI/indexer и connector. До cutover существует строго ограниченный engineering bulk path по ADR-11; после cutover исключений для agent/connector/LLM нет.

## Decision

1. Open WebUI остаётся **минимальным fork** с feature-flagged managed KB. Personal Notes и обычные чаты не мигрируются и не изменяются. GO — отдельный modular monolith/deployable с ports-and-adapters для Git reads/writes, proposals, всех business/engineering merges, webhook ingestion и reconciliation.
2. Агент получает только typed **read/search/propose** capabilities в явном scope. Первый vertical slice ограничен create/edit одной страницы одним proposal. Agent bulk operations, subtree moves, attachment management и сложные преобразования требуют отдельных задач и contracts.
3. Агенту недоступны merge, grants, arbitrary Git push, shell/terminal, generic SQL, arbitrary filesystem, Tool Creation, arbitrary Python Tools и неаудированные custom tools. Запрет действует независимо от роли chat user и канала direct/deferred/note/automation/channel/OpenAPI/call_tool.
4. `actor`, `space`, `groups`, `tenant`, policy revisions и execution scopes принимаются только из trusted server execution context. LLM и документ не задают их. Содержимое документа является данными, не инструкцией по расширению полномочий.
5. Human apply — отдельный authenticated platform workflow, не экспортируемый как LLM tool. После cutover любой business/engineering final apply проходит GO и ADR-13; люди выполняют review/approve, но не получают прямое merge permission.
6. Только merge service identity GO имеет GitLab merge permission после cutover. Agent, connector и CI/indexer получают отдельные минимальные credentials без merge. Merge credential недоступен agent process, browser, CI/indexer и connector.
7. Protected `main`, MR-only writes и token/branch rules проверяются на стороне GitLab, а не только в GO/UI. Попытка обхода даёт ноль canonical writes. Потеря доступа между review и merge отклоняет операцию при повторной авторизации.
8. Домен GO не импортирует UI/Open WebUI internals. Компоненты взаимодействуют версионированными contracts; managed KB включается opt-in feature flag.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Merge-tool у агента для admin/owner | Удобнее automation, но роль chat user и prompt injection становятся путём privilege escalation | Категорически отклонено |
| Только скрыть privileged tools в UI | Минимальная работа, но direct/deferred/OpenAPI bypass остаётся | Отклонено как security boundary |
| Общий privileged GitLab token | Простая интеграция, но credential leakage даёт merge/push вне review | Отклонено; credentials разделены |
| Отдельный сервис на каждую операцию | Сильнее изоляция процессов, но преждевременная распределённая сложность | Отклонено; модульный GO с измеримыми seams |
| Расширенный fork Open WebUI | Меньше новых компонентов, но высокая стоимость upgrade и смешение privilege domains | Отклонено |

## Consequences

### Positive

- Один enforceable write/merge path для всех каналов.
- Компрометация модели или tool registration не даёт merge credential.
- Минимальный fork уменьшает upgrade surface и сохраняет существующий пользовательский опыт.
- Маленький proposal language делает review и тестирование предметными.

### Negative

- Нет полностью автономной публикации; требуется человек.
- Ограничение single-page снижает начальную автоматизацию массовых операций.
- Все инженерные merges также зависят от доступности GO после cutover.

### Cost

- Необходимы capability inventory, credential isolation, ports/adapters и adversarial suite по всем каналам.
- Отдельный GO требует deployment, observability, recovery и runbooks; точные затраты определяются после T00.

## Verification / T00 evidence

- **T00:** построить capability matrix реальных Open WebUI auth/grants/tools/RAG seams и GitLab protected-branch/token semantics с code references. Непроверенные возможности остаются UNKNOWN.
- На sandbox GitLab доказать: agent/connector token не может merge; прямой push в protected `main` отклонён; browser/CI не имеют merge credential; человек не выполняет final apply вне GO.
- Adversarial tests A04–A06, A17, A18: direct/deferred/note/automation/channel/OpenAPI/call_tool, prompt injection, malformed arguments, попытка подменить actor/tenant/groups и повторная генерация при apply.
- Проверить, что unsupported bulk/subtree/attachment operations отклоняются сервером, а personal Notes/ordinary chats не регрессируют.
- Каждый bypass — блокер G1; mock UI или отсутствие кнопки не засчитывается.

### T00 evidence (2026-11-07; Open WebUI `v0.13.0` `c38885a1a737da4968f157092f304f3b5481d0bf`, GitLab CE `19.5.3`)

Upstream STOP findings подтверждены статическим аудитом ([evidence/t00/openwebui-auth-audit.md](../evidence/t00/openwebui-auth-audit.md)):

- arbitrary Python `exec` в server process без sandbox: `backend/open_webui/utils/plugin.py:208-250`;
- Tool Creation через Workspace API и как built-in: `backend/open_webui/routers/tools.py:500-549`, `backend/open_webui/tools/builtin.py:3870-3908`;
- default approval mode `full`; automations/channels принудительно обходят per-call approval: `backend/open_webui/main.py:1240-1250`;
- AccessGrant имеет только `read/write`, не action capabilities: `backend/open_webui/models/access_grants.py:23-42`;
- раздельные native и legacy execution paths: `backend/open_webui/utils/middleware.py:3092-3184`, `backend/open_webui/utils/middleware.py:1102-1144`.

Обязательные adapter controls (не optional):

1. Единый deny-by-default capability resolver после deferred target resolution и до side effect в обеих точках: `execute_tool_call` и legacy `tool_call_handler`; coverage direct/deferred/note/automation/channel/OpenAPI/MCP/browser и subagents. Exposure filtering в `get_tools` — только дополнительная мера.
2. Corporate deployment отключает arbitrary Python Tools и Tool Creation; первый slice — только read/search/propose.
3. Per-call stock approval не считается capability authorization.
4. Merge service identity GO физически недоступна agent/browser/CI/connector.

GitLab-side enforcement evidence: 42 completed probes на synthetic sandbox ([evidence/t00/gitlab-capabilities.md](../evidence/t00/gitlab-capabilities.md)) — protected `main` (`push_access_level=0`), merge только Maintainer (`merge_access_level=40`), GO — единственный Maintainer, Developer/Reporter direct merge отклонён. GitLab не предоставляет atomic target-branch CAS: GO per-target serialization и durable `recovery_required` barrier по [ADR-13](ADR-013-merge-serialization-recovery.md) обязательны. Instance/project Owner bypass остаётся G0 owner decision (G0-D3) с governance/reconciliation.

**Текущее состояние:** GitLab-side enforcement доказан на synthetic sandbox; product-side deny-by-default adapter не реализован; adversarial A04–A06/A17/A18 не выполнялись. Это не production readiness и не G1 evidence.

## Related contracts

- `list_documents`, `search_documents`, `read_document`, `get_document_links`, `propose_create_document`, `propose_edit_document`, `get_proposal`.
- Human-only proposal edit/reject/merge/history/restore endpoints; `Idempotency-Key` scope actor + route + payload hash.
- Trusted execution context и `AuthzContext`; machine-readable errors и anti-enumeration.
- GO Git adapter, Identity/AuthZ adapter, proposal/MR events, protected `main` и scoped credentials.
- [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-09](ADR-009-platform-review-ux.md), [ADR-11](ADR-011-two-phase-publication.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-13](ADR-013-merge-serialization-recovery.md).
