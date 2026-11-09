---
name: 'Security and data-integrity review — Corporate Agentic Knowledge Platform'
type: architecture-review
status: no-critical-high-blockers
created: '2026-11-06'
updated: '2026-11-06T13:35:10Z'
review_round: 3
reviewed_artifact: '../ARCHITECTURE-SPINE.md'
normative_source: '../../../../../specs/corporate-kb/spec.md'
scope: 'Target TOCTOU, MR note/tag tamper, self-approval editor, recovery fencing/unknown, full clone ACL, cutover race'
verdict: 'Нет CRITICAL/HIGH blockers в проверенном scope. Все шесть findings закрыты на уровне design; требуется T00 verification.'
---

# Security / data-integrity review — повторная проверка, раунд 3

## 1. Verdict

**Нет blockers.**

В шести запрошенных security/data-integrity областях не осталось CRITICAL/HIGH архитектурных замечаний. Все findings переведены в **CLOSED / DESIGN → READY FOR T00 VERIFICATION**.

Это не VERIFIED/DONE и не owner security/design approval. Выбранные Open WebUI commit и GitLab version/edition отсутствуют; concurrency, crash, tamper, export и restore tests ещё не выполнялись. Итоговое решение G0 остаётся за владельцем и должно опираться на реальные T00 evidence.

## 2. Основание

Проверен актуальный `ARCHITECTURE-SPINE.md`: AD-1–AD-16, Consistency Conventions, Structural Seed и Deferred, относительно R05–R14 и I01–I14 в `spec.md`.

Ключевые новые гарантии:

- canonical DecisionRecord хранится как полный JSON одновременно в append-only MR note и protected annotated tag `kb-decisions/<decision_id>` на `proposal_sha`;
- tag является Git-native durability anchor для accept/reject/cancel и входит в clone;
- `recovery_required` устанавливается до внешнего merge call и блокирует все новые merges target после crash/fencing до conclusive target-wide reconciliation;
- недоказуемый outcome остаётся quarantined, timeout не снимает barrier;
- один GitLab repository = один Space;
- merge reconciliation проверяет parentage, note, tag, hash и trailers;
- squash, automatic rebase и fast-forward запрещены.

## 3. Сводка findings

| ID | Область | Статус | CRITICAL/HIGH |
|---|---|---|---|
| SD-01 | Target merge/approval TOCTOU | CLOSED / DESIGN | Нет |
| SD-02 | Self-approval последующим editor | CLOSED / DESIGN | Нет |
| SD-03 | Decision note/tag tamper, durability и rebuild | CLOSED / DESIGN | Нет |
| SD-04 | Recovery fencing/unknown | CLOSED / DESIGN | Нет |
| SD-05 | Cutover race | CLOSED / DESIGN | Нет |
| SD-09 | Full clone cross-space ACL | CLOSED / DESIGN | Нет |

---

## SD-01 — CLOSED / DESIGN: target TOCTOU закрыт serialized writer и проверяемым merge result

**Evidence:** AD-2, AD-6, AD-7; R08, R10; I05, I06.

### Закрывающие controls

1. Все business/engineering final apply проходят GO; после cutover только merge service identity GO имеет merge permission.
2. Все merges сериализуются per repository/target branch через advisory lock с owner/fencing token и коротким critical section.
3. GO использует один `policy_bundle_id` и согласованные access/approval revisions, повторно проверяет external group, path scope, exact `proposal_sha` и `target HEAD == base_sha` непосредственно перед merge.
4. Mismatch даёт conflict и ноль writes в `main`.
5. Squash, automatic rebase и fast-forward запрещены. Reconciliation требует first parent = `base_sha`, second parent = `proposal_sha`, а также совпадение trailers/note/tag.
6. `recovery_required` не позволяет следующему writer начать новый merge после crash/fencing, пока прежний target-wide outcome не доказан.

Прежний сценарий, в котором engineering merge или второй GO instance продвигает target между проверкой и merge, закрыт единым writer perimeter и target-wide recovery barrier. Проверка parentage дополнительно предотвращает признание merge, применённого не к просмотренным base/proposal.

### Обязательная T00 verification

