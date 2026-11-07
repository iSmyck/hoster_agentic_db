# Managed inference integration contract

**Статус:** PROPOSED для G0. Authority: [ARCHITECTURE-SPINE.md](../architecture-spine.md), AD-5, AD-11, AD-14–AD-16. Общие границы: [integration.md](../integration.md).

Open WebUI commit/model connection seams, hoster.ai studio endpoints/model IDs, protocol capabilities, embedding dimensions, extraction/reranker/OCR/vision models, retries и offline assets — **UNKNOWN до T00/owner configuration**. Реальные endpoints и credentials в контракт не включаются.

## 1. Managed model connection boundary

Open WebUI upstream model connection владеет provider credentials, approved model config, retries/timeouts/cancellation и streaming composition. Agent получает только bounded tools из [agent-tools.yaml](agent-tools.yaml), но не provider credential, arbitrary model connection admin или human apply context.

Provider inventory должен явно перечислять:

| Назначение | Обязательные attributes |
| --- | --- |
| Chat/answer | Connection ID, approved model config, data profile, tool/streaming capability |
| Task/title/summarization | Тот же inventory; auxiliary calls не обходят profile |
| Extraction/conversion | Approved route/model/config/assets и provenance hashes |
| Embeddings | Connection/model/version/dimensions/chunking profile, index profile linkage |
| Reranking | Approved provider/model/config и bounded candidates |
| OCR/vision | Approved provider/model/assets, media class и human verification gate |
| Fallback, если разрешён | Только явно inventoried route в том же data profile и owner-approved config; не implicit provider behavior |

Все providers/fallbacks входят в allowlist и egress policy. Неучтённые provider credentials в CI, connector или agent запрещены. Offline model assets готовятся заранее; cold offline startup проверяется отдельно.

## 2. Data profiles

| Gate | `strict` — default | `pii_permitted` |
| --- | --- | --- |
| Owner | Владелец источника обязателен до intake/inference | Обязателен |
| Legal/admission | Owner checklist до conversion + post-conversion scan | Documented legal basis до import + усиленные access/retention rules |
| PII hits | Каждое срабатывание разбирает человек; unresolved → reject/на правке | Разбираются по клиентской policy; silent accept запрещён |
| Inference perimeter | Только approved providers внутри selected profile | Только собственный согласованный hoster.ai/client perimeter |
| External PII egress | PII-содержащий input отклоняется или возвращается на очистку до admission; unresolved hit не публикуется, а сам профиль не разрешает такой egress | Категорически запрещён |
| Fallback | Unplanned fallback запрещён | Особенно запрещён для extraction/OCR/embeddings/reranking |
| Logs/export | Raw private content и PII snippets не пишутся | То же; approved export регулируется отдельными rights |

Auto scanner — вспомогательный сигнал, не доказательство отсутствия PII. Документ/source text не получает полномочия изменить profile, provider, scopes или fallback.

## 3. No unplanned fallback

1. Каждый call выбирает один approved connection/model/profile из inventory.
2. Timeout, 4xx/5xx, malformed response или unavailable primary не разрешает автоматический переход к другому provider/model/perimeter.
3. Retry возможен только в пределах того же approved route, bounded policy и operation idempotency semantics.
4. Альтернативный route должен быть заранее описан в inventory, соответствовать data profile/egress/legal basis и явно выбираться configuration. Скрытый SDK fallback отключается/проверяется.
5. Отсутствие approved route даёт sanitized `UPSTREAM_UNAVAILABLE`/BLOCKED, не silently degraded external processing.

Это распространяется на chat, titles, summaries, extraction, embeddings, reranking, OCR/vision и evaluation graders.

## 4. Agent read/search/propose flow

