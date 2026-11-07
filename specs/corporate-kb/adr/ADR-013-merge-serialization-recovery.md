# ADR-13 — Merge serialization and recovery

**ID/Title:** ADR-13 / Сериализация merge, parentage и восстановление после сбоя  
**Status:** **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00**. Не является production readiness/security approval.  
**Date:** 2026-11-06  
**Requirements/AD links:** R06–R10, R16, R18; I01–I07, I10, I11; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-2, AD-5–AD-7, AD-13, AD-16; [spec.md](../spec.md): T05, T06, A08–A10.

## Context

Проверка `base_sha` и последующий merge образуют TOCTOU, если два applies или независимые writers меняют target. GitLab timeout/non-error response не доказывает ни наличие, ни отсутствие merge. Blind retry с новым decision ID может создать повторную публикацию, а локальный `failed` — ложно заявить, что `main` не изменился.

Дополнительная сложность — crash после внешнего merge call, но до записи projection, а также потеря advisory lock новым GO owner. Lock сам по себе не сохраняет информацию о неизвестном outcome. Нужен durable per-target barrier, Git-derived reconciliation и однозначная merge parentage, позволяющая отличить reviewed proposal от squash/rebase/fast-forward результата.

## Decision

1. **Все business и engineering merges выполняются только через GO.** После cutover ни человек, ни другой сервис не имеет direct merge permission. Это исключает side writer, который мог бы изменить target вне сериализации GO.
2. GO сериализует critical sections **per repository/target branch** через advisory lock с owner и fencing token. Critical section короткий: required rechecks и merge coordination; locks не удерживаются во время LLM calls или human review.
3. Перед merge GO повторно проверяет approver/groups/path scope, один policy bundle и revisions, exact source `proposal_sha`, отсутствие более новой ProposalVersion и `target HEAD == base_sha`. Mismatch даёт `conflicted`/`invalid`/forbidden и ноль writes в `main`.
4. До merge существует canonical DecisionRecord по ADR-14. **В одной DB transaction непосредственно перед external merge call** GO переводит decision в `merge_attempted` и устанавливает durable per-repository/target **`recovery_required`**. Barrier сохраняется независимо от последующего lock loss, crash или fencing.
5. `recovery_required` блокирует **все новые merges данного target**, а не только повтор того же MR. Новый lock owner обязан выполнить target-wide reconciliation и доказать исход каждого in-flight attempt до снятия barrier. Timeout, истечение lock или смена owner не очищают его.
6. Squash, automatic rebase и fast-forward запрещены. Accepted publication создаёт **реальный merge commit**, у которого:
   - first parent = `base_sha`;
   - second parent = `proposal_sha`;
   - `Decision-ID`, `Decision-Note-ID`, `Decision-Hash`, `Approved-by` совпадают с canonical note/tag и approver.
   Только такой проверенный commit, присутствующий в `main`, подтверждает `merged`.
7. Projection использует `unique(decision_id)` и состояния `recorded → merge_attempted → merged/failed/conflicted/invalid`. `failed` не доказывает отсутствие merge. Terminal truth выводится из GitLab, а не из локального status или HTTP response.
8. Повтор с тем же `decision_id` либо уже применённым `(repository_id, target_branch, proposal_sha)` возвращает существующий **Git-derived результат** и не вызывает новый merge. Timeout после `merge_attempted` не разрешает blind retry с новым decision ID.
9. Reconciliation проверяет target ancestry, first/second parents, trailers, MR state, note/tag/hash и exact SHAs. Conclusive merged/failed/conflicted/invalid результат фиксируется в projection; недоказуемый outcome остаётся **quarantined**, а target barrier активен.
10. До DecisionRecord безопасен retry создания той же операции по idempotency contract. После record, но до merge retry использует тот же `decision_id`; после неизвестного external outcome сначала выполняется reconciliation. Полная rebuild/recovery не должна молча очищать неизвестный attempt.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Merge без per-target lock | Меньше GO state, но concurrent target advance и duplicate applies | Отклонено |
| Только advisory lock без durable barrier | Простая HA, но новый owner забывает in-flight outcome после crash | Отклонено |
| Blind retry после timeout | Простой клиентский flow, но возможен duplicate merge | Запрещено |
| Считать non-error response успехом | Меньше reconciliation, но ложный merged при потере commit/metadata | Запрещено |
| Fast-forward/squash для линейной истории | Проще history, но теряется обязательная base/proposal/decision parentage | Запрещено |
| Automatic rebase перед merge | Уменьшает conflicts, но меняет reviewed `proposal_sha` и approval | Запрещено |
| Автоматически снимать barrier по timeout | Быстро восстанавливает throughput, но публикует при неизвестном outcome | Запрещено |

## Consequences

### Positive

- Target race закрыт и credential boundary, и сериализацией, и exact HEAD checks.
- Crash на любом участке не требует угадывания: Git даёт доказательство результата.
- Duplicate apply возвращает прежний результат без второй публикации.
- Merge parentage/trailers позволяют независимо проверить reviewed base/proposal/decision.

### Negative

- Один неизвестный outcome останавливает все merges target до conclusive reconciliation.
- Реальные merge commits увеличивают сложность истории по сравнению с fast-forward.
- GO и `kb_ops` recovery state критичны для availability записи.

### Cost

- Нужны fencing, durable barrier, target-wide Git reconciliation и quarantine UX/runbooks.
- Crash/fault-injection и concurrent integration tests обязательны на реальном GitLab; они сложнее happy-path tests.

## Verification / T00 evidence

- **T00:** подтвердить на целевой GitLab version/edition merge exact source SHA, configurable merge commit trailers, first/second parent semantics, отключение squash/rebase/FF в managed path, protected merge-only-GO и чтение MR/note/audit после timeout.
- Concurrent test двух независимых clients и двух proposals: один merge; второй получает conflict при изменённом HEAD; одновременный retry того же decision возвращает один Git-derived результат.
- Fault injection вокруг каждого boundary: до DecisionRecord; после record; после DB `merge_attempted`/`recovery_required`; во время external call; после merge до response; после response до projection. Ни один сценарий не создаёт duplicate или ложный `merged`.
- Потерять lock/owner после unknown outcome: новый owner не выполняет новые merges target, пока target-wide reconciliation не завершён. Недоказуемый случай остаётся quarantined.
- Проверить first parent = `base_sha`, second parent = `proposal_sha`, все trailers/note/tag/hash; любой mismatch — не `merged`. `failed` при недоступном GitLab не считается доказательством отсутствия merge.
- Mock GitLab допустим для unit fault matrix, но **не заменяет sandbox integration PASS**. Текущее состояние: реальные проверки не выполнялись.

## Related contracts

- GO per-repository/target advisory lock: owner, fencing token, durable `recovery_required`.
- Decision states `recorded`/`merge_attempted`/`merged`/`failed`/`conflicted`/`invalid`, `unique(decision_id)`.
- Merge key `(repository_id, target_branch, proposal_sha)`, exact `base_sha`/`proposal_sha`, idempotent replay.
- Real merge parentage и Decision trailers; target-wide reconciliation/quarantine.
- [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-14](ADR-014-canonical-decision-record.md), [ADR-15](ADR-015-postgresql-schema-ownership.md).
