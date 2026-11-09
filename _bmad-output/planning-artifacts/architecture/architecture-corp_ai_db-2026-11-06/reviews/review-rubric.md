# Independent good-spine rubric review — итерация 3

Дата: 2026-11-06  
Объект: `../ARCHITECTURE-SPINE.md`  
Источники: `specs/corporate-kb/spec.md` v1.2, `specs/corporate-kb/content-standard.md` v2.2, актуальные spine и `.memlog.md`.

## Verdict

**PASS по architecture-spine rubric — CRITICAL/HIGH blockers не остались.**

Это не отметка об owner approval и не подтверждение GitLab/Open WebUI capabilities: pinned baseline и sandbox evidence остаются обязательными результатами T00/G0. Сам spine теперь формулирует согласованные, проверяемые invariants без прежних архитектурных блокеров.

Повторный deterministic lint: `ok=true`, `total_findings=0`.

## Проверка прежних blockers

| Прежний blocker | Статус | Доказательство в актуальном spine |
|---|---|---|
| F-01 CRITICAL: crash освобождает lock во время in-flight merge | **RESOLVED** | AD-7 в одной DB transaction **до внешнего merge call** устанавливает `merge_attempted` и per-target `recovery_required`. Barrier блокирует все новые merges target после crash/fencing до conclusive target-wide reconciliation. Timeout не снимает barrier, недоказуемый outcome остаётся quarantined. Другой MR больше не может использовать окно неизвестного исхода. |
| F-02 HIGH: editor self-approval и неполный ProposalRecord | **RESOLVED** | AD-6 требует append-only ProposalRecord каждой версии с `version_author_stable_id`, исходным author/requester, rationale, evidence, exact SHAs и idempotency metadata. AD-6/AD-13 запрещают редактору approve собственной версии и создают новую ProposalVersion при edit. |
| F-03 HIGH: неоднозначный policy revision | **RESOLVED** | AD-6/AD-7/AD-12 и Policy convention используют `policy_bundle_id` + согласованные `access_policy_revision` и `approval_policy_revision`. Bundle идентифицирует repository+paths; IAM, GO, AuthzContext и DecisionRecord используют один набор revisions. |
| F-04 HIGH: Physical Space mapping в Deferred | **RESOLVED** | AD-4 фиксирует один GitLab repository = один Space. ACL, blobs, history, protected branch, credentials, cutover, index и export имеют единый периметр. Deferred:203 оставляет только provisioning details, не mapping. |
| F-05 HIGH: AD-3/AD-9 preflight contradiction | **RESOLVED** | AD-9 явно разрешает inactive cutover preflight на exact `cutover_sha` и запрещает retrieval из него до активации Space. AD-3 и AD-9 образуют согласованную последовательность. |

## Проверка новых правил

### DecisionRecord и recovery

- AD-1/AD-7 сохраняют один canonical JSON в append-only MR note и protected annotated tag `kb-decisions/<decision_id>` на `proposal_sha`.
- Tag содержит полный JSON и является Git-native durability anchor не только для accept/merge, но и reject/cancel; MR note является API/UI representation.
- Missing/mismatched note или tag делает decision invalid. Исправление создаёт новый `decision_id` со `supersedes_decision_id`, не перезаписывая историю.
- Merge reconciliation проверяет note/tag/trailers, first parent=`base_sha`, second parent=`proposal_sha`. Это закрывает не только source substitution, но и ложный `merged` для merge commit на другой базе.
- Идемпотентность по `decision_id` и `(repository_id, target_branch, proposal_sha)` предотвращает повторную публикацию той же версии.

### Merge shape

- Squash, automatic rebase и fast-forward запрещены; реальный merge commit обязателен.
- Parentage делает reviewed target base и proposal SHA проверяемыми после timeout/crash.
- Все post-cutover merges по-прежнему идут только через GO; agent/connector/LLM auto-merge запрещён.

### Index snapshot

- Единственный CI/index writer сериализует active pointer per Space/generation/profile.
- `index-snapshot-v1` различает `snapshot_sha`, `document_revision_sha`, blob/content hash и dependency hash.
- Incremental run публикуется только при эквивалентности полного dependency closure full snapshot на том же `main_sha`; это закрывает stale links/attachments/deletions при incremental indexing.
- Pending/rejected и preflight content не обслуживаются как published; retrieval повторно авторизует payload и отклоняет stale revision.

### Space и export

- Один repository = один Space устраняет прежнюю неоднозначность folder-level ACL/export.
- Full clone требует export permission на Space и всю его историю; filtered export/history removal требуют отдельного privileged workflow.
- Decision tags входят в clone, а decisions/assets manifests и snapshot closure проверяются при restore.

## Good-spine checklist

