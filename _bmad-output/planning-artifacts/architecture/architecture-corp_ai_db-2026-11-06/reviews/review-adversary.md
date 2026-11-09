# Adversarial architecture review — третий проход

Дата: 2026-11-06T13:35Z  
Объект: `../ARCHITECTURE-SPINE.md`  
SHA-256 текущего объекта: `a8cf3b89310e156db4208f26b07b28e314a80f97c25a9f6f8bfc40939ad9c5af`  
SHA-256 предыдущего reviewed объекта: `0f605619810c5e833f90970b1cda921d222b1f6a75f12a97bc205dcca1492414`  
Метод: повторная попытка построить формально соответствующие, но несовместимые реализации после recovery barrier, decision tags, repo=Space, ProposalRecord version_author, policy bundle, preflight и `index-snapshot-v1` fixes.

## Verdict

**PASS на уровне architecture spine: CRITICAL/HIGH blockers не найдены.**

Не удалось построить две реализации, которые одновременно соблюдают актуальные AD и приводят к небезопасному либо несовместимому canonical merge/recovery/index/export outcome уровня CRITICAL/HIGH. Прежние ADV-18, ADV-19 и ADV-20 закрыты как architecture blockers. Остаются **10 MEDIUM findings: 0 CRITICAL, 0 HIGH, 10 MEDIUM, 0 LOW** — обязательные acceptance items для versioned companions и T00, а не дефекты initiative-level spine.

PASS не означает owner approval, разрешение на implementation или подтверждение GitLab/Open WebUI capabilities. Подробные companion contracts обязательны перед реализацией. Protected annotated decision tags, merge trailers, note ID/hash/audit, metadata export, merge-only-GO и token/branch-rule semantics остаются реальными T00 stop-checks (`ARCHITECTURE-SPINE.md:202`). Пустой `companions: []` на этом этапе не считается finding.

## Результаты повторных атак на прежние blockers

| Атака | Почему CRITICAL/HIGH больше не воспроизводится |
|---|---|
| Late in-flight M1 после crash, затем новый M2 | Перед внешним merge call GO фиксирует `merge_attempted` и per-target `recovery_required` в DB transaction; barrier блокирует все новые merges target после crash/fencing, timeout его не снимает, недоказуемый outcome остаётся quarantined (`:66`). Прежняя retry-only реализация теперь несоответствующа |
| Повтор уже применённого SHA под другим decision | Дедупликация ограничена `(repository_id, target_branch, proposal_sha)`; merge признаётся только с first parent=`base_sha`, second parent=`proposal_sha` и совпадающими trailers/note/tag (`:66`). Нельзя присвоить текущему decision произвольный merge только по ancestry |
| Editor self-approval через original author | Каждая ProposalRecord версии содержит отдельный `version_author_stable_id`; редактор создаёт новую версию и не может утвердить её сам (`:60`, `:128`) |
| Разные access/approval policy у IAM и GO | Один `policy_bundle_id`, согласованные access/approval revisions в AuthzContext и DecisionRecord (`:60`, `:66`, `:96`, `:130`) |
| Смешанный index snapshot/incremental reuse | `index-snapshot-v1` различает snapshot, document revision, content и dependency hashes; incremental run обязан иметь полный dependency closure, эквивалентный full snapshot на том же `main_sha` (`:78`) |
| Retrieval из inactive preflight | Preflight строится на exact `cutover_sha` и никогда не обслуживает retrieval до активации Space (`:78`) |
| Partial export чужих Spaces | В MVP один repository=один Space; ACL, blobs, history, refs и export имеют единый периметр (`:48`). Full clone требует права на Space и всю его историю (`:90`) |
| Rejected proposal теряется или попадает в index | Decision tag сохраняет `proposal_sha` и входит в clone, а index по-прежнему строится только из published `main`/inactive preflight (`:66`, `:78`). Full-history export permission покрывает достижимое rejected content |
| Два владельца active index pointer | Только CI/index writer продвигает pointer после полного run, с serialization per Space/generation/profile (`:78`) |
| Ложный `merged` по MR state или timeout | Только проверенный merge commit с заданными parents/trailers/note/tag подтверждает `merged`; timeout и недоказуемый outcome остаются quarantined (`:66`) |

## Граница PASS

Следующие сценарии сознательно не классифицированы как blockers:

