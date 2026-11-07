# Canonical ↔ API ↔ event ↔ projection mapping

**Статус:** PROPOSED для G0. Это обязательный versioned mapping contract для T01, не утверждение о выполненной реализации. Канонические enums не подменяются похожими строками. [Integration](../integration.md), [T01 test catalog](t01-contract-tests.yaml), [database catalog](database-catalog.yaml).

## 1. Decision action, outcome и attempts

| Canonical DecisionRecord | OpenAPI | `kb_ops` / export | Обязательное правило |
| --- | --- | --- | --- |
| `action=accepted` | `DecisionCommand.action=accepted` | `decisions.action=accept` | Только accepted допускает merge attempt; action не означает `merged`. |
| `action=rejected` | `rejected` | `decisions.action=reject`; integrity-valid `DecisionResult.state=recorded`; export `publication.outcome=rejected` | MR закрыт без merge. Export outcome — производное `rejected + recorded + verified MR closure`, не новый canonical action/state. Note/tag mismatch → `invalid`, не normal closure. |
| `action=cancelled` | `cancelled` | `decisions.action=cancel`; integrity-valid `DecisionResult.state=recorded`; export `publication.outcome=cancelled` | MR закрыт без merge. Нельзя заменять cancelled на rejected/failed. Note/tag mismatch → `invalid`, не normal closure. |

| DecisionResult / export outcome | DB decision / attempt | Barrier и terminal semantics |
| --- | --- | --- |
| `recorded` accepted | `decisions.state=recorded`; `attempts=[]`, `no_merge_proven` отсутствует | Canonical note+tag durable, но merge operation ещё не зарегистрирована. До первой DB transaction crash window допускает `recovery_required/target_quarantined=true` без утверждения «merge отсутствует». |
| `recorded` rejected/cancelled | `decisions.state=recorded`; `attempts=[]`; decision-level closure evidence | Merge operation не создаётся. Verified MR closure; `recovery_required=false`, `target_quarantined=false`, `retryable=false`. |
| `merge_attempted` | `decisions.state=merge_attempted`; `attempts` nonempty; last attempt `prepared/in_flight/completed/unknown`, `no_merge_proven=false` | `recovery_required=true`, `target_quarantined=true`, `retryable=false`, no merge proof. UI «quarantined» — только это сочетание, не отдельный canonical state. |
| `merged` | `decisions.state=merged`; last real attempt `verified_merged` | Требуется merge SHA + repository/target ancestry + first/second parents + four trailers + note/tag/hash proof; `no_merge_proven=false`, barrier закрыт. |
| `failed` | `decisions.state=failed`; last real attempt `verified_not_merged` | Только `request_state=completed`, `no_merge_proven=true` и per-attempt reconciliation evidence. `retryable=true` разрешает лишь guarded recovery retry после fresh preconditions. |
| `conflicted` | `decisions.state=conflicted`; last real attempt `conflicted` | Terminal, `retryable=false`; требуется новая ProposalVersion от fresh HEAD и новое review. |
| `invalid` | `decisions.state=invalid`; accepted имеет `attempts=[]` либо real attempts; rejected/cancelled всегда `attempts=[]` | Terminal, `retryable=false`; correction — новый decision UUID с supersedes. Nonempty attempt с `no_merge_proven=false` требует quarantine; отсутствие attempts не порождает no-merge claim. |

Projection state graph сохраняет `recorded → merge_attempted → merged/failed/conflicted/invalid`. Quarantine — flags, не отдельный canonical state. Дополнительный guarded recovery edge `failed → merge_attempted` не является HTTP replay: его выполняет только recovery coordinator с новым `attempt_id`, тем же `decision_id`, exact base/proposal, fresh policy/HEAD checks после доказанных `request completed + no merge`. Повтор identical decision command создаёт ноль attempts и возвращает один текущий Git-derived outcome. `conflicted` и `invalid` такого edge не имеют.

