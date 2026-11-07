# Source and immutable storage integration contract

**Статус:** PROPOSED для G0. Authority: [ARCHITECTURE-SPINE.md](../architecture-spine.md), AD-3, AD-8–AD-11, AD-14–AD-16. Сквозные flows: [integration.md](../integration.md).

Первый connector, source versions/editions/API/auth/rate limits, object-store layout, extraction route, supported formats и numeric size/rate/retention limits — **UNKNOWN до T00/owner decision**. Production corpus не создаётся до согласования repository perimeter и source corpus.

## 1. Source binding и доверие

Versioned source binding связывает:

- `source_id`, `source_binding_id`, selected remote objects;
- один target repository=Space и path policy;
- ownership mode и deployment data profile;
- source owner и required legal/data barriers;
- минимальный read credential reference в deployment secrets;
- approved extraction/provider route и config hash.

Source credential, object-storage credential и bind secrets не попадают в documents, ProposalRecord evidence, model args, logs, dry-run или export. Source ACL hints — только подсказки, не platform grants. Effective ACL выдаёт Identity/AuthZ; разные ACL требуют разных Spaces/repositories.

Connector имеет отдельный `connectorCredential` из [OpenAPI](openapi.yaml) с source-binding-scoped dry-run, post-cutover proposal, non-live cursor read и registered typed read capabilities. Он не использует browser/agent credential и не имеет pre-cutover bulk, merge/index/grant rights. Source text — недоверенные данные.

## 2. Import dry-run

Вход: immutable source snapshot `{source_id,source_version,content_sha256,package_ref}`, source binding, normalized config hash, ownership mode, data profile и Idempotency-Key.

1. Проверить согласованный Space/repository, owner, data profile и binding.
2. Прочитать immutable version/hash; mutable current URL не является версией.
3. Выполнить intake security и path normalization.
4. Построить deterministic path→document UUID map, сохраняя IDs при rename по provenance; same basename и Cyrillic не меняют stable ID.
5. Построить tree, relative links/anchors, attachment manifest, provenance и previous imported base.
6. Выполнить extraction только в staging; сохранить original/extracted/canonical hashes, approved route/config и loss report.
7. Завершить data/PII/media/quality checks и human dispositions.
8. Вернуть [ImportManifest](openapi.yaml) с `canonical_writes=false`, entries, attachments, errors/warnings и manifest hash.

Dry-run не создаёт branch, MR, `main` commit, active index entries или `merged` cursor. Повтор того же source+config snapshot воспроизводит IDs/manifest. Другой snapshot создаёт новый manifest/hash, не мутирует прежний evidence.

### Intake security

Отклоняются либо изолируются до отдельного supported workflow:

- archive traversal, absolute/ambiguous paths, `\`, `..`, symlinks и escape за staging root;
- executable HTML/MDX, active content и unsafe preview;
- `.git`, `.env`, keys/tokens/password-like secrets и запрещённые hidden files;
- oversized/decompression-bomb inputs и превышение configured count/size limits;
- duplicate IDs, unsupported formats, invalid UTF-8 canonical output и unresolved required links;
- mutable/unhashed attachments и declared/observed media mismatch.

Limits до owner/T00 не означают unlimited input; test configuration fail closed.

## 3. Import commit и cutover

Commit принимает `dry_run_manifest_sha256`, `expected_base_sha`, rationale/evidence и тот же idempotency context.

| Фаза | Результат commit | Публикация |
| --- | --- | --- |
| До cutover | `pre_cutover_controlled` staging package | Controlled engineering bulk только в unpublished main, без пользователей/published index; затем sign-off/freeze/protections/preflight/activation |
| После cutover | `post_cutover_proposal` через GO | Только MR + human review + GO merge; auto-merge запрещён даже для deterministic source_managed |

Manifest mismatch, stale base, unresolved blocker или revoked capability даёт ноль canonical writes. Повтор по hash/version — no-op или возврат существующего result/proposal.

## 4. Ownership modes

| Mode | Source update | Local edit | После cutover |
| --- | --- | --- | --- |
| `migrated` | Старый source не writer; изменение может быть audit signal | Обычный GO/MR | GO/MR/human merge |
| `source_managed` | Deterministic diff от previous imported base | Запрещён policy; GO отклоняет local proposal | GO/MR/human merge; auto-merge запрещён |
| `curated` | Сравнение previous imported base + current curated + incoming | Разрешён и сохраняется | Proposal/conflict через GO/MR; ноль overwrite |
| `live_operational` | Typed read-only API/snapshot по запросу | Нет canonical wiki edit | Нет automatic page/MR/index/cursor |

`live_operational` намеренно отсутствует в canonical [front matter v2](front-matter.schema.json) ownership enum и в ProposalRecord; [source-origin](source-origin.schema.json) допускает его только для typed source binding/provenance. `SourceSyncCursor` и `kb.source.sync.changed.v1` содержат лишь migrated/source_managed/curated: live document/proposed/outstanding/merged cursor запрещён контрактом.

## 5. Provenance и three-way update

[source-origin-v1](source-origin.schema.json) сохраняет source/binding/object/version/hash/ref, observed_at, ownership mode, optional previous imported base, immutable original и extraction provenance. `DOC-0001` и другие stable source IDs не подвергаются lowercase normalization. Operational cursor не хранится в canonical origin.

Versioned `document-front-matter-v2` — отдельный schema contract change по content-standard v2.3 §4.4. Он требует origin для migrated/source_managed и равенства outer/inner ownership mode, добавляет stable `links[]` по document UUID и `valid_until`; `access` остаётся запрещённым. [docops-review-metadata-v1](docops-review-metadata.schema.json) проецирует exact document revision/date/provenance в review queue и `kb.docops.review_requested.v1`: expired → due, future/current → scheduled, removed → null+not required. Registry/metadata не может перезаписать canonical значение или создать grant. `archived=true` iff archive present; restore опускает archive, replacement/descendants проверяются semantic validator.

Для curated update сравниваются:

1. **previous imported base** — последний учтённый source-derived content;
2. **current curated document** — актуальная exact Git revision;
3. **incoming source** — новая immutable source version/extraction.

Source-independent manual changes сохраняются. Same-paragraph/semantic conflict становится явным proposal/conflict с evidence; silent whole-file overwrite запрещён. Source deletion создаёт tombstone/obsolete review. Owner выбирает archive/delete/retain через reviewed MR; Git history/mirrors/object retention не стираются автоматически.

## 6. Durable cursor и one outstanding proposal

GO владеет cursor в `kb_ops` для `(source_binding_id,source_object_id)`:

| Cursor | Когда продвигается | Когда запрещено |
| --- | --- | --- |
| `seen_version + seen_hash` | Только парой после durable observation с достаточными immutable metadata | При временном fetch/extraction failure до durable record или при version без hash/hash без version |
| `proposed_version + proposed_hash` | Только парой после durable MR + ProposalRecord; `proposal_pending` дополнительно требует outstanding proposal ID+SHA | До MR, после crash без record, при false staging success или отсутствии одной части pair |
| `merged_version + merged_hash` | Только парой после проверенного Git-derived merge и source mapping reconciliation | После MR creation, human reject/conflict, merge timeout или CI indexing; merged без hash запрещён |
| `outstanding_proposal_id + outstanding_proposal_sha` | Только парой при `proposal_pending` | Оба null при `merged` и любом другом non-pending state; completed/rejected/conflicted proposal не остаётся outstanding |

Правила:

- На source object не более одного outstanding proposal независимо от workers/retries.
- Новая source version во время outstanding обновляет только `seen`; второй MR не создаётся.
- После terminal outcome latest seen обрабатывается от fresh base; поддерживаемые intermediate versions остаются в provenance/evidence.
- Same hash/version — no-op или существующий proposal.
- Reject/conflict не продвигает `merged`; следующий proposal — явное новое решение, не overwrite.
- GO сериализует source transitions per source object. Merge serialization остаётся отдельным per-target lock и не удерживается во время review.
- Crash до MR, после MR до cursor и после merge до cursor восстанавливается из durable source registry/MR/Git outcome, не из worker memory.

События cursor публикуются как `kb.source.sync.changed.v1` в [events.yaml](events.yaml).

## 7. Immutable originals и attachments

Каждая attachment revision содержит:

```text
object_id, version, sha256, size, media_type, source_ref,
media_class, verification_status
```

и связывается с document revision и Space ACL через [front matter](front-matter.schema.json).

- Originals/large assets immutable/versioned. Повторная загрузка того же hash — no-op/existing ref.
- Поддерживаемые мелкие assets могут входить в reviewed Git MR; большие/чувствительные originals остаются в approved object storage.
- Mutable current URL без hash не является canonical/export/CI reference.
- CI читает только object/version/hash отдельным read-only credential. Object storage не предоставляет public anonymous URL по умолчанию.
- `kb.attachment.changed.v1` проходит GO→CI и расширяет dependency closure; removal также требует canonical snapshot и учитывает history/retention.
- Attachment payload, history и export повторно авторизуются; search credential не даёт object-history access.

### Media admission

| Class | Обработка | Index/answer |
| --- | --- | --- |
| `decorative` | Не переносить | Исключить |
| `illustrative` | Immutable asset + короткая подпись | После checks |
| `substantive` | Original + явно automatic description + risk-based human check | Description маркировано и ссылается на original |
| `critical` | Требуемая human transcription/verification | Только после verification |
| `handwritten` | Human transcription со сверкой или страница-ссылка на original | Нетранскрибированное не индексируется |

Автоматическое описание не выдаётся за оригинальный факт и всегда ссылается на original страницы/слайда.

## 8. `live_operational` typed read-only flow

1. Agent/UI выбирает зарегистрированную typed operation и bounded filters; arbitrary source query не поддерживается. Машинная boundary — `readLiveOperational` в [OpenAPI](openapi.yaml) с `LiveOperationalReadInput/Result`.
2. Adapter проверяет server AuthzContext, operation allowlist, source credential scope, data profile, path/body Space+binding equality и limits.
3. Выполняется только read. Result содержит `snapshot_time`, immutable source version/hash, typed facts и truncation/limits; `canonical_writes=proposal_cursor_effects=index_writes=false`.
4. Payload повторно авторизуется по Space/operation scope до browser/model payload.
5. Timeout/error не маскируется stale result как current fact. Любой cache требует отдельного design и client+ACL+snapshot/policy keys.
6. Не создаются Git page, MR, embedding/index entry или source `merged` cursor.

## 9. Errors и retry

| Code | Семантика |
| --- | --- |
| `SECURITY_REJECTED` | Traversal/symlink/executable/secrets/oversize; quarantine/reject |
| `PII_REVIEW_REQUIRED` | Нет corpus/inference admission до human disposition |
| `UNSUPPORTED_FORMAT` | Явный manifest error; success не выдумывается |
| `EXTRACTION_LOSS` | Quarantine/other approved route/human review; cursor не выдаёт success |
| `OUTSTANDING_PROPOSAL_EXISTS` | Вернуть существующий proposal; обновить только seen для новой версии |
| `CURATED_CONFLICT` / `STALE_BASE` | Явный conflict; нет overwrite/merged transition |
| `SOURCE_GONE` | Tombstone/obsolete review, не silent delete |
| `UPSTREAM_UNAVAILABLE` | Bounded retry/backoff; durable cursors без результата не продвигаются |
| `IDEMPOTENCY_KEY_REUSED` | Тот же key с другим source/config/payload отклонён |

Worker не создаёт новый key для маскировки uncertain outcome. Все extraction/OCR/LLM calls используют approved inventory; failure не даёт false success или blind summary publication.

## 10. Export/restore closure

[export-manifest](export-manifest.schema.json) связывает source origins, document revisions/content hashes и immutable assets. Для complete export:

- каждый external asset имеет object/version/storage ref и `exported_object_sha256 == attachment.sha256`;
- missing/rejected asset не имеет выдуманного `exported_object_sha256`, попадает в `missing[]`, поэтому `closure.complete=assets_complete=false` и ready запрещён;
- `decisions_complete=assets_complete=authorization_complete=true` и `missing=[]` обязательны для complete/ready; accepted-before-merge сохраняет explicit outcome+recovery evidence, `attempts=[]` без no-merge claim, не fictitious merge/attempt; rejected/cancelled также не имеют merge operation;
- `documentEntry.valid_until` обязателен и равен canonical front-matter-v2 на exact document revision; roundtrip восстанавливает то же значение;
- source refs не содержат credentials или mutable signed URLs;
- policy/grants mapping и decisions closure восстанавливаются отдельно;
- clean restore проверяет originals/extracted/canonical provenance, links/attachments, decisions и full index rebuild.

Secrets, private chats и raw unapproved source payloads не экспортируются. Retention/object deletion учитывает Git history, mirrors и object versions; hard purge — отдельный deferred privileged workflow.

## 11. Обязательные проверки

После T00: deterministic nested import/Cyrillic/same basename, repeat/resume/no-op, malicious fixtures, strict/PII gates, все ownership modes, curated conflicts/deletion, two workers/one outstanding, cursor crash points, attachment hash/ACL/media gates, live_operational read-only и export/restore closure. Первый реальный connector отдельно проверяется на sandbox update/revoke/delete/retry/attachments; mocked source не считается реальной integration проверкой.