- **Полная потеря `kb_ops`:** безопасная реализация обязана консервативно рассматривать unresolved DecisionRecords как potentially attempted и восстановить barrier до новых merges. Альтернатива «нет DB row — merge точно не отправлялся» противоречит требованию quarantine недоказуемого outcome и потому не является формально соответствующей реализацией. Детализация bootstrap остаётся MEDIUM ADV-28.
- **Accept/reject/cancel crash между tag и MR transition:** canonical `main` этим путём не изменяется; DecisionRecord и MR state позволяют восстановить результат. Нужен общий non-merge apply protocol, но это не merge-race уровня HIGH (ADV-29).
- **Поздний index run:** реализация, активирующая старый SHA, прямо нарушает AD-9 Prevents и I11; она не используется как допустимая вторая реализация. Обязательные CAS/freshness fixtures остаются в companion (ADV-31).
- **Restore на GitLab с другими note IDs:** это заранее объявленный UNKNOWN metadata export, а не скрытое противоречие. Нужен доказанный ID-preservation или authenticated alias protocol; отсутствие capability требует design review по самому spine (ADV-32).

---

# MEDIUM — обязательные условия companions перед реализацией

## ADV-28 — MEDIUM: recovery barrier должен восстанавливаться консервативно после полной потери БД

**Локация:** AD-7 (`ARCHITECTURE-SPINE.md:66`), AD-8 (`:72`), State (`:133`).

**Триггер:** `merge_attempted` и `recovery_required` устанавливаются в `kb_ops`, но схема пересобираема. Decision tag создаётся до DB transaction, поэтому отсутствие merge commit и DB row не доказывает, что внешний merge call не отправлялся.

**Реализация A — per-target bootstrap recovery.** При rebuild GO сканирует protected decision tags/notes, помечает каждый target с unresolved accept как `recovery_required`, выполняет target-wide reconciliation и лишь затем открывает merges. **Реализация B — global bootstrap freeze.** После любой потери `kb_ops` GO запрещает все merges deployment-wide, затем снимает freeze target за target после того же reconciliation. Обе реализации соблюдают quarantine недоказуемых outcomes; B выбирает более широкий availability tradeoff.

**Несовместимость и последствие:** A и B различаются порядком восстановления и доступностью, но обе безопасны. Несовместимость появится только если companion позволит трактовать отсутствие `merge_attempted` row как доказательство отсутствия in-flight call; тогда late merge сможет повторить прежний CRITICAL сценарий.

**Минимальное усиление / companion:** `go-merge-recovery-v1` должен явно задать bootstrap barrier до первого merge, conservative classification unresolved tags как `unknown`, запрет вывода `not_attempted` из отсутствующей DB projection и target-wide fixtures с потерей БД после note/tag, после DB transaction и после отправки merge.

## ADV-29 — MEDIUM: accept/reject/cancel требуют отдельного apply/recovery state machine

**Локация:** AD-7 (`ARCHITECTURE-SPINE.md:66`), AD-13 (`:102`).

**Триггер:** decision tags покрывают accept/reject/cancel, а projection states описаны преимущественно для merge. Crash между protected tag и MR close/transition допускает разные промежуточные представления.

**Реализация A — synchronous non-merge apply.** Для reject GO создаёт note/tag, затем синхронно закрывает MR с exact proposal SHA и только после этого возвращает `rejected`; crash оставляет `recorded`, retry тем же decision ID повторяет close. **Реализация B — asynchronous non-merge apply.** После tag GO возвращает `reject_recorded`, а MR close выполняет reconciliation; терминальный `rejected` также требует подтверждённого closed MR. Обе идемпотентны и не утверждают terminal outcome только по tag.

**Несовместимость и последствие:** API/UI промежуточные статусы и момент ответа различаются; concurrent accept/reject без общей ordering model может оставить два DecisionRecords, из которых только один имеет применённый MR outcome. Это не создаёт записи в `main`, но требует единой projection/retry семантики.

**Минимальное усиление / companion:** `proposal-decision-v1` задаёт non-merge states, MR conditional transition, ordering accept/reject/cancel/edit относительно merge barrier, поведение проигравшего DecisionRecord и recovery после crash между tag и close. Терминальный reject требует и DecisionRecord, и подтверждённого закрытия MR согласно AD-13.