`DecisionResult.attempts[]` и export `publication.attempts[]` содержат только реальные durable `merge_operations` для accepted, ordered oldest→newest; `attempt_id=merge_operation_id`. До первой accepted merge transaction и для reject/cancel массив пуст. Optional derived `no_merge_proven` существует только при nonempty attempts и отражает последний real attempt. Decision-level `reconciliation_evidence` хранит MR closure/retry evidence независимо от merge operations.

| `merge_operations.state` | API attempt mapping |
| --- | --- |
| `prepared` | Real attempt `request_state=prepared`, `no_merge_proven=false`; существует только после accepted `merge_attempted` transaction |
| `call_inflight` | `request_state=in_flight`, `no_merge_proven=false` |
| `unknown` | `request_state=unknown`, `no_merge_proven=false`, target quarantined |
| `verified_merged` | `request_state=completed`, `no_merge_proven=false`, decision `merged` только со всем merge proof |
| `verified_not_merged` | `request_state=completed`, `no_merge_proven=true`, decision `failed` после request completion proof |
| `conflicted` | Real attempt `request_state=completed`, decision `conflicted`, terminal |
| `invalid` | Real attempt при наличии; decision `invalid`, terminal; unknown external outcome не превращается в доказанное no-merge |

## 2. Proposal, document и actors

| Canonical/API | Projection mapping | Запрещённая подмена |
| --- | --- | --- |
| Proposal `draft/in_review/published/conflicted/rejected/cancelled/superseded` | `kb_ops.proposals.state` использует те же значения | `superseded` не переводится как `archived`. |
| ProposalView `archived` | Производное от canonical document `archived=true + archive` | Не маппируется из `kb_ops.proposals.state=superseded`. |
| Document `indexed` | Document projection входит в validated active published snapshot/profile | Не является Git canonical state и не следует из merge без pointer. |
| `author/version_author/requester` | `proposal_version_id` UUID сохраняется как stable ID каждой версии; `proposal_sha` остаётся exact content identity | Disposable sequence или только `(proposal_id,proposal_sha)` не заменяет required UUID. |
| `actor_type=human/agent/connector` | Совпадает в ProposalRecord/API/projection | Bot/service credential не замещает principals. |
| Authz `internal_ci/service` | Operational actor `service` + verified `service_id` | Не становится canonical ProposalRecord actor. Event `webhook` тоже operational service identity, не human. |

## 3. Index, cutover и source states

| Canonical/API | Projection mapping |
| --- | --- |
| Index `requested/resolving/building/validating` | `index_runs` то же state; descriptor отсутствует или строится, serving false. |
| Index `ready` | `index_runs.state=ready_to_publish` + descriptor `snapshots.state=validated`; exact/semantic hashes и closure готовы, pointer ещё не active. |
| Index `active` | `index_runs.active` + `snapshots.active` + active pointer; только `purpose=published`, `is_preflight=false`, `serving_allowed=true`. |
| Index `superseded/failed/dead_letter` | Одноимённые run states; descriptor superseded/failed либо отсутствует; active pointer не ссылается на него. |
| Cutover `freeze_pending` | `space_cutovers.state=prepared`. |
| Cutover `frozen` | `frozen`. |
| Cutover `protected` | `protecting` после подтверждённых protected tag/MR-only rules; до `preflight`. |
| Cutover `preflight` | `preflight`; inactive full preflight ready, но published descriptor ещё не активирован. |
| Cutover `activating` | `activating`; separate published non-preflight descriptor и pointer уже validated/active, пользовательский доступ ещё false. |
| Cutover `activated` | `active`; user access true только после pointer и GO activation. |
| Cutover `failed/conflicted` | Одноимённые states; никакого activation claim. |
| Source `observed/seen_durable/no_op/proposal_pending/merged/rejected/conflicted/tombstone/retry/dead_letter` | Одноимённые `source_sync_states.sync_state` и `kb.source.sync.changed.v1`; seen/proposed/merged version+hash существуют только парами. `proposal_pending` требует proposed pair + outstanding ID/SHA; `merged` требует merged pair + verified merge SHA и `outstanding_proposal_id/outstanding_proposal_sha=null`; все non-pending states очищают outstanding pair. |
| `live_operational` | Только `readLiveOperational` typed result со `snapshot_time`; не имеет `source_sync_states`, canonical document, MR/index/cursor mapping. |

