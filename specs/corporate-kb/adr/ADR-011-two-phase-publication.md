# ADR-11 — Two-phase publication

**ID/Title:** ADR-11 / Двухфазная начальная публикация и cutover  
**Status:** **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00**. Не разрешает production migration, corpus load или rollout без отдельных owner approvals.  
**Date:** 2026-11-06  
**Requirements/AD links:** R06, R07, R11–R13, R16, R18; I01, I02, I06, I08, I14; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-1–AD-3, AD-9, AD-10, AD-13, AD-16; [content-standard.md](../content-standard.md): части A–C; [spec.md](../spec.md): T12.

## Context

ETL и первичная сборка требуют контролируемого bulk load без per-page MR, тогда как после публикации I01/I02 требуют protected `main` и MR-only writes. Одновременно нельзя открыть пользователям непроверенный corpus или собрать published index до экспертного sign-off. Граница должна быть объективной, привязанной к exact SHA и не оставлять окна прямого push.

Более ранние положения о возможном auto-merge доверенной source-managed синхронизации противоречат выбранному coaching решению. Authority фиксирует: после cutover agent/connector/LLM auto-merge запрещён для всех managed changes, включая детерминированную синхронизацию.

## Decision

### Фаза 1 — до cutover

1. Import dry-run выполняется заранее **без canonical writes** и возвращает path→ID map, provenance, links/attachments, source version/hash и ошибки. Повтор по hash/version — no-op; unsupported inputs и потери явно попадают в report.
2. Archive traversal, symlinks, executable HTML/MDX, secrets, `.git`/служебные исключения и oversized inputs отклоняются. Файл без владельца и завершённого data barrier не передаётся в corpus.
3. Controlled engineering bulk push допустим **только** в unpublished `main`, когда пользовательский доступ закрыт и published index отсутствует. Это единственный write-path первичной сборки; per-page MR в этой фазе не требуется.
4. Экспертная валидация является гейтом публикации: объём/выборка/расхождения и sign-off фиксируются в validation evidence. Critical content проверяется по content-standard; LLM comparison не заменяет требуемую человеческую проверку.
5. До cutover фиксируется **CutoverRecord**, связывающий Space, exact `cutover_sha` (`main_sha`), validation evidence, sign-off actor `stable_id` и UTC timestamp. Validation tag/record должен относиться к тому же exact SHA.

### Cutover и фаза 2 — после публикации

6. Cutover сначала включает **write freeze** и повторно требует `HEAD == cutover_sha`. Несовпадение останавливает cutover; нельзя подписать один corpus, а опубликовать другой.
7. Затем создаются protected cutover/validation tag и MR-only branch rules; merge permission остаётся только у merge service identity GO. После этого прямой push закрыт для людей, ИИ-команды, agent, connector и других сервисов.
8. CI строит **inactive preflight index** на exact `cutover_sha`. Preflight не обслуживает retrieval и не считается published index. Только после успешного preflight и подтверждения всех protections активируются Space, пользовательский доступ и published index pointer.
9. После cutover любые managed changes — через GO и MR с human merge. **Auto-merge запрещён**, включая agent/connector/LLM и source-managed детерминированную синхронизацию. Cursor продвигается только после durable proposal/merge result по source update contract.
10. Ошибка после cutover исправляется новым reviewed MR; restore — revert-MR/new commit. Не выполняется history rewrite или возврат к незащищённому bulk path.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Per-page MR для всей первичной сборки | Единый процесс, но большой review overhead до существования published corpus | Не требуется в unpublished фазе |
| Bulk push после открытия доступа | Быстрый import, но bypass review и непроверенный retrieval | Запрещено |
| Сначала опубликовать, затем валидировать | Быстрый запуск, но пользователи/модель получают непроверенный corpus | Запрещено |
| Auto-merge trusted source-managed | Меньше ручной работы, но agent/connector publication bypass | Запрещено после cutover |
| Freeze без exact SHA check | Простой lock, но sign-off может относиться к другому содержимому | Недостаточно |
| Preflight как активный search index | Раньше видим результат, но нарушает активационный gate | Запрещено |

## Consequences

### Positive

- Первичная сборка остаётся практичной без постоянного исключения из MR-only модели.
- Sign-off, canonical SHA, protections и index связаны одной воспроизводимой цепочкой.
- Пользователи и retrieval не видят corpus до успешной активации.
- Устранены auto-merge и незащищённое окно публикации.

### Negative

- Cutover требует координированного freeze и останавливает запись при расхождении HEAD.
- Ошибка preflight откладывает доступ; после protection исправления уже требуют MR.
- Повторные source updates требуют человеческого merge даже при детерминированном diff.

### Cost

- Нужны dry-run/reporting, validation evidence, CutoverRecord, branch/tag automation и inactive index management.
- Экспертная валидация и повторный human review являются постоянной операционной работой; сроки и бюджет не оцениваются этим ADR.

## Verification / T00 evidence

- **T00:** проверить на выбранной GitLab version/edition protected branch/tag rules, merge-only-GO token semantics, exact SHA refs, webhook/CI ordering и возможность закрыть все direct merge/push paths. Неподтверждённые capabilities — UNKNOWN/BLOCKED.
- Dry-run на synthetic malicious fixtures: traversal, symlink, executable HTML/MDX, secret-like files, oversized/unsupported inputs; доказать отсутствие canonical writes и корректный path→ID/provenance report.
- Race test: изменить HEAD после sign-off/freeze → cutover останавливается на `HEAD != cutover_sha`, активация и published index не происходят.
- Проверить последовательность: validation record/tag → protection/GO-only merge → inactive preflight exact SHA → activation. До activation retrieval/user access denied.
- После cutover детерминированно отклонить direct push и auto-merge от agent, connector, engineering identity и LLM path; любое изменение требует GO/MR/human merge.
- **Текущее состояние:** production corpus не создавался, migration не выполнялась, реальные GitLab/CI checks отсутствуют.

## Related contracts

- Import dry-run manifest, path→ID map, provenance, data barrier и validation evidence.
- CutoverRecord: Space, exact `cutover_sha`, evidence, sign-off actor, timestamp; protected cutover/validation tag.
- `IndexRequested`/preflight snapshot, Space activation и published pointer.
- MR-only protected `main`, GO merge credential, source cursor durable states.
- [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-05](ADR-005-index-delivery.md), [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-13](ADR-013-merge-serialization-recovery.md), [ADR-16](ADR-016-repository-per-space.md).
