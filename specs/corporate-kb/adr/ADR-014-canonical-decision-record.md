# ADR-14 — Canonical DecisionRecord

**ID/Title:** ADR-14 / Каноническая запись решения и пересобираемая GO projection  
**Status:** **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00**. Физическая неизменяемость GitLab notes/tags и metadata capabilities не считаются доказанными до audit.  
**Date:** 2026-11-06  
**Requirements/AD links:** R07–R10, R14, R18; I05–I07, I10; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-1, AD-6, AD-7, AD-11; [spec.md](../spec.md): T05, T07, T13.

## Context

Решение владельца должно переживать потерю PostgreSQL и однозначно связывать человека, exact proposal/base revisions, policy и merge result. Запись только в GO DB теряет audit; файл в proposal branch меняет `proposal_sha` и инвалидирует reviewed version; одна MR note не попадает в обычный Git clone и зависит от API retention/mutation semantics.

Нужны Git-native durability anchor для accept/reject/cancel, API/UI representation, криптографическая связь с merge trailers и пересобираемая projection. При этом append-only является протокольным требованием, а не автоматически доказанным физическим WORM-свойством GitLab.

## Decision

1. До применения решения GO создаёт **один canonical DecisionRecord JSON** с как минимум:
   - `decision_id` — UUID и idempotency key;
   - `proposal_sha`, `base_sha`, `action`;
   - actor `stable_id`, UTC RFC 3339 timestamp, `evidence`;
   - `policy_bundle_id`, `access_policy_revision`, `approval_policy_revision`.
   Для accept action применяются approver rules ADR-12; reject/cancel также получают durable DecisionRecord.
2. Одинаковые canonical payload и связанный **`record_sha256`** записываются в:
   - **append-only structured MR note от GO** — API/UI representation;
   - **protected annotated tag `kb-decisions/<decision_id>`** (то есть `kb-decisions/<uuid>`), указывающий на `proposal_sha`, — полный Git-native durability anchor, включаемый в clone.
   DecisionRecord не помещается файлом в proposal branch и не меняет `proposal_sha` после создания.
3. Note и tag содержат один и тот же полный record/hash. **Missing или mismatched note/tag делает decision `invalid`.** Исправление не редактирует старую запись: создаётся новый `decision_id` со `supersedes_decision_id`.
4. Accepted merge commit содержит trailers:
   - `Decision-ID` = `decision_id`;
   - `Decision-Note-ID` = идентификатор canonical MR note;
   - `Decision-Hash` = `record_sha256`;
   - `Approved-by` = стабильная атрибуция approver.
   Parentage проверяется ADR-13. Для reject/cancel merge commit не требуется; MR закрывается, а note/tag остаются anchors.
5. Append-only означает запрет product-level update/delete и обнаружение mismatch. T00 обязан проверить фактические note ID/audit/mutation и protected annotated tag semantics. До этого record не называется физически immutable хранилищем.
6. Обязательный **decisions manifest** для export включает полные DecisionRecords, hashes и необходимые MR metadata/связи note/tag/merge. Он компенсирует то, что MR notes не являются обычными Git objects, и позволяет проверить closure; canonical anchors при этом не заменяются manifest.
7. GO projection имеет `unique(decision_id)` и disposable состояния `recorded → merge_attempted → merged/failed/conflicted/invalid`. Полная пересборка восстанавливает Git-derived current state из MRs, notes, tags и merge commits. Transient attempt timestamps/errors могут быть disposable.
8. **Disposable projection не отменяет safety barrier ADR-13.** При rebuild нельзя молча сбросить `merge_attempted`/`recovery_required` с неизвестным outcome: target остаётся blocked/quarantined до conclusive reconciliation. Только проверенный merge commit в `main` подтверждает `merged`.
9. Повтор того же `decision_id` или уже применённого `(repository_id, target_branch, proposal_sha)` возвращает существующий Git-derived результат. Детерминированная serialization/canonicalization и точный hash input фиксируются контрактом до реализации; этот ADR не выдумывает алгоритм или schema version.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Decision только в PostgreSQL | Простые queries, но потеря БД уничтожает canonical audit | Отклонено |
| Decision-файл в proposal branch | Удобный Git diff, но новый commit меняет reviewed SHA | Запрещено |
| Только MR note | Доступно API/UI, но не входит в clone и зависит от metadata retention/mutation | Недостаточно |
| Только annotated tag | Git-native clone, но менее удобен MR API/UI | Недостаточно; нужен и note |
| Mutable correction старой записи | Простое редактирование, но разрывает hash/audit/trailers | Запрещено; только supersedes |
| Projection как источник terminal truth | Быстрый status, но расходится с Git при timeout/crash | Отклонено |

## Consequences

### Positive

- Decision, exact revisions, policy и actor проверяются без GO DB.
- Clone сохраняет protected tag anchor, а manifest обеспечивает MR metadata closure.
- Duplicate merge подавляется stable idempotency identity и hash linkage.
- Accept/reject/cancel используют единый durable audit contract.

### Negative

- Два representations требуют mismatch detection и reconciliation.
- Невозможность исправить note/tag требует supersedes-цепочек.
- Недоступность нужных GitLab capabilities может заблокировать design.

### Cost

- Нужны note/tag adapter, deterministic hashing, manifest generation и projection rebuild.
- Protected tags и metadata увеличивают backup/export scope и число integration/failure tests.

## Verification / T00 evidence

- **T00:** проверить создание append-only structured note от GO, стабильный note ID, audit/mutation behavior, protected annotated tags на arbitrary `proposal_sha`, включение tag в clone, merge commit trailers и metadata export на выбранном GitLab baseline.
- Unit/contract tests: одинаковый canonical bytes/hash для note/tag/manifest/trailer; изменение payload, missing note/tag, wrong tag target или note ID → `invalid`; correction создаёт новый UUID и `supersedes_decision_id`.
- Accept/reject/cancel fixtures подтверждают tag на exact `proposal_sha`; accept дополнительно связывает merge parentage/trailers, reject/cancel закрывают MR без ложного merge.
- Смоделировать потерю disposable GO projection в test environment и выполнить rebuild. Проверить Git-derived current state и отсутствие автоматического снятия unknown recovery barrier.
- Clone + decisions manifest на clean environment: каждая запись/hash/MR linkage и внешний merge trailer сходятся; нельзя объявить полный restore при отсутствующей note metadata.
- **Текущее состояние:** GitLab note/tag/trailer/export capabilities не проверены; mocked note не является integration evidence.

## Related contracts

- DecisionRecord JSON, deterministic serialization и `record_sha256`; `supersedes_decision_id`.
- Structured MR note, `Decision-Note-ID`, protected annotated `kb-decisions/<decision_id>` на `proposal_sha`.
- Merge trailers `Decision-ID`, `Decision-Note-ID`, `Decision-Hash`, `Approved-by`; first/second parent rules.
- Decisions manifest + required MR metadata; GO projection `unique(decision_id)` и rebuild/reconciliation.
- [ADR-06](ADR-006-portability-retention.md), [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-13](ADR-013-merge-serialization-recovery.md), [ADR-15](ADR-015-postgresql-schema-ownership.md).