| Критерий | Оценка | Комментарий |
|---|---|---|
| Реальные divergence points для E00–E08 | **PASS** | Merge/recovery, decision/proposal durability, Space perimeter, policy snapshots и index activation согласованы между эпиками. |
| Enforceable Binds/Prevents/Rule | **PASS** | Прежние неисполнимые утверждения заменены проверяемыми barriers, parentage, hashes, tags и snapshot equivalence. |
| Deferred без несовместимости | **PASS** | Space mapping больше не Deferred. Оставшиеся Deferred относятся к baseline, provisioning, моделям, benchmarks и owner thresholds. |
| Технологии не выдуманы | **PASS на уровне spine / T00 для evidence** | Protected annotated tags, merge commits, MR notes и PostgreSQL locks используются по назначению; target-version capabilities явно обязательны к проверке. |
| Покрытие R01–R18 | **PASS** | Все требования имеют architecture owner и enforceable invariant; неблокирующие улучшения перечислены ниже. |
| Покрытие I01–I14 | **PASS** | Merge/push boundary, exact reviewed SHA/base, recovery, ACL, rebuild, late-job guards, attachments и UI states покрыты. |
| Deployment/environments/operations | **PASS** | Dedicated client isolation, Local/T00, Integration test, backup/restore/upgrade и operational metrics присутствуют. Детализация alert ownership остаётся MEDIUM, не blocker. |
| Brownfield ratification | **OPEN / T00** | До pinned checkout нельзя подтвердить code seams; spine корректно не выдаёт их за доказанные. |

## Оставшиеся MEDIUM — не blockers G0 spine

Эти пункты сохранены из предыдущих итераций и не расширяют исходный R/I scope.

| ID | Область | Оставшееся уточнение | Autofix перед соответствующим эпиком |
|---|---|---|---|
| M-01 | AD-7 / State | После уже выполненного merge `invalid` из-за note/tag mismatch смешивает publication outcome и audit integrity. | Разделить `publication_state=merged/...` и `audit_state=valid/invalid`; post-merge invalid вызывает incident, но не автоматический повторный merge/rollback. |
| M-02 | AD-3/AD-4/AD-6 и источники | No-auto-merge, отказ от front matter `access` как auth source и business approval-policy вместо CODEOWNERS требуют явной нормативной синхронизации. | Связать с ADR/supersession и обновить spec/content-standard отдельной задачей после owner decision. |
| M-03 | AD-12 / Deferred:201 | OIDC `sub` не scoped issuer/provider; fresh group recheck и revocation budgets требуют provider-specific проверки. | Использовать provider/directory+issuer+subject identity scope; проверить fail-closed recheck и refresh/subscription budgets ≤30 минут в T00/T03. |
| M-04 | AD-9/AD-13/AD-15/AD-16 | Citation correctness оценивается, но общий SourceRef не назван явно. | В T01/T09 зафиксировать document ID+full SHA+section/range/hash и attachment version/hash+page/slide в tool/UI contracts. |
| M-05 | AD-9/AD-10/AD-13 | Archive descendants, `valid_until` и feedback owner queue не детализированы в spine. | Зафиксировать в T02/T10/T15 MR transitions, descendant/replacement rules, index purge и expiry/feedback tests. |
| M-06 | AD-11/AD-16 / Environments | Есть metrics и restore/upgrade evidence, но не назначены alert owners/runbooks и rehearsal environment. | В T18 определить alert→owner/runbook, degraded-mode runbooks, online/CI budgets и Integration/client-staging rehearsal. |

## LOW

**L-01 — I-traceability.** Frontmatter и Capability Map перечисляют R, но не дают компактную таблицу I01–I14 → AD/enforcement/test. Добавить её в T01 contracts/traceability, не раздувая spine.

## R/I итог

- **R01–R18:** покрыты на уровне architecture spine.
- **I01–I14:** покрыты; прежние I03/I06/I07 gaps закрыты version author, recovery barrier, parentage и durable decision tags.
- **Новых CRITICAL/HIGH противоречий не обнаружено.**

## Обязательное T00/T01 evidence, не являющееся новым scope

1. Protected annotated tag creation/protection, полный JSON в annotation, tag refs в clone/export и поведение при missing/mismatched note/tag.
2. GitLab merge commit trailers, parent order, запрет squash/rebase/fast-forward и merge-only-GO effective branch/token rules на pinned version/edition.
3. Chaos test двух разных MR: crash после принятия GitLab merge, потеря advisory lock, попытка второго merge. `recovery_required` обязан удерживать target до conclusive reconciliation; иначе target остаётся quarantined.
4. Rebuild `kb_ops` из GitLab: unresolved canonical accept/reject/cancel decisions и merge outcomes восстанавливаются без второго merge; отсутствие доказанного исхода не снимает quarantine.
5. Inactive preflight на exact `cutover_sha` не доступен retrieval до activation.
6. Для `index-snapshot-v1`: incremental links/attachments/deletions сравниваются с full snapshot на том же `main_sha`; late run не активирует старую generation/profile.
7. T01 добавляет I01–I14 → acceptance A01–A26 traceability и negative/concurrency tests в существующий harness.
