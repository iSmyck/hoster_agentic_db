# ADR-09 — Platform review UX

**ID/Title:** ADR-09 / Review UX владельца в платформе  
**Status:** **Accepted** по spec решением владельца от 2026-11-06; дополнен decision/review semantics во время architecture coaching. Реализация зависит от результатов T00/G0; конкретный editor/component — **Proposed/UNKNOWN** до audit.  
**Date:** 2026-11-06  
**Requirements/AD links:** R01–R03, R05, R07–R10, R13, R16, R18; I03, I05, I06, I09, I14; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-2, AD-4, AD-6, AD-7, AD-13; [spec.md](../spec.md): T07–T09, A06–A08, A22–A23.

## Context

Бизнес-владелец должен понимать, что именно изменится, видеть rationale/evidence и завершить review без Git/CLI. Бизнес-владельцы **не имеют GitLab user records**, поэтому GitLab MR UI не может быть их authentication или approval surface. Инженерный GitLab MR UI сохраняется, но final apply любого контура идёт через GO.

Текстовый diff сам по себе недостаточен: скрытое изменение front matter, дерева, ссылок или attachment revision способно изменить права, структуру и смысл. Новый commit/rebase меняет `proposal_sha`, поэтому переносить approval на новую версию нельзя. Preview, который не может достоверно показать изменение, должен блокировать merge, а не создавать видимость контроля.

## Decision

1. Минимальный business review screen находится **в платформе поверх GitLab API/GO**: «было / стало / rationale / evidence / принять / отклонить / править». GitLab MR UI — только инженерный контур; второго независимого business review surface не создаётся.
2. Review показывает exact `base_sha` и `proposal_sha` в технических деталях, текст и поддерживаемое форматирование, front matter, дерево/структуру, links, affected files и attachment revisions, provenance/evidence, actor/run и scope изменения.
3. Любое значимое изменение обязано быть видимо. При недостоверном diff/preview, XSS-risk rendering или скрытом metadata/media изменении **merge из платформы блокируется**. Evidence показывается только после авторизации его visibility.
4. Accept привязан к exact `proposal_sha` и одному eligible approver по ADR-12. Approver не совпадает с author, version author или requester. Edit создаёт новый commit/ProposalVersion и новый SHA, сбрасывает approval; rebase равнозначен новой версии. При apply повторная LLM-генерация запрещена.
5. Accept/reject/edit идемпотентны по exact proposal SHA и idempotency contract. Reject/cancel фиксируются DecisionRecord и закрытием MR; edit не затирает предыдущую ProposalVersion. Restore — отдельный revert-MR/new commit.
6. Конфликт/base mismatch объясняется человеческим языком: страница изменилась, требуется новая proposal от свежего HEAD. UI не предлагает automatic conflict merge и не скрывает ноль/неизвестность результата при timeout.
7. Review queue назначается внешней группе, а не персональному GitLab user. Mover меняет доступ и очередь после обновления групп; перед merge GO повторно проверяет группу, path scope и policy revisions.
8. UI явно различает `draft`, `in_review`, `published`, `indexed`, `archived`, `conflicted`; техническое `recovery_required`/quarantine не отображается как успешный merge. Только подтверждённый Git merge commit подтверждает публикацию.
9. WYSIWYG component выбирается в T00 по front matter fidelity, diff/preview, Cyrillic, attachments, accessibility и license. Самописный редактор без отдельного ADR не создаётся; выбор компонента не меняет canonical model.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Бизнес-review непосредственно в GitLab | Меньше UI, но требует GitLab users и не соответствует принятой business boundary | Отклонено владельцем |
| Только текстовый diff | Простая реализация, но скрывает metadata/links/attachments | Недостаточно; merge блокируется при неполном preview |
| Automatic rebase/conflict merge при accept | Меньше ручной работы, но merged content отличается от reviewed SHA | Запрещено |
| Самописный полноценный редактор | Максимальный контроль, но большой scope и риск fidelity/security | Не выбирать без отдельного ADR |
| Два независимых business approval surfaces | Гибкость, но разные policy/audit semantics | Отклонено; один platform flow через GO |

## Consequences

### Positive

- Владелец-неинженер выполняет полный lifecycle без GitLab account и CLI.
- Reviewed content и merged content связаны exact SHA и DecisionRecord.
- Скрытые metadata/attachment изменения становятся явными или блокируют merge.
- Единый UX показывает Git и index состояния без смешения их semantics.

### Negative

- Требуется собственный review UI и качественная визуализация разных типов изменений.
- Конфликт требует новой proposal и повторного review.
- Некоторые медиа/структуры могут быть непригодны к merge до появления достоверного preview.

### Cost

- Нужны diff/preview adapters, accessibility/security tests и editor selection audit.
- Поддержка attachment/structure visualization и human-readable recovery увеличивает frontend/backend интеграцию; объём оценивается после T00.

## Verification / T00 evidence

- **T00:** сравнить готовые editor components на synthetic fixtures: front matter round-trip, Cyrillic, links/anchors, attachments, diff/preview, XSS handling, keyboard/accessibility и license. Не указывать выбранный компонент до evidence.
- A06/A07/A08: новый commit/rebase отклоняет старый approval; accept/reject retry идемпотентен; concurrent merge показывает conflict и не меняет `main`.
- Владелец без GitLab user/CLI проходит pending queue → diff/rationale/evidence → accept/reject/edit → history/restore. Проверить reload survival и group-assigned queue после mover.
- Детерминированно показать изменения front matter/structure/links/attachment revisions; невозможность достоверного preview блокирует merge. Проверить XSS rejected, no lost text, evidence ACL и open MR exclusion.
- Crash/timeout UX: отсутствует ложный `merged` до Git reconciliation; quarantined outcome не предлагается как успех.
- **Текущее состояние:** UX acceptance и editor audit не выполнялись; принятие ADR не закрывает G0/G1.

## Related contracts

- ProposalRecord/ProposalVersion, exact SHA diff/preview, evidence/attachment revision metadata.
- Human accept/reject/comment/edit/merge endpoints, idempotency и version mismatch errors.
- `approval-policy.yaml`, AuthzContext, DecisionRecord и merge trailers.
- UI states `draft`/`in_review`/`published`/`indexed`/`archived`/`conflicted`, recovery/quarantine representation.
- [ADR-04](ADR-004-execution-capability-boundary.md), [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-10](ADR-010-ldap-oidc-identity.md), [ADR-12](ADR-012-business-approval-without-gitlab-users.md), [ADR-13](ADR-013-merge-serialization-recovery.md), [ADR-14](ADR-014-canonical-decision-record.md).