- Incremental canonical `ready/active` требует nonempty `closure.equivalence_evidence`: distinct full run+snapshot в canonical `ready/active`, `validated_at`, complete closure, `missing_inputs=[]`, exact+semantic hashes и совпадение Space/repository/target/main SHA/generation/profile/closure hash. DB `ready_to_publish` соответствует canonical ready. Requested/failed/empty evidence не является prerequisite.
- Cutover `preflight/activating/activated` связывает separate preflight/published run+snapshot IDs, same SHA и обязательные `preflight_validated_at`/`published_validated_at`; prerequisite requested/failed/unvalidated preflight запрещён.

## 4. Policy, paths и stable links

- `authz-context-v2.space_scopes[]` является полным per-Space mapping: `{space_id,repository_id,policy_bundle_id,access_policy_revision,approval_policy_revision,group_snapshot,revocation_epoch}`. Projection обязана сохранять запись per `(context_id,space_id)` и `revocation_epoch`; один top-level bundle/snapshot для нескольких Spaces запрещён. Cursor хранит весь набор и actor epoch.
- `AccessPolicyChanged.changes[]` маппируется независимо per Space. `affected_space_ids` с одним общим bundle больше не используется.
- Canonical policy/approval paths абсолютные NFC. Lossless boundary mapping в repository-relative projection: `/` ↔ пустой prefix только для policy scope; `/pricing` ↔ `pricing`; `/approval-policy.yaml` ↔ `approval-policy.yaml`. Reverse mapping добавляет ровно один `/`. Document paths изначально relative и никогда не пустые/absolute.
- До mapping выполняются NFC normalization и проверки отсутствия `\`, control chars, пустых/`.`/`..` segments, duplicate/trailing separators. Duplicate normalized approval prefixes и rule IDs отклоняются. `/` vs `/pricing` выбирает `/pricing` только на segment boundary; identical/NFC/NFD duplicates invalid.
- Front matter v2 `links[]`, import/export `documentLink`, API `DocumentLinkEntry` и `document_links.target_document_id` сохраняют один UUID. `resolved` требует одновременно target projection и тот же target UUID в same Space/snapshot; swapped ID — `invalid`, не resolved.

## 5. Front matter, DocOps и export

- `document-front-matter-v2` — versioned change, добавляющий canonical `links[]` и `valid_until`; `origin` остаётся provenance и равен outer `ownership_mode`. `access` и `live_operational` запрещены.
- `docops-review-metadata-v1` — projection, не второй канон: `document_id + document_revision_sha + valid_until + provenance` должны совпадать с front matter. `scheduled` = ещё не expired, `due` = expired по server UTC date, `removed` = `review_required=false + valid_until=null`.
- `archived=true` iff `archive` present. Restore — reviewed revision `archived=false` без archive. Replacement/descendant semantics проверяются semantic validator, а не только JSON Schema.
- API `ExportInput.format` и manifest `format` оба равны `git_clone_with_manifests`. `ExportJob.ready` допустим только при `closure.complete=decisions_complete=assets_complete=authorization_complete=true`, `missing=[]` и все assets `exported`. `incomplete/failed` не выдают complete claim.
- Export `documentEntry.valid_until` обязателен и равен canonical front-matter-v2 значению на exact document revision; он входит в documents manifest hash/restore roundtrip.
- Accepted recorded/merge_attempted/failed/conflicted/invalid экспортируются без merge, но с explicit publication+real attempts+recovery evidence. `recorded accepted` и rejected/cancelled имеют `attempts=[]` и не получают synthetic no-merge claim. Только `merged` содержит merge proof. Missing/rejected assets не имеют выдуманного `exported_object_sha256` и делают export incomplete.