- Доказать отсутствие merge/push мимо GO через UI, API, merge trains, auto-merge и engineering tokens.
- Доказать общий lock domain для всех GO instances и фактическую проверку fencing перед merge credential use.
- Concurrency tests: paused owner, stale fenced worker, два GO instances, target change до lock, попытка bypass во время critical section.
- Отклонить squash/rebase/fast-forward и любой merge с неправильными parents/trailers.

При невозможности подтвердить merge-only-GO или branch/token semantics finding переоткрывается; в текущем design блокера нет.

---

## SD-02 — CLOSED / DESIGN: self-approval editor исключён для каждой ProposalVersion

**Evidence:** AD-5, AD-6, AD-12, AD-13, Consistency/Proposal identity; R05, R08; I03, I05.

### Закрывающие controls

- Append-only ProposalRecord каждой версии содержит `author_stable_id`, `version_author_stable_id`, `requester_stable_id`, `actor_type`, optional `run_id`, rationale/evidence, exact SHAs и idempotency metadata.
- Approver не совпадает с author/requester; editor создаёт новую версию и не может утвердить её сам.
- Новый commit/rebase сбрасывает approval; accept/reject/edit идемпотентны по exact proposal SHA.
- Stable IDs и actor принимаются из server-issued trusted context, а не из LLM/client-controlled Git identity.

Сценарий «чужой request → собственный edit → собственный approve» закрыт явно для текущей версии.

### Обязательная verification

Self-edit после agent-run; повторный editor; author/requester/version_author/approver collisions; spoofed actor; replay старого approval на новый SHA; edit после approval; переименование login/email без смены stable ID.

---

## SD-03 — CLOSED / DESIGN: protected annotated tags восстанавливают полный canonical JSON для всех решений

**Evidence:** AD-1, AD-7, AD-11; R07–R10, R14; I07.

### Закрывающие controls

1. Канон — единый JSON с `decision_id`, `proposal_sha`, `base_sha`, action, actor `stable_id`, timestamp, evidence, `policy_bundle_id`, access/approval revisions и `record_sha256`.
2. Полный JSON сохраняется не только в MR note, но и в protected annotated tag `kb-decisions/<decision_id>` на `proposal_sha`.
3. Tag явно является полным Git-native durability anchor **для accept, reject и cancel**, а не только hash accepted decision.
4. MR note теперь API/UI representation. Её изменение/удаление не уничтожает единственный canonical экземпляр: полный record восстанавливается из tag.
5. Missing/mismatched note или tag делает decision invalid; исправление создаёт новый `decision_id` со `supersedes_decision_id`, что запрещает незаметную перезапись истории.
6. Tag входит в clone; export содержит явные refs и DecisionRecords/MR metadata, restore проверяет snapshot closure.
7. Merge commit содержит `Decision-ID`, `Decision-Note-ID`, `Decision-Hash`, `Approved-by`; reconciliation сверяет trailers с note/tag/hash и parentage.

Это устраняет оба прежних остаточных риска: reject/cancel получил внешний durable anchor, а accept больше не зависит от невосстановимого hash-only payload. При потере `kb_ops` и удалении/изменении MR note полный actor/evidence/policy JSON можно восстановить и проверить из Git refs.

### Обязательная T00/T13 verification

- Protected annotated tag создаётся с полным JSON на exact `proposal_sha`; tag protection запрещает move/delete для непривилегированных actors и всех service credentials, которым это не требуется.
- Clone/mirror/export действительно включает `kb-decisions/*`, annotations и полный JSON; restore проверяет их hashes и согласованность с MR metadata.
- Tamper tests: edit/delete/spoof note; missing/mismatched tag; tag на неправильном SHA; изменённый JSON/hash; trailers mismatch; supersede fork; accept/reject/cancel rebuild после полной потери `kb_ops`.
- Reject/cancel recovery между записью tag и закрытием MR должен завершаться conclusive reconciliation либо quarantine, без второго решения для того же intent.

В текущем design физическая защита tag и полнота export являются обязательными target capabilities из Deferred, а не предполагаемыми фактами. Их провал означает BLOCKED T00, но не оставшийся архитектурный HIGH.

---

