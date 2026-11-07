# ADR-08 — Git-native canonical storage

**ID/Title:** ADR-08 / GitLab как каноническое хранилище документного lifecycle  
**Status:** **Accepted** по spec решением владельца от 2026-11-05; дополнен архитектурными контрактами 2026-11-06. Реализация зависит от результатов T00/G0 и не является production approval.  
**Date:** 2026-11-05; дополнено 2026-11-06  
**Requirements/AD links:** R01–R14, R17, R18; I01–I14; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-1–AD-3, AD-7–AD-10, AD-13, AD-15; [spec.md](../spec.md): разделы 3.2, 5, 7 и 14.

## Context

Версия 1.1 предполагала Notes/pages как канон, PostgreSQL operational DB и collaboration checkpoint/apply consistency. Это создавало две редактируемые истины и переносило сложность lifecycle в собственный mutation boundary. Спецификация 1.2 изменила решение владельца: Git уже предоставляет revisions, branches, MR diff/review, attribution и protected publication.

Нужно зафиксировать единый canonical write path, не исключая контролируемую начальную сборку неопубликованного корпуса. PostgreSQL остаётся полезной для grants snapshots, operations и retrieval, но не должна становиться второй командной базой документов или решений. Decision, cutover, recovery и export требуют отдельных контрактов, чтобы Git-native модель сохраняла audit после потери БД.

## Decision

1. **Markdown + front matter в GitLab — канон.** Полный lowercase commit SHA — revision; `base_sha` — target HEAD, на котором построен diff; `proposal_sha` — exact source HEAD; `merge_commit_sha` — созданный merge commit. Порядок revisions определяется Git ancestry, не сортировкой SHA.
2. **Merge request — proposal**, содержащий exact diff, base/proposal SHA, rationale, evidence и actor/run metadata. После cutover публикация — реальный merge commit через GO по явному человеческому решению. Squash, automatic rebase и fast-forward publication запрещены ADR-13.
3. `document_id` — opaque UUID, не зависящий от пути; `space_id` — стабильный lowercase slug; `source_id` отделён от document ID. Ссылки используют document ID. Rename сохраняет ID; history читается из Git; restore выполняется revert-MR/new commit без перезаписи истории.
4. **DecisionRecord — canonical JSON** в append-only structured MR note от GO и protected annotated tag `kb-decisions/<decision_id>` на `proposal_sha` по ADR-14. Начальная публикация подтверждается CutoverRecord на exact `main_sha` по ADR-11. Merge commit связывается с решением trailers.
5. **PostgreSQL не участвует в canonical write path.** `kb_authz`, `kb_ops`, `kb_index` содержат только производные/операционные состояния с единственными writers по ADR-15. Git-derived current state пересобирается; отсутствие БД не уничтожает канон или decision audit.
6. GO — единственный orchestrator managed Git writes и всех merges после cutover, но не вторая истина. Agent/connector/LLM создают только proposals и не выполняют auto-merge. Engineering review может происходить в GitLab UI, final apply также идёт через GO.
7. Начальная публикация имеет две фазы по ADR-11: controlled engineering bulk допустим только до cutover в unpublished `main` без пользовательского доступа и published index. Это ограниченная pre-publication фаза, а не постоянное исключение из MR-only invariant.
8. Personal Notes не являются каноном managed corpus и не мигрируются. `kb_exec` file-only не является canonical read/write API. Внешние originals/large assets immutable/versioned и связываются hashes с Git revision.
9. **ADR-01 и ADR-02 withdrawn by ADR-08.** Возврат к database-first рассматривается только по stop-триггерам: realtime collaborative editing становится твёрдым требованием либо обязательны page-level ACL внутри одного периметра с прямым доступом людей к Git. Нужен отдельный ADR и переоценка, а не скрытая прослойка.
10. При GitLab outage обходная запись запрещена. Stale index read mode по умолчанию отключён и требует отдельного ADR, явного UX и повторной авторизации.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Database-first + Git export | Гибкие mutations, но dual-write, собственный revision/conflict/audit lifecycle и lock-in | Отклонено решением владельца |
| Notes/pages как канон | Меньше нового UI, но не соответствует managed Git lifecycle и сохраняет collab complexity | ADR-01 withdrawn |
| Собственный collaboration checkpoint/apply | Realtime возможности, но отдельная consistency model вне MVP | ADR-02 withdrawn |
| Только file-only service без GitLab MR | Простой доступ, но потеря нативного proposal/review/audit | Отклонено |
| Прямой push после публикации | Быстрее изменения, но bypass review и нарушение I01/I02 | Запрещено |

## Consequences

### Positive

- Одна история документа, proposal, decision и publication без dual canonical stores.
- Clone/mirror и Git ancestry дают переносимость и проверяемый rebuild.
- Open WebUI остаётся тонкой оболочкой; GitLab переиспользует редакционные возможности.
- Реальный merge commit и decision anchors сохраняют атрибуцию вне GO DB.

### Negative

- Нет realtime collaboration и silent last-write-wins.
- Запись и canonical read зависят от GitLab; конфликты требуют понятного UX.
- Merge parentage, note/tag durability и recovery сложнее простого status update.
- History retention/privacy deletion требуют отдельного privileged design.

### Cost

- Нужны GO, GitLab capability validation, reconciliation и CI/index rebuild.
- Переносимый audit требует notes/tags/manifests и backup GitLab metadata, а не только файлов.
- Трудоёмкость v1.1 отозвана; новая оценка выполняется после T00, этот ADR её не задаёт.

## Verification / T00 evidence

- **T00:** pin Open WebUI baseline и GitLab version/edition; проверить exact-SHA reads, MR merge по exact source SHA, conflicts/idempotency, protected branches/tags, merge commit message/trailers, note IDs, scoped tokens и audit/metadata export.
- Доказать на synthetic repository: до merge `main` unchanged; новый commit/rebase сбрасывает approval; concurrent/stale merge даёт conflict и ноль writes; revert-MR создаёт новую историю без rewrite.
- Удалить/пересоздать disposable projections в test environment и восстановить Git-derived current state из commits, MR notes/tags и merge trailers. Transient failure не считается доказательством отсутствия merge.
- Проверить отсутствие pending/rejected content в published index, stable IDs после rename, attachments revision/ACL и clone/manifest closure.
- Все неподтверждённые GitLab capabilities остаются UNKNOWN/BLOCKED до design review. **Текущее состояние:** baseline не выбран, интеграционные проверки не выполнялись, production не разрешён.

## Related contracts

- Front matter/document identity, ProposalRecord/ProposalVersion, DecisionRecord, CutoverRecord.
- Full SHA conventions, merge parentage и trailers `Decision-ID`, `Decision-Note-ID`, `Decision-Hash`, `Approved-by`.
- MR append-only note, protected annotated `kb-decisions/<decision_id>`, decisions manifest.
- GO Git adapter, rebuildable `kb_authz`/`kb_ops`/`kb_index`, clone/mirror/assets manifests.
- [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-11](ADR-011-two-phase-publication.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-13](ADR-013-merge-serialization-recovery.md), [ADR-14](ADR-014-canonical-decision-record.md), [ADR-16](ADR-016-repository-per-space.md).