## ADV-30 — MEDIUM: policy bundle должен фиксировать effective snapshot и invalidation при его смене

**Локация:** AD-6 (`ARCHITECTURE-SPINE.md:60`), AD-12 (`:96`), Policy (`:130`).

**Триггер:** bundle и revisions согласованы, но физическое размещение policy и момент, когда новая revision становится effective, остаются контрактной деталью.

**Реализация A — co-located bundle.** Access/approval policy лежат в target Space repository; их revisions связаны с `base_sha`, а per-target merge lock сериализует и policy, и документы. **Реализация B — shared policy repository.** Bundle ссылается на отдельный policy repository; IAM активирует immutable bundle revision, GO перед merge использует один effective bundle и отклоняет decision при смене revision до apply. Обе используют одинаковые bundle/revisions в AuthzContext и DecisionRecord.

**Несовместимость и последствие:** co-located и shared bundle имеют разные блокировки, activation lag и recovery boundaries. Если B разрешит безусловное переключение revision между note/tag и merge, audit будет описывать не ту policy; если A ошибочно считает, что любой bundle покрыт document lock, появится аналогичный race.

**Минимальное усиление / companion:** `policy-bundle-v1` задаёт canonical location, effective-vs-merged activation, immutable bundle manifest, согласование access/approval revisions, final freshness check и обязательную invalidation/new decision при смене effective bundle. Для shared repository нужен явный cross-repository ordering/recovery protocol, а не предположение о per-Space lock.

## ADV-31 — MEDIUM: `index-snapshot-v1` должен закрепить stale baseline и activation CAS fixtures

**Локация:** AD-9 (`ARCHITECTURE-SPINE.md:78`), Git revisions (`:127`).

**Триггер:** поля различены, но retrieval всё ещё использует общий термин `revision_sha`; не выбран единый freshness baseline для normal CI lag и preflight catch-up.

**Реализация A — snapshot freshness.** Retrieval считает candidate stale, когда его `snapshot_sha` отстаёт от observed published HEAD; ответ явно содержит indexed-through SHA либо candidates отклоняются. **Реализация B — dependency freshness.** Retrieval допускает unchanged candidate со старым `document_revision_sha`, если current dependency hash совпадает, а manifest имеет допустимый indexed-through ancestor; изменённые dependencies отклоняются. Обе используют полный dependency-closed snapshot и не выдают historical content молча.

**Несовместимость и последствие:** A может временно отклонять весь corpus, B сохраняет unchanged retrieval; UI freshness и metrics различаются. Некорректная B без current dependency check вернёт stale content, поэтому проверка не может быть optional.

**Минимальное усиление / companion:** `index-snapshot-v1` задаёт, какое поле заменяет generic `revision_sha` в retrieval, stale baseline, indexed-through response, current dependency validation, activation CAS по active pointer, preflight-to-published catch-up и запрет late activation. Отдельный GitLab-outage stale mode остаётся ADR.

## ADV-32 — MEDIUM: restore должен сохранять верифицируемую связь Decision-Note-ID после смены GitLab instance

**Локация:** AD-7 (`ARCHITECTURE-SPINE.md:66`), AD-11 (`:90`), Deferred capabilities (`:202`).

**Триггер:** merge commit immutable и содержит исходный `Decision-Note-ID`; clean GitLab может назначить новые note IDs при импорте. Protected tag и `record_sha256` сохраняются в clone, а API note ID может измениться.

**Реализация A — ID-preserving import.** Целевой GitLab/import mechanism сохраняет original MR/note IDs; reconciliation выполняет прямое совпадение trailers/note/tag. **Реализация B — authenticated alias manifest.** Restore создаёт новые notes, а signed/versioned manifest связывает original note ID с restored ID; reconciliation использует alias вместе с protected tag и record hash, признавая прямое несопоставленное несовпадение invalid.

**Несовместимость и последствие:** прямой importer A не совместим с alias consumer B и наоборот; без нормативного alias все restored decisions могут стать `invalid`, либо ослабленная проверка примет подменённую note. Это закрывается только проверенной capability/contract, не игнорированием ID mismatch.

**Минимальное усиление / companion:** `portability-manifest-v1` и T00 выбирают ID preservation или authenticated aliases, сохраняют original/restored MR IID/note IDs, required refs включая `kb-decisions/*`, record/tag hashes, MR metadata и attachment closure. Невозможность доказать связь — design review/BLOCKED, а не PASS restore.

