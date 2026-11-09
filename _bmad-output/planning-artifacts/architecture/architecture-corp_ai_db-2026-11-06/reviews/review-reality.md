# Technology reality-check — third pass

**Дата:** 2026-11-06 13:35 UTC  
**Проверенный артефакт:** актуальный `../ARCHITECTURE-SPINE.md`  
**Verdict:** **PASS — CRITICAL/HIGH blockers не обнаружены.**

Все три blocker finding второго прохода закрыты на уровне architecture design. Это не вердикт VERIFIED для конкретных релизов: GitLab/Open WebUI versions, GitLab edition и точные API/config semantics остаются **T00 UNKNOWN** и обязаны пройти target integration gates.

## Границы проверки

- Это повторный desk review актуального spine и официальной документации, не integration test. Spine не изменялся этим review.
- Online docs подтверждают только current capability surface. Они не используются для утверждения возможностей ещё не выбранного GitLab/Open WebUI release.
- T00 checks ниже являются остаточными verification conditions, а не CRITICAL/HIGH design findings.

## Закрытие прежних blockers

### RR2-01 — CLOSED: persistent target-wide recovery barrier закрывает late in-flight handover

**Location:** `ARCHITECTURE-SPINE.md:60`, `ARCHITECTURE-SPINE.md:66`.

До внешнего merge call GO теперь в одной DB transaction устанавливает `merge_attempted` и per-target `recovery_required`. Barrier блокирует **все новые merges target** после crash/fencing до conclusive target-wide reconciliation. Timeout не снимает barrier, а недоказуемый outcome остаётся quarantined.

Это закрывает прежний путь «GO A отправил merge и упал → GO B выполнил другой merge → поздний A применился поверх нового base»: пока исход A недоказан, B не имеет права выполнять merge. Advisory lock продолжает сериализовать рабочие операции GO, но безопасность crash recovery больше не зависит от предположения, что lock отменяет уже отправленный HTTP request [P02].

**Остаточная проверка, не blocker:** fault-injection до/после request, timeout, lock handover и полная потеря projection. Rebuild обязан консервативно восстанавливать quarantine для accept DecisionRecords без проверенного terminal merge, а не трактовать отсутствие merge как доказанный `failed`.

### RR2-02 — CLOSED: protected annotated decision tag является Git-native anchor для accept/reject/cancel

**Location:** `ARCHITECTURE-SPINE.md:30`, `ARCHITECTURE-SPINE.md:66`, `ARCHITECTURE-SPINE.md:202`.

DecisionRecord теперь представлен единым canonical JSON в двух местах:

- MR note — append-only API/UI representation;
- protected annotated tag `kb-decisions/<decision_id>` на `proposal_sha` — полный Git-native durability anchor для accept/reject/cancel, входящий в clone.

Это устраняет зависимость rejected/superseded history от self-hash в изменяемой note и от наличия merge commit. Tag сохраняет полный JSON и делает rejected `proposal_sha` reachable при clone/export; missing/mismatched note или tag переводит decision в `invalid`. Исправление через новый `decision_id` со `supersedes_decision_id` не перезаписывает прежний anchor.

Current GitLab Tags API документирует создание annotated tag через `message` на заданный `ref` [G12]. Protected tags поддерживают exact/wildcard rules и защиту от accidental update/deletion [G13]. Git annotated tag содержит tagging message [GIT03], а обычный clone по умолчанию включает tags [GIT04]. Конкретная целевая GitLab version/edition, effective protection и exact API response semantics остаются T00 UNKNOWN.

**Остаточные проверки, не blockers:**

- Pre-provision `kb-decisions/*` protection до первого decision; synthetic agent/human не может overwrite/delete через UI, API или Git transport. Current docs разрешает privileged Allowed-to-create + Maintainer удалять protected tag через GitLab, поэтому effective role policy входит в проверку [G13].
- Для annotated tag API `target` может содержать ID самого tag object, а не commit ID; reconciliation обязан peel tag object и проверить `proposal_sha`, а не сравнивать `target` напрямую [G12].
- Каноническая JSON serialization и область вычисления `record_sha256` должны быть versioned/deterministic; note body normalization не должна менять parsed canonical payload или запускать quick actions [G01].
- Clone/export не использует `--no-tags`, shallow/filtered режим, теряющий decision refs; restore проверяет tag object, annotation JSON и полный proposal/blob closure [GIT04].

### RR2-03 — CLOSED: merge shape и parentage закреплены явно

**Location:** `ARCHITECTURE-SPINE.md:30`, `ARCHITECTURE-SPINE.md:66`, `ARCHITECTURE-SPINE.md:102`.

Squash, automatic rebase и fast-forward запрещены. Reconciliation больше не признаёт `merged` по состоянию MR или наличию произвольного merge commit: требуются first parent = `base_sha`, second parent = `proposal_sha`, а также совпадение trailers/note/tag.

Это исключает подмену approved объекта через squash/server-side rebase, риски которых видны в current merge-methods docs [G02]. Commits API предоставляет `parent_ids` и полное message для проверки contract [G03], но точное поведение pinned GitLab release и сохранение trailers остаются T00 UNKNOWN.

**Остаточная проверка, не blocker:** project/group settings не могут включить squash, automatic rebase или fast-forward; merge с любым другим parentage/trailer становится `invalid/conflicted`, а не `merged`.

## Статус остальных прежних findings

