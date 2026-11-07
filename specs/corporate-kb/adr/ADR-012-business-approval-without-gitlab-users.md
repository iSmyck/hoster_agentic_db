# ADR-12 — Business approval without GitLab users

**ID/Title:** ADR-12 / Бизнес-согласование без GitLab user records  
**Status:** **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00**. Не является production security approval.  
**Date:** 2026-11-06  
**Requirements/AD links:** R05, R07–R10, R16, R18; I03–I07, I12; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-2, AD-4–AD-7, AD-12, AD-13; [spec.md](../spec.md): раздел 5, T03, T05–T07.

## Context

Бизнес-владельцы должны принимать решения, **не имея GitLab user records вообще**. Следовательно, GitLab не может аутентифицировать их или нативно фиксировать их business approval. Использование shadow accounts, общих пользователей или подмены actor bot identity разрывает attribution и self-approval prohibition.

CODEOWNERS в информационном content-standard ранее обозначал владельцев папок. Для платформенной безопасности authority уточняет: CODEOWNERS остаётся **только инженерным ownership/review контуром** и не является источником business authorization. Нужен versioned policy, который связывает внешние группы и path-scoped approver roles, а GO выполняет merge отдельной service identity после повторной проверки.

## Decision

1. Бизнес-пользователи и owners существуют только в upstream/platform identity, нормализованной ADR-10. **GitLab user records для них не создаются.** Business decisions атрибутируются trusted `stable_id` в ProposalRecord, DecisionRecord, GO audit и Git merge metadata.
2. Versioned **`approval-policy.yaml`** в Git отображает внешние AD/OIDC groups на path-scoped approver roles. Path matching нормализует разделители, Unicode и запрещает `..`; policy не является secret, credentials остаются в deployment secrets.
3. MVP требует **одного approver**, который не совпадает ни с `author_stable_id`, ни с `version_author_stable_id`, ни с `requester_stable_id`. Совпадение человека в любой из этих ролей запрещает self-approval. Multiple approvers/quorum вне MVP.
4. Append-only ProposalRecord каждой версии содержит как минимум:
   - `author_stable_id`, `version_author_stable_id`, `requester_stable_id`, `actor_type`, optional `run_id`;
   - `rationale`, `evidence[]`, `proposal_sha`, `base_sha`;
   - idempotency metadata и необходимые proposal/version identifiers.
   GitLab bot/service identity не заменяет эти поля.
5. Редактирование proposal создаёт новую ProposalVersion/`version_author_stable_id` и новый `proposal_sha`; старый approval недействителен. Новый version author не может утвердить собственную версию. Rebase также требует новой проверки.
6. GO — единственный business merge orchestrator. После cutover только его merge service identity имеет GitLab merge permission; все business и engineering final applies сериализуются ADR-13. Credential недоступен browser, agent, CI/indexer или connector.
7. Непосредственно перед merge GO использует один `policy_bundle_id` и согласованные access/approval revisions, повторно проверяет:
   - текущее external group membership и `stable_id` approver;
   - path scope и self-approval prohibition по всем трём ролям;
   - exact source `proposal_sha` и `target HEAD == base_sha`;
   - достоверность review/preview и отсутствие target recovery barrier.
   Несовпадение даёт conflict/forbidden и **ноль writes в `main`**.
8. Merge commit содержит `Approved-by` со стабильной атрибуцией approver и Decision trailers по ADR-14. Non-error GitLab response без подтверждённого merge commit не доказывает публикацию.
9. **CODEOWNERS — engineering only.** Он может задавать инженерных владельцев/review checks в пределах фактической GitLab edition, но не заменяет `approval-policy.yaml` и не авторизует бизнес-владельца. Engineering review выполняется в GitLab UI, final apply — через GO.
10. Бизнес-статусы/ownership в platform UI выводятся из Git/MR, `approval-policy.yaml` и platform policy, а не приписываются CODEOWNERS как бизнес-источник.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Создать owners GitLab accounts | Нативные approvals, но нарушает принятую identity boundary и увеличивает лицензирование/управление | Отклонено |
| Shadow/shared GitLab users | Внешне просто, но actor подменяется и audit недостоверен | Запрещено |
| CODEOWNERS как business authorization | Путь ownership уже знаком, но требует GitLab identity и смешивает инженерный контур | Отклонено; engineering only |
| Доверять approver из browser/request | Меньше серверных проверок, но позволяет подмену actor и self-approval | Запрещено |
| Merge напрямую человеком после platform review | Меньше GO, но невозможен без GitLab user и единой сериализации | Отклонено |
| Несколько approvers/quorum в MVP | Больше гибкость, но сложнее policy и acceptance | Вне MVP; отдельные требования/ADR |

## Consequences

### Positive

- Отсутствуют shadow accounts и зависимость business governance от GitLab edition.
- Approval привязан к человеку, внешней группе, path и exact version.
- Self-approval закрыт для исходного автора, редактора версии и requester.
- Единый GO credential и policy bundle дают проверяемый merge/audit path.

### Negative

- GO и Identity/AuthZ adapter становятся критическими для публикации.
- Изменение proposal требует нового независимого review.
- Нативный GitLab approval не отражает business decision; нужна отдельная нотация DecisionRecord/trailers.

### Cost

- Нужны versioned policy engine, group recheck, path normalization, platform review и Git metadata mapping.
- Требуются concurrency/revocation tests и эксплуатационная защита единственного merge credential.

## Verification / T00 evidence

- **T00:** проверить external group recheck, upstream grants, exact-SHA merge, merge trailers/note IDs, protected branch rules и token без merge на реальном sandbox baseline. Неподтверждённые GitLab semantics не выдавать за готовые.
- Матрица self-approval: approver = author; approver = version author; approver = requester; совпадение нескольких ролей — все отклоняются. Разный eligible approver из действующей группы проходит.
- Удаление approver из группы или изменение path scope между review и merge → forbidden, ноль `main` writes. Новый commit/rebase сбрасывает approval.
- Проверить Unicode/separator/`..` path cases, согласованность policy bundle/revisions и отказ при stale base/proposal SHA.
- Доказать отсутствие GitLab user requirement для business owner и невозможность получить merge credential через browser/agent/CI/connector. CODEOWNERS не расширяет business rights.
- **Текущее состояние:** реальные identity/GitLab integration tests не выполнялись; design acceptance не является security gate PASS.

## Related contracts

- `approval-policy.yaml`, access policy, `policy_bundle_id`, full access/approval revision SHA.
- ProposalRecord/ProposalVersion actor fields, evidence, idempotency metadata.
- AuthzContext и immediate group/path recheck; DecisionRecord `Approved-by` linkage.
- GO merge service identity, protected `main`, per-target serialization/recovery.
- [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-09](ADR-009-platform-review-ux.md), [ADR-10](ADR-010-ldap-oidc-identity.md), [ADR-13](ADR-013-merge-serialization-recovery.md), [ADR-14](ADR-014-canonical-decision-record.md), [ADR-16](ADR-016-repository-per-space.md).
