# GitLab integration contract

**Статус:** PROPOSED собственный GO↔GitLab protocol для G0. Главный authority: [ARCHITECTURE-SPINE.md](../architecture-spine.md), AD-1–AD-3, AD-5–AD-11, AD-13–AD-16. Общий lifecycle: [integration.md](../integration.md).

GitLab version/edition, exact API routes/fields, token types, note mutation/audit semantics, protected annotated tags, merge commit message/trailers, webhook authenticity/replay fields и metadata export — **UNKNOWN до T00**. Ниже не утверждается наличие конкретной upstream capability. Недоступная capability фиксируется BLOCKED/design review, не заменяется предполагаемым поведением.

## 1. Обязательная T00 capability matrix

| Capability | Что доказать на synthetic sandbox | Если не подтверждено |
| --- | --- | --- |
| Exact-SHA reads | Tree/blob/history/MR/diff читаются по полному SHA; ancestry и first/second parents доступны | G0 stop для SHA-safe canonical/retrieval |
| Exact-SHA real merge | GO может применить reviewed source SHA к expected target с настоящим merge commit, без squash/rebase/FF | G0 stop; не имитировать publication через push |
| Merge metadata | Custom `Decision-ID`, `Decision-Note-ID`, `Decision-Hash`, `Approved-by` сохраняются и читаются после timeout/restart | G0 stop для Decision integrity |
| MR notes | GO создаёт structured note; стабильный note ID, mutation/audit permissions и metadata export проверены | Нельзя называть note физически immutable; требуется design review |
| Protected annotated tags | `kb-decisions/<uuid>` создаётся на arbitrary `proposal_sha`, защищён от update/delete, включается в clone/fetch/export | G0 stop для accepted/rejected/cancelled durability |
| Merge-only-GO | Direct push в protected target закрыт для людей/bots; только merge service identity GO имеет merge | G1 blocker; UI hiding не засчитывается |
| Scoped credentials | Proposal/agent/connector/CI identities не имеют merge; CI read-only exact main | G1 blocker |
| Webhooks/audit | Authenticity/replay проверяется; MR/main/audit достаточны для target-wide reconciliation | Недоказуемый timeout остаётся quarantined |
| Metadata portability | MR notes/metadata, refs/tags, merge trailers и links экспортируются с проверяемыми hashes | Полный restore не объявляется |

## 2. Repository и credential perimeter

В MVP один repository соответствует ровно одному Space. Protected target, refs, blobs/history, policies, agent/connector/CI credentials, cutover, index generations и clone/export имеют общий периметр. Несколько ACL Spaces в одном repository запрещены.

- `space_id` — stable lowercase slug; `repository_id` — отдельный configured identifier. Naming/group layout/provisioning UNKNOWN T00.
- Business users не имеют GitLab user records. Engineering GitLab RBAC и CODEOWNERS остаются engineering-only.
- Proposal/write identity GO отделена от merge service identity. Agent, connector, CI, browser и general proposal adapters не получают merge credential.
- После cutover engineering final apply тоже проходит GO. GitLab MR UI может использоваться для engineering review, но не для side merge.
- Direct post-merge CI commits запрещены. Производный `INDEX.md` — artifact либо часть того же reviewed MR.

## 3. Cutover state machine

| State | Вход / обязательные действия | Разрешённый выход |
| --- | --- | --- |
| `freeze_pending` | Dry-run и human sign-off готовы; пользовательский доступ и published index отсутствуют | Включить write freeze |
| `frozen` | Проверить `HEAD == cutover_sha`; зафиксировать CutoverRecord | Создать protected tag и MR-only protections; mismatch → `failed` |
| `protected` | Direct push/merge закрыт для всех, кроме GO merge identity | Запустить full inactive preflight exact SHA |
| `preflight` | Full exact+semantic, dependency closure, eligibility, attachments/media, negative ACL checks; `snapshot_sha=cutover_sha`, serving запрещён | Создать отдельные published run+descriptor с новыми IDs и full validation на том же SHA |
| `activating` | Separate published non-preflight descriptor validated и pointer active; preflight остаётся immutable non-serving | Per-Space/profile CAS pointer; пользовательский доступ ещё закрыт |
| `activated` | Published pointer уже существует и соответствует exact cutover SHA; run/snapshot IDs отличаются от preflight | GO активирует Space и пользовательский доступ |

Повтор по Space+`cutover_sha` возвращает/продолжает существующий CutoverRecord с тем же idempotency context. При изменении HEAD прежний record нельзя активировать: нужен новый sign-off, CutoverRecord и preflight. До `activated` retrieval/user access denied. После cutover rollback — reviewed/revert MR, не history rewrite.

Controlled bulk push разрешён только до этой state machine, в unpublished `main`, без пользователей/published index и после dry-run/data barriers. Это не постоянный write path.

## 4. ProposalRecord и MR metadata

Каждая immutable ProposalVersion связывается с `(proposal_id,proposal_version_id,proposal_sha)` и [ProposalRecord](proposal-record.schema.json).

Обязательные связи:

- exact `base_sha` = target HEAD reviewed diff;
- exact `proposal_sha` = source branch HEAD;
- `author_stable_id` — инициатор исходного proposal;
- `version_author_stable_id` — создатель конкретной версии;
- `requester_stable_id` — человек-requester, не service account;
- `actor_type`, trusted optional `run_id`, rationale/evidence;
- idempotency key/payload hash и server `created_at`.

Изменение текста, reviewer edit или rebase создаёт новый commit, version ID и ProposalRecord. Старый approval не переносится. `kb_ops` хранит только projection. Физическое MR metadata representation, append-only/audit/export properties и attributed commits без business GitLab users — T00 capabilities; ProposalRecord не должен изменять `proposal_sha`.

## 5. DecisionRecord: note + protected annotated tag

До применения accept/reject/cancel GO создаёт [DecisionRecord](decision-record.schema.json) с action, human stable actor, exact revisions, rationale/evidence, policy bundle+revisions, payload/record hashes и optional supersedes.

PROPOSED deterministic serialization:

1. Удалить `record_sha256` из объекта.
2. Сериализовать остаток JCS RFC 8785 в UTF-8.
3. Вычислить SHA-256 и вставить `record_sha256`.
4. Записать **один и тот же полный JSON** в structured MR note и annotated tag `kb-decisions/<decision_id>` на `proposal_sha`.

`note_id` не входит в сам record, поскольку назначается GitLab после note creation; он сохраняется в projection/export и merge trailer. Отсутствие note/tag, разные bytes/hash, неверный tag target или superseded/mismatched linkage делают decision `invalid`. Исправление создаёт новый UUID с `supersedes_decision_id`, не mutation старого JSON.

| Action | GitLab outcome | Export outcome |
| --- | --- | --- |
| `accepted` | `recorded → merge_attempted → merged/failed/conflicted/invalid`; real merge только после всех checks | Explicit publication outcome+real attempts; merge parents/trailers/proof только для `merged`, иначе attempt+recovery evidence |
| `rejected` | MR закрыт без merge, `main` unchanged; DecisionResult `recorded` | Derived export outcome `rejected` + note + tag + closure evidence; merge отсутствует |
| `cancelled` | MR закрыт без merge, `main` unchanged; DecisionResult `recorded` | Derived export outcome `cancelled` + note + tag + closure evidence; merge отсутствует |

Quarantine не является новым canonical state: это `merge_attempted + recovery_required + target_quarantined` либо recovery flags поверх unresolved `recorded accepted`. `attempts[]` содержит только реальные merge operations accepted; `recorded accepted` после note+tag до первой DB transaction имеет `attempts=[]` и не получает `no_merge_proven`, rejected/cancelled не создают merge operation. `failed` допустим только после completed request и Git-derived no-merge evidence последней real attempt; guarded recovery retry создаёт новый attempt с тем же decision ID после fresh preconditions. Identical command replay создаёт ноль attempts и возвращает один текущий outcome. `conflicted/invalid` terminal.

## 6. Merge serialization и apply

1. Human decision поступает только из authenticated browser+CSRF. `Idempotency-Key == decision_id`.
2. GO получает advisory lock `(repository_id,target_branch)` с owner/fencing token.
3. Под lock выполняются fresh group/approver/path/policy/session checks; approver отличается от author/version_author/requester.
4. Проверяются MR open, exact source HEAD, target HEAD=`base_sha`, полный preview, отсутствие более новой ProposalVersion и `recovery_required`.
5. До external call сохраняются note+tag как `recorded accepted` с `attempts=[]`; затем одна DB transaction устанавливает `merge_attempted`, создаёт первую реальную merge operation и durable per-target `recovery_required`.
6. Merge service identity GO выполняет exact-SHA merge с required trailers. Squash, automatic rebase, fast-forward, generated-on-apply content и automatic conflict merge запрещены.
7. GO независимо от response читает target. Merge считается подтверждённым только если commit в target ancestry имеет first parent=`base_sha`, second parent=`proposal_sha`, четыре верных trailer и совпадающие note/tag/actor.
8. Replay `decision_id` или `(repository_id,target_branch,proposal_sha)` возвращает тот же текущий Git-derived result и создаёт ноль attempts. Только conclusive `failed` после request completion+no-merge может получить `retryable=true`; recovery coordinator затем создаёт новый attempt с тем же decision ID и fresh preconditions.
9. Barrier снимается только после conclusive target-wide verification и отсутствия unresolved attempts. Index запускается отдельно.

`failed` не выставляется по timeout или отсутствию DB row. Non-error response без найденного/проверенного commit также не является `merged`; `merged` требует merge SHA и полного parent/trailer/note/tag/hash proof. `conflicted` и `invalid` terminal и не retryable.