| Область | Итог third pass |
|---|---|
| **Все merges через GO / merge-only-GO** | Необходимая граница зафиксирована; effective edition, protected branch/tag rules и token permissions проверяются T00 [S13, G04, G05, G13]. |
| **Retry/idempotency** | `decision_id`, `(repository_id, target_branch, proposal_sha)`, note/tag reconciliation и persistent recovery barrier образуют согласованный contract. |
| **Metadata export** | Explicit refs + decision tags + decisions/assets manifests + snapshot-closure restore покрывают accepted и rejected decisions; custom exporter остаётся T00 verification [G09, G10]. |
| **Open WebUI identity/revocation** | Stable attributes, nested groups, StartTLS/LDAPS и adapter seams не выдаются за подтверждённые факты; `AuthzContext` и owner-approved revocation SLO сохранены, target checks обязательны [O01–O03, O07, O08]. |
| **Model connections/egress** | Inventory/allowlist всех providers/fallback нормативны; direct/task/passthrough/retry configuration проверяется на pinned release [O09–O11]. |
| **RAG/ACL reuse** | Payload ACL, stale rejection и adapter/stop path зафиксированы; pgvector остаётся deferred до ACL-aware benchmark [S02, S06, O12]. |
| **PostgreSQL schemas/advisory locks** | Schema ownership отделён от runtime verification; advisory lock используется по назначению, а canonical crash safety обеспечивает persistent recovery barrier [P01, P02]. |
| **Git ancestry** | Использование ancestry вместо lexicographic SHA корректно; candidate/current-main и history-rewrite проверки остаются обязательными [GIT01]. |
| **Protected cutover tag** | Остаётся закрытым в AD-3; decision tags теперь имеют отдельный T00 protection contract. |

## Обязательные T00/integration gates после design PASS

1. **Decision tag fault matrix:** create/read timeout, duplicate `decision_id`, missing tag, moved tag, wrong annotation, mismatched note, rejected/cancelled/superseded recovery после потери GO projection.
2. **Recovery fault matrix:** crash до transaction, после transaction до request, после request до response, timeout, delayed request после handover и database rebuild; любой недоказанный target остаётся quarantined.
3. **Merge shape:** exact first/second parent, полные trailers и note/tag/hash совпадение; squash/rebase/fast-forward negative tests.
4. **Protection and tokens:** synthetic non-GO identities не могут merge/push/overwrite/delete protected refs через UI, API или Git transport; учитываются edition, role, group/wildcard rules и token type.
5. **Portability:** clone и restore сохраняют все decision refs, annotations, rejected proposal commits/blobs и MR metadata; snapshot closure проверен машинно.
6. **Pinned upstream:** stable identity, revocation, payload ACL/stale rejection, provider/fallback inventory и RAG adapter seam подтверждаются на выбранных commits либо активируют documented adapter/stop path.

## Источники

### GitLab / Git

- **[S11]** Merge Requests API: https://docs.gitlab.com/api/merge_requests/
- **[S13]** Protected branches: https://docs.gitlab.com/user/project/repository/branches/protected/
- **[G01]** Notes API и body normalization: https://docs.gitlab.com/api/notes/
- **[G02]** Merge methods, squash и automatic rebase: https://docs.gitlab.com/user/project/merge_requests/methods/
- **[G03]** Commits API: https://docs.gitlab.com/api/commits/
- **[G04]** Protection rules and permissions: https://docs.gitlab.com/user/project/repository/branches/protection_rules/
- **[G05]** Protected branches API: https://docs.gitlab.com/api/protected_branches/
- **[G09]** Project import/export: https://docs.gitlab.com/user/project/settings/import_export/
- **[G10]** Project import/export API: https://docs.gitlab.com/api/project_import_export/
- **[G12]** Tags API: https://docs.gitlab.com/api/tags/
- **[G13]** Protected tags: https://docs.gitlab.com/user/project/protected_tags/
- **[GIT01]** Git ancestry (`merge-base --is-ancestor`): https://git-scm.com/docs/git-merge-base
- **[GIT02]** Git trailers: https://git-scm.com/docs/git-interpret-trailers
- **[GIT03]** Annotated tag objects: https://git-scm.com/docs/git-tag
- **[GIT04]** Clone/tag and mirror semantics: https://git-scm.com/docs/git-clone

### Open WebUI / PostgreSQL / pgvector

- **[O01]** LDAP: https://docs.openwebui.com/features/authentication-access/auth/ldap
- **[O02]** SSO/OIDC: https://docs.openwebui.com/features/authentication-access/auth/sso/
- **[O03]** SCIM: https://docs.openwebui.com/features/authentication-access/auth/scim
- **[O07]** Roles: https://docs.openwebui.com/features/authentication-access/rbac/roles
- **[O08]** Hardening/revocation: https://docs.openwebui.com/getting-started/advanced-topics/hardening
- **[O09]** Model connections: https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/
- **[O10]** Direct Connections: https://docs.openwebui.com/features/chat-conversations/direct-connections
- **[O11]** Task Models: https://docs.openwebui.com/features/administration/task-models
- **[O12]** RAG/External Knowledge Sources: https://docs.openwebui.com/features/chat-conversations/rag/
- **[S02]** Knowledge: https://docs.openwebui.com/features/workspace/knowledge/
- **[S06]** pgvector, выбор остаётся deferred: https://github.com/pgvector/pgvector
- **[P01]** PostgreSQL schemas: https://www.postgresql.org/docs/current/ddl-schemas.html
- **[P02]** PostgreSQL advisory locks: https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS
