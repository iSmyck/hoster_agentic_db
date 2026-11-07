# ADR-06 — Portability and retention

**ID/Title:** ADR-06 / Переносимость, backup/restore и retention  
**Status:** **Proposed** для G0; реализация зависит от результатов T00, а сроки retention, RPO/RTO и privileged deletion требуют отдельных решений владельца. Не является production approval.  
**Date:** 2026-11-06  
**Requirements/AD links:** R05, R11–R15, R17, R18; I09–I11, I13; [ARCHITECTURE-SPINE.md](../architecture-spine.md): AD-1, AD-4, AD-7, AD-11, AD-15, AD-16; [spec.md](../spec.md): T13, T18.

## Context

Обещание «знания остаются в Git» неполно без MR/decision metadata, protected annotated tags, внешних immutable assets, policy и проверяемого restore. Обычный clone рабочей ветки может не включать все явные refs; database dump не является источником канона. Права на чтение страницы не обязательно означают право экспортировать всю историю Space.

Git history, MR notes/tags, mirrors и object versions сохраняют копии после видимого удаления. Поэтому retention нельзя трактовать как удаление текущего файла, а hard purge нельзя выполнять незаметным history rewrite. Численные сроки и recovery objectives ещё не утверждены.

## Decision

1. Экспорт Space — **`git clone` согласованного repository snapshot + manifest** с явными refs, IDs/tree/links/origin и фиксацией snapshot SHA. Правило один repository = один Space связывает ACL, history, clone/export и backup единым периметром.
2. Обязательный **decisions manifest** включает полные DecisionRecords, их `record_sha256`, необходимые MR metadata и связи с note/tag/merge trailers по ADR-14. Manifest облегчает проверку, но не заменяет canonical Git note/protected annotated tag.
3. **Assets manifest** перечисляет immutable external objects, versions, hashes, media types, sizes и source references. Чтение текущего mutable URL без hash не считается воспроизводимым export/restore.
4. По умолчанию export не включает secrets, private chats или неутверждённые payloads. Full-repository clone разрешён только при export permission на Space **и всю его историю**. Filtered export, удаление history и hard purge требуют отдельного privileged workflow и ADR; они не подменяются обычным clone.
5. Backup включает Git mirror со всеми необходимыми refs, GitLab metadata, external object storage, versioned configuration и secrets policy. Секреты остаются в deployment secret mechanism и не копируются в manifest/log/report.
6. Restore drill проверяет snapshot closure: documents/revisions, links/attachments, decisions и merge parentage/trailers, policies/grants mapping, refs и external assets. `kb_ops` и `kb_index` пересобираются из canonical Git/GitLab/source metadata; grants восстанавливаются через Identity/AuthZ adapter из Git policy + IdP.
7. Каждый клиент имеет независимые repositories, configuration, PostgreSQL/index, object storage, secrets и backups. Cross-client backup/export/cache запрещены.
8. Retention владельца отдельно определяется для веток/MR/audit/chats/files/object versions/mirrors/backups. В MVP admin break-glass и privacy hard purge отключены. Их включение требует отдельного ADR, privileged approval, history-rewrite/new index generation и mirror-retention protocol.
9. RPO/RTO, сроки хранения и idempotency replay retention остаются UNKNOWN/DEFERRED до решения владельца; никакие значения данным ADR не задаются.

## Alternatives and tradeoffs

| Альтернатива | Компромисс | Результат |
|---|---|---|
| Только database dump | Сохраняет projection, но теряет Git-native lifecycle и decision anchors | Отклонено как canonical backup |
| Только clone default branch | Просто, но может исключить decision refs, MR metadata и assets | Недостаточно |
| Полный export любому reader | Удобно, но раскрывает всю историю Space | Запрещено без отдельного export permission |
| Молчаливое history rewrite для deletion | Быстро визуально, но ломает ancestry/decisions и оставляет mirrors | Только отдельный privileged ADR; в MVP отключено |
| Единый backup нескольких клиентов | Дешевле администрирование, но смешивает data/secrets и blast radius | Отклонено |

## Consequences

### Positive

- Снижается lock-in: канон, решения и assets можно проверить и перенести.
- Restore становится проверяемой операцией, а не наличием backup files.
- Явные refs/manifests сохраняют business audit после потери БД.
- Space perimeter предотвращает accidental cross-Space history export.

### Negative

- Полная история увеличивает объём и чувствительность export.
- Внешние assets и GitLab metadata усложняют snapshot closure.
- Retention конфликтует с append-only/history semantics и требует явных исключений.

### Cost

- Нужны manifest tooling, metadata/assets backup, restore drills и безопасное хранение нескольких копий.
- Privileged purge и filtered export — отдельные дорогостоящие workflows, не включённые в MVP.

## Verification / T00 evidence

- **T00:** на выбранной GitLab version/edition проверить clone/fetch необходимых protected annotated tag refs, MR notes/metadata export и восстановление merge trailers; отсутствие capability — BLOCKED/design review, не предполагаемый PASS.
- A15: clone + manifests → clean dedicated instance → explicit policy/grant mapping → rebuild `kb_ops`/`kb_index`; сравнить IDs, дерево, content hashes, links, revisions, attachments и decision chain.
- Проверить, что reader без export permission не получает full history, secrets/chats отсутствуют, missing/mismatched note/tag делает decision invalid, missing asset/hash блокирует claimed complete restore.
- Mirror backup + restore rehearsal с sanitized evidence о срезе refs, snapshot closure, rebuild и расхождениях. Не объявлять RPO/RTO без отдельного решения и измерения.
- Retention/hard-purge tests не выполнять destructive на production; соответствующий design остаётся BLOCKED до owner approval.
- **Текущее состояние:** clean restore и реальная GitLab metadata export capability не проверены.

## Related contracts

- Clone/export manifest, explicit refs, decisions manifest, assets manifest, provenance/origin mapping.
- DecisionRecord JSON + MR note + `kb-decisions/<decision_id>` + merge trailers.
- Attachment binding `{object_id, version, sha256, size, media_type, source_ref}`.
- Restore/rebuild procedures для `kb_authz`, `kb_ops`, `kb_index`; dedicated client secrets/backup policy.
- [ADR-08](ADR-008-git-native-canonical-storage.md), [ADR-10](ADR-010-ldap-oidc-identity.md), [ADR-14](ADR-014-canonical-decision-record.md), [ADR-15](ADR-015-postgresql-schema-ownership.md), [ADR-16](ADR-016-repository-per-space.md).