1. Server создаёт bounded run с trusted `requester_stable_id`, `run_id`, AuthzContext и effective scope.
2. Agent вызывает typed read/search/links с limits/cursor. Retrieval/GO авторизует каждый result **до** model payload.
3. Selected canonical revision читается через GO. Citations содержат stable document ID, full document revision и section/range.
4. Модель получает минимально необходимый authorized context. Документный текст/tool output маркируется как недоверенные данные, не instructions.
5. `propose_create_document`/`propose_edit_document` принимает exact base, single-page change, rationale/evidence и idempotency key. GO привязывает operation к trusted actor+route+payload.
6. GO создаёт branch/MR/ProposalRecord с requester/version_author/run attribution. Agent не получает accept/reject/merge/grants/export.
7. Stale base/ambiguous patch возвращает machine error; новая работа создаётся от fresh HEAD. Apply никогда не вызывает LLM для повторной генерации.
8. Human review видит точный diff/rationale/evidence и принимает решение отдельным browser/session+CSRF workflow.

Prompt injection, admin/owner chat role, deferred/note/native/temporary chat, automation/channel/OpenAPI/call_tool и malformed tool args не расширяют capability.

## 5. Tool calling и streaming behavior

После T00 на pinned Open WebUI + реальном approved endpoint проверяются:

- sequential и parallel read-only/propose calls с сохранением trusted run correlation;
- streaming partial arguments и сборка только после typed schema validation;
- malformed JSON, unknown fields, unsupported operation, oversized payload и repeated headings;
- cancellation, timeout, disconnect/retry без повторной mutation с новым key;
- revocation во время stream: закрытие subscription и отсутствие новых payloads;
- citation correctness/no-answer/abstention, но deterministic ACL/merge tests отдельно от LLM judge;
- TTFT и full response отдельно, с corpus SHA/config/model/tool-schema versions.

Partial/malformed arguments никогда не исполняются как shell/Python/SQL и не вызывают merge. Streaming UI не показывает optimistic `merged`; только Git-derived GO result подтверждает publication.

## 6. Indexing/extraction inference

1. CI/index worker получает exact immutable snapshot/profile и approved connection из inventory.
2. Embedding/chunking/reranking semantics образуют независимый `index_profile_version`; dimensions/model config не hardcoded.
3. Extraction/OCR/vision provenance включает route/config/model/assets и original/output/loss hashes.
4. Worker не использует собственный неучтённый credential или fallback. Raw payload ограничен authorized exact input и profile.
5. Смена model/dimensions/chunking создаёт новый shadow profile и full validated build; destructive live rebuild запрещён.
6. Critical/handwritten media без human transcription/verification не отправляется как подтверждённый index fact. Automatic descriptions маркируются и ссылаются на original.
7. Provider failure оставляет run failed/retryable/dead-letter, не активирует partial index и не меняет canonical merge.

## 7. Live operational reads

`live_operational` использует typed read-only adapter, не inference по устаревшему wiki report:

- operation allowlist, filters и bounds задаются server contract;
- AuthzContext и source credential проверяются отдельно;
- result содержит `snapshot_time`, source version/record ID и freshness/limits;
- payload повторно авторизуется до browser/model;
- timeout не маскируется stale данными как current fact;
- Git page, MR, embedding/index entry и merged cursor автоматически не создаются.

Generic arbitrary source query/write и source-provided actor/grants не поддерживаются.

## 8. Security и observability

Logs/traces содержат request/run/tool/proposal IDs, approved connection/profile IDs, sanitized result codes, latency/retry/cancel metrics, но не prompts, raw documents/private queries/evidence/PII snippets/provider payloads/tokens/bind secrets. Evaluation datasets/results проходят тот же data barrier.

Release evidence фиксирует corpus snapshot SHA, code/config/model/tool-schema versions и dataset. Retrieval quality, factual support, citation correctness и abstention оцениваются отдельно; LLM judge не заменяет deterministic security.

## 9. Integration status и stop conditions

Без реального согласованного hoster.ai endpoint и credentials интеграционная проверка — **BLOCKED**. Mocked streaming/tool calls не являются PASS. Отсутствие способа ограничить tool registrations, применить ACL до model payload, инвентаризировать все auxiliary providers или запретить unplanned fallback требует design review и не ослабляется ради demo.