## SD-04 — CLOSED / DESIGN: target-wide `recovery_required` закрывает crash/fencing unknown

**Evidence:** AD-6, AD-7, Consistency/State; R09, R10; I07; A09.

### Закрывающие controls

1. Перед внешним merge call одна DB transaction устанавливает `merge_attempted` и per-target `recovery_required`.
2. Barrier блокирует **все новые merges target** после crash/fencing до conclusive target-wide reconciliation, а не только повтор того же MR.
3. Timeout не снимает barrier; недоказуемый outcome остаётся quarantined.
4. Retry по `decision_id` или уже применённому `(repository_id, target_branch, proposal_sha)` возвращает Git-derived результат.
5. Только проверенный merge commit в `main` подтверждает `merged`; transient DB failure не считается доказательством отсутствия merge.

Это закрывает прежний опасный интервал: новый writer больше не может увидеть промежуточно чистый target и начать второй merge, пока старый in-flight request способен завершиться. Target остаётся без новых canonical writes до доказанного результата или quarantine.

### Обязательная crash matrix

Crash до/после DB transaction; до/после note/tag; после отправки merge без response; merge завершён без DB update; stale owner после fencing; новый merge другого MR на том же target во время unknown; timeout; невозможность доказать outcome; concurrent reject/merge.

Ожидания: barrier установлен до side effect, новые merges target заблокированы, conclusive merge проходит parent/note/tag/hash/trailer verification, inconclusive target остаётся quarantined, повтор не создаёт второй Decision-ID/merge.

---

## SD-05 — CLOSED / DESIGN: cutover сохраняет exact-SHA и generation barrier

**Evidence:** AD-3, AD-9; R12; I01, I02, I08, I11.

### Закрывающие controls

- Cutover начинается с write freeze и `HEAD == cutover_sha`, затем создаёт protected tag и MR-only rules с merge только через GO.
- Preflight строится на exact `cutover_sha`, остаётся inactive и никогда не обслуживает retrieval до активации Space.
- Space и published index активируются только после успешной проверки.
- Только CI/index writer продвигает active pointer после полного run, сериализуя запись per Space/generation/profile.
- `index-snapshot-v1` различает snapshot/document/blob/dependency hashes; incremental run должен иметь dependency closure, эквивалентный full snapshot на том же `main_sha`.
- Late old generation не может вернуться через ancestry/generation guards.

### Обязательная verification

Freeze непрерывен до завершения activation; late bulk push и engineering merge отклонены; crash до/после pointer activation не открывает unvalidated corpus; два cutover workers не создают competing active pointers; stale preflight и tag move отклоняются.

---

## SD-09 — CLOSED / DESIGN: repository=Space устраняет cross-space clone disclosure

**Evidence:** AD-4, AD-11, Deferred Repository provisioning; R05, R14; I09.

### Закрывающие controls

- В MVP один GitLab repository = один Space. ACL, blobs, history, protected branch, credentials, cutover, index и clone/export имеют единый периметр.
- Full-repository clone требует export permission на Space и всю его историю; filtered export/удаление истории требуют отдельного privileged workflow.
- Export использует согласованный snapshot с явными refs; decisions/assets manifests и restore snapshot closure обязательны.

Прежний сценарий, когда один pack содержит несколько Spaces с разными ACL, исключён structural invariant. Decision tags входят в тот же Git-native export perimeter.

### Обязательная verification

Actor без полного Space/history export permission получает отказ; clone содержит только один Space; refs включают `kb-decisions/*`; missing tag/object/ref нарушает closure; filtered export нельзя вызвать обычным Space actor; export использует актуальный `AuthzContext`.

---

## 4. Оставшиеся CRITICAL/HIGH

**Нет.**

## 5. Gate recommendation

- Все шесть findings: **CLOSED / DESIGN → READY FOR T00 VERIFICATION**.
- Не переводить их в VERIFIED/DONE и не объявлять owner approval до реальных sandbox GitLab tests на выбранной version/edition.
- Любой failed target capability из Deferred оставляет соответствующую задачу BLOCKED; mocks не принимаются как подтверждение merge-only-GO, protected annotated tags, metadata export или token semantics.

**Финальный verdict: нет blockers.**