## ADV-33 — MEDIUM: CutoverRecord и preflight resume нуждаются в едином representation

**Локация:** AD-3 (`ARCHITECTURE-SPINE.md:42`), AD-1 (`:30`), AD-9 (`:78`).

**Триггер:** write freeze, exact SHA и inactive preflight заданы, но location CutoverRecord и состояния повторного запуска делегированы реализации.

**Реализация A:** annotated cutover tag содержит record; состояние вычисляется из tag + branch rules + preflight manifest + grants. **Реализация B:** protected tag идентифицирует corpus, а отдельный Git ref хранит append-only CutoverRecord states. Оба различают corpus SHA и record/tag identity и соблюдают freeze/protect/preflight/activation порядок.

**Несовместимость и последствие:** export и resume одной команды могут не распознать запись другой; crash между preflight success и activation допускает разные повторные действия. Сам preflight retrieval barrier уже закрыт.

**Минимальное усиление / companion:** `cutover-record-v1` задаёт location, corpus/record/tag SHA, states `frozen/protected/preflight_ready/active`, идемпотентный resume, поведение при новом reviewed merge во время preflight и обязательное включение record/refs в export.

## ADV-34 — MEDIUM: append-only ProposalRecord требует canonical persistence и version linkage

**Локация:** AD-6 (`ARCHITECTURE-SPINE.md:60`), Proposal identity (`:128`), ownership table (`:170`, `:174`).

**Триггер:** `version_author_stable_id` устраняет self-approval ambiguity, но расположение append-only ProposalRecord каждой версии не названо; оно должно переживать потерю `kb_ops`.

**Реализация A:** каждая версия получает structured MR note с version linkage и hash; source commit хранит только SHA reference. **Реализация B:** canonical ProposalRecord находится в commit trailer/annotated version tag, MR note является API representation. Обе сохраняют original author, version author, requester и exact base/proposal SHA в GitLab.

**Несовместимость и последствие:** recovery и export, ожидающие разные representations, не смогут доказать editor attribution; удаление source branch без version anchor может оборвать историю review. Это не меняет принятую principal model.

**Минимальное усиление / companion:** `proposal-record-v1` задаёт canonical GitLab persistence, previous-version linkage, immutable hash, required principals, relation к DecisionRecord и clone/export refs. ActorIdentity включает provider/issuer namespace, поскольку OIDC `sub` уникален только внутри issuer.

## ADV-35 — MEDIUM: AuthzContext требует trusted issuer и единой scope/freshness semantics

**Локация:** AD-4 (`ARCHITECTURE-SPINE.md:48`), AD-12 (`:96`), Capability map (`:191`).

**Триггер:** server-issued context, bundle и refresh заданы, но issuer/validation и одинаковая интерпретация effective scopes между компонентами остаются в companion.

**Реализация A:** только Identity/AuthZ adapter выдаёт context, остальные проверяют issuer, actor/request/run binding и freshness. **Реализация B:** доверенные GO/Retrieval создают internal contexts через общий AuthZ library и одинаковые policy/group snapshots. Обе обновляют context перед payload/export/merge и не принимают actor/groups от agent payload.

**Несовместимость и последствие:** snapshots в пределах SLO могут дать разные промежуточные scopes; consumer без issuer/freshness contract не отличит доверенный context от произвольной структуры. Это не отменяет зафиксированный revocation barrier.

**Минимальное усиление / companion:** `authz-context-v1` задаёт trusted issuers/validators, audience/request/run binding, expiry/max age, replay rules, policy bundle activation, Space/path scope semantics и ActorIdentity с issuer/directory ID. Изменение effective bundle до merge должно инвалидировать decision согласно ADV-30.

## ADV-36 — MEDIUM: source cursor остаётся обязательным recovery protocol

**Локация:** AD-10 (`ARCHITECTURE-SPINE.md:84`), ownership table (`:174`).

**Триггер:** canonical source registry и durable phases названы, но version/hash и переход source version во время outstanding MR делегированы.