## 7. Recovery и fencing

Полная обязательная таблица crash points приведена в [integration.md §7](../integration.md). Operational rules GO:

- Новый owner не предполагает отмену старого external request после lock loss. Он проверяет DB barrier и Git unresolved accept records перед любым новым merge.
- Crash между note/tag и DB transaction закрывается обнаружением unresolved accept при следующем target reconciliation.
- После `merge_attempted` все новые merges target блокируются, даже если lock перешёл другому owner.
- Reconciliation проверяет target ancestry, MR state, note+tag/hash, tag target, first/second parents, trailers и Approved-by.
- До первой DB transaction accepted остаётся `recorded` с `attempts=[]` и recovery/quarantine flags без no-merge claim. При доказанном отсутствии external call recovery очищается без synthetic attempt. При наличии real external attempt доказанные request completion + no-merge переводят последнюю operation в `failed`; лишь затем guarded recovery retry продолжает с новым attempt ID, тем же `decision_id` и fresh preconditions. Недоказуемый outcome остаётся `merge_attempted`+quarantined с `retryable=false`.
- Полная потеря `kb_ops` включает global bootstrap merge freeze. Targets открываются по одному после conservative Git-derived rebuild; отсутствие attempt row не является отрицательным доказательством.

## 8. Webhook ingestion → CI

1. Adapter проверяет authenticity/replay и передаёт [webhook event](events.yaml) с verified event ID, repository и payload hash. Payload actor/revision не считается доверенным proof.
2. GO выполняет idempotent inbox write и читает GitLab current target state.
3. GO фиксирует observed exact `main_sha` и ancestry generation, затем отправляет `kb.index.requested.v1`.
4. CI читает exact snapshot read-only. Merge/push/archive/delete, `AccessPolicyChanged` и `AttachmentChanged` используют общий run/reconciliation контур.
5. Exact+semantic run валидируется до single-writer pointer publication. Публикация сериализуется per Space/profile с CAS по expected current fence/latest ancestry/validated run; stale owner обновляет ноль rows. Late run не откатывает pointer; SHA sorting запрещена.
6. Duplicate/out-of-order/lost events обрабатываются dedupe/retry/dead-letter и periodic HEAD reconciliation. CI outage не меняет канон и не откатывает merge.

Webhook/CI credentials не имеют merge/index bypass: webhook не управляет pointer напрямую, CI не меняет `main`/grants.

## 9. Clone, refs, decisions и assets

[export-manifest-v2](export-manifest.schema.json) обязателен для полного Space export:

- `refs[]` содержит full ref object SHA, peeled target и SHA-256 raw exported object bytes. Для annotated tag `object_sha` — tag object, `peeled_sha` — proposal commit; decision ref protected=true.
- `decisions[]` содержит accepted/rejected/cancelled records, MR note ID/body/`canonical_json_sha256`/metadata ref и tag object/target/raw content с тем же canonical JSON hash. `body_sha256`, `record_sha256` и canonical full-record hash различаются.
- Каждый entry имеет explicit publication outcome+real attempts+recovery evidence. Accepted recorded/merge_attempted/failed/conflicted/invalid не требует merge; recorded accepted и rejected/cancelled имеют `attempts=[]` без synthetic no-merge attempt/merge operation. Только merged содержит merge commit SHA, repository/target ancestry, first/second parents, raw commit hash, note+tag/canonical JSON proof и все trailers. Rejected/cancelled имеют verified decision-level closure и не содержат merge.
- `documentEntry.valid_until` обязателен и равен canonical front-matter-v2 на exact document revision; restore roundtrip сохраняет значение.
- `assets[]` содержит immutable storage ref, object/version/content hash/size/media/source ref и export status. `exported_object_sha256` обязателен только для exported и равен attachment hash/bytes; missing/rejected не имеет фиктивного hash.
- `closure` содержит hashes refs/documents/decisions/assets/policies/repository tree. Complete/ready требует `decisions_complete=assets_complete=authorization_complete=true`, missing=[] и все assets exported; любой missing/rejected объект или batch делает export incomplete.

Обычный clone default branch недостаточен: protected decision refs и MR notes/metadata должны быть получены явно. Manifest дополняет, но не заменяет canonical note+tag. Full export требует export permission на всю Space history; secrets/private chats не включаются.

## 10. Outage и обязательные evidence

При GitLab outage обходная canonical write запрещена. Read-from-index stale mode по умолчанию выключен и требует отдельного ADR. Merge timeout оставляет target quarantined; CI/index lag не меняет Git outcome.

После T00 требуются sanitized sandbox results по concurrent apply, stale base, bot-no-merge, no-direct-push, all-channel bypass, note/tag corruption, every integration §7 crash point, DB loss, webhook loss/duplicates, cutover replay и clone+manifests restore. Реальные проверки сейчас не выполнялись; mocked GitLab не является integration PASS.