**Реализация A:** front matter хранит provenance/previous base, registry — cursor; новые versions ждут завершения outstanding MR. **Реализация B:** registry хранит provenance/base/cursor, front matter только refs; новая version обновляет тот же MR новым `proposal_sha` и новым `version_author_stable_id`, сбрасывая approval. Обе сохраняют один outstanding proposal и durable cursor phases.

**Несовместимость и последствие:** restore с другой моделью повторяет/пропускает versions; raw ETag и normalized Markdown hash дают разные no-op решения. Обновление MR меняет reviewed version, ожидание меняет freshness.

**Минимальное усиление / companion:** `source-sync-v1` задаёт canonical registry, binding identity, raw/source version, raw и normalized hashes, previous base, durable evidence для `seen/proposed/merged`, backup/export и единый wait/update-MR protocol.

## ADV-37 — MEDIUM: AttachmentChanged и knowledge/full-service restore требуют явных contracts

**Локация:** AD-15 (`ARCHITECTURE-SPINE.md:114`), AD-9 (`:78`), AD-11 (`:90`), Deferred RPO/RTO (`:208`).

**Триггер:** два независимых companion вопроса остаются: canonical attachment event/binding и допустимый restore scope upstream-owned state.

**Реализация A:** attachment binding находится в `attachments.yaml` того же reviewed commit, published event отправляется после merge; backup дополнительно включает PostgreSQL/PITR и secrets recovery. **Реализация B:** binding находится во front matter, upload event ждёт published binding; backup ограничен knowledge corpus, users проходят JIT, credentials заводятся повторно. Обе пары допустимы только при явном contract/owner-approved RPO; unreviewed attachment и скрытая потеря upstream state не считаются соответствующими.

**Несовместимость и последствие:** exporter/indexer по-разному вычисляет attachment closure; одинаковый restore PASS может означать полный сервис или только знания. RPO/RTO явно DEFERRED, поэтому restore scope не повышен до HIGH.

**Минимальное усиление / companion:** `attachment-binding-v1`/`attachment-event-v1` разделяют upload и published events, platform/object-store versions, exact main SHA, reviewed binding и dependency closure. Backup/runbook классифицирует canonical state как MUST_RESTORE или ALLOWED_LOSS с owner-approved RPO; portability не содержит secrets/chats by default.

---

## Судьба предыдущего прохода

| Прежний ID | Решение в третьем проходе |
|---|---|
| ADV-18 CRITICAL | Закрыт DB transaction + per-target `recovery_required` перед external call, блокировкой всех new merges и quarantine timeout/unknown; bootstrap детализация — ADV-28 |
| ADV-19 HIGH | Закрыт scoped tuple, parent order и обязательными trailers/note/tag; restore ID mapping — ADV-32 |
| ADV-20 HIGH | Закрыт `index-snapshot-v1` и эквивалентностью incremental full snapshot; freshness baseline/fixtures — ADV-31 |
| ADV-21 | Закрыт `version_author_stable_id`; persistence — ADV-34 |
| ADV-22 | Policy bundle/AuthzContext усилены; trusted issuer/freshness — ADV-35 |
| ADV-23 | repo=Space и full-history permission закрывают perimeter; restore/export IDs/refs — ADV-32/ADV-33 |
| ADV-24 | Представление/resume — ADV-33, не blocker |
| ADV-25 | Source protocol — ADV-36, не blocker |
| ADV-26 | Attachment contract — ADV-37, не blocker |
| ADV-27 | Owner-approved RPO/restore scope — ADV-37, не blocker |

## Условия сохранения PASS

1. До реализации утвердить versioned companions для ADV-28…ADV-37 и связанные concurrency/recovery/disclosure fixtures.
2. В T00 доказать protected annotated decision tags, custom merge trailers/parent order, note ID/hash/audit, metadata export/restore, merge-only-GO и branch/token semantics на pinned GitLab edition.
3. Не ослаблять conservative recovery: unresolved после потери БД = unknown/quarantine, а не `not_attempted`; timeout не снимает barrier.
4. Не заменять реальные sandbox checks моками. Отсутствие required GitLab capability возвращает соответствующий design в BLOCKED согласно Deferred, но не является новым finding против текущего spine.

**Итог:** текущий spine согласован на initiative level. CRITICAL/HIGH blockers не остаются; дальнейшая работа — обязательная детализация companions и реальная capability verification, а не ещё один пересмотр принятых AD по уже закрытым сценариям.
