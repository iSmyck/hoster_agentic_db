# Architecture Decision Records — Corporate Agentic Knowledge Platform

## Назначение и порядок применения

Каталог фиксирует архитектурные решения для G0 design review. Нормативные требования R01–R18 и инварианты I01–I14 из [spec.md](../spec.md) имеют приоритет над деталями планирования. Новые проектные решения и их rationale взяты из [ARCHITECTURE-SPINE.md](../architecture-spine.md), который является authority для данного комплекта, и сопутствующего [.memlog.md](../../../_bmad-output/planning-artifacts/architecture/architecture-corp_ai_db-2026-11-06/.memlog.md). [content-standard.md](../content-standard.md) определяет контентный конвейер в границах этих решений.

Поле `access` во front matter не является самостоятельным источником авторизации; CODEOWNERS относится только к инженерному ownership/review; после cutover auto-merge запрещён для всех managed changes, **кроме** trusted source-sync с per-source `auto_merge=true` по [ADR-18](ADR-018-source-sync-auto-merge-policy.md). Эти правила не смешиваются с более ранними информационными формулировками стандарта.

Канонический ID записывается как `ADR-03`…`ADR-17`; ноль в именах файлов `ADR-003`…`ADR-017` является только форматом имени. Ссылки в тексте используют канонический ID.

## Индекс

| ID | Решение | Статус | Дата |
|---|---|---|---|
| ADR-01 | Notes/pages как канон и PostgreSQL operational DB | **Withdrawn by ADR-08**; файл не создаётся | — |
| ADR-02 | Collaboration checkpoint/apply consistency | **Withdrawn by ADR-08**; realtime collaboration вне MVP, файл не создаётся | — |
| [ADR-03](ADR-003-retrieval-adapter.md) | Retrieval adapter | **Proposed** до T00 audit и ACL-aware benchmark | 2026-11-06 |
| [ADR-04](ADR-004-execution-capability-boundary.md) | Execution capability boundary | **Proposed** для G0; реализация зависит от результатов T00 | 2026-11-06 |
| [ADR-05](ADR-005-index-delivery.md) | Index delivery | **Proposed** для G0; engine specifics также Proposed до audit/benchmark | 2026-11-06 |
| [ADR-06](ADR-006-portability-retention.md) | Portability and retention | **Proposed** для G0; параметры retention и recovery требуют решений владельца | 2026-11-06 |
| [ADR-07](ADR-007-client-packaging-license.md) | Client packaging and license | **Proposed** до T00, license/SBOM и GitLab edition review | 2026-11-06 |
| [ADR-08](ADR-008-git-native-canonical-storage.md) | Git-native canonical storage | **Accepted** по spec решением владельца; реализация зависит от результатов T00/G0 | 2026-11-05; дополнено 2026-11-06 |
| [ADR-09](ADR-009-platform-review-ux.md) | Platform review UX | **Accepted** по spec; TipTap adapter selected и owner-approved (G0-D8); canonical adapter/T04 browser gate впереди; realtime CRDT вне MVP | 2026-11-06; уточнено 2026-11-08 |
| [ADR-10](ADR-010-ldap-oidc-identity.md) | LDAP/OIDC identity | **Accepted** по spec; дополнен решениями architecture coaching; upstream capabilities подлежат T00 | 2026-11-06 |
| [ADR-11](ADR-011-two-phase-publication.md) | Two-phase publication | **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00** | 2026-11-06 |
| [ADR-12](ADR-012-business-approval-without-gitlab-users.md) | Business approval without GitLab users | **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00** | 2026-11-06 |
| [ADR-13](ADR-013-merge-serialization-recovery.md) | Merge serialization and recovery | **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00** | 2026-11-06 |
| [ADR-14](ADR-014-canonical-decision-record.md) | Canonical DecisionRecord | **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00** | 2026-11-06 |
| [ADR-15](ADR-015-postgresql-schema-ownership.md) | PostgreSQL schema ownership | **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00** | 2026-11-06 |
| [ADR-16](ADR-016-repository-per-space.md) | One repository per Space | **Accepted during architecture coaching 2026-11-06; реализация зависит от результатов T00** | 2026-11-06 |
| [ADR-17](ADR-017-gitlab-deployment-topology.md) | GitLab deployment topology and tenant profiles | **Accepted by project owner**; GitLab вне application namespace, `shared`/`dedicated` по tenant profile; production gates открыты | 2026-11-09 |
| [ADR-18](ADR-018-source-sync-auto-merge-policy.md) | Source-sync auto-merge policy | **Accepted by project owner**; amends ADR-04/ADR-11 для trusted source-sync auto-merge | 2026-11-14 |

## Границы статусов

- **Accepted не означает production approved.** Любая реализация зависит от результатов T00 baseline audit, G0 design review и последующих gates; production migration, rollout и включение egress требуют отдельных разрешений владельца.
- Pinned baseline выбран и runtime-проверен на synthetic sandboxes: Open WebUI `v0.13.0` (`c38885a1…`), GitLab CE `19.5.3`, PostgreSQL `18.6` + pgvector `0.8.7` — см. [baseline.md](../baseline.md) и [evidence/t00](../evidence/t00/README.md). **T00 DONE, G0 APPROVED** ([g0-review.md](../g0-review.md)); TipTap adapter selected (G0-D8). Это не production approval: final retrieval parameters, license legal clearance и deferred privileged operational controls остаются follow-up.
- Engine specifics — pgvector/FTS, HNSW/IVFFlat, partitioning, exact fallback, embedding/chunking/reranking и связанные параметры — имеют статус **Proposed** до audit и benchmark, даже когда связанный архитектурный инвариант принят.
- Не заданы retention-сроки, RPO/RTO, freshness/latency/quality thresholds или иные SLO. Единственный зафиксированный SLO — отзыв доступа **не более 30 минут** по ADR-10.
- Разделы **Related contracts** перечисляют логические и планируемые контракты. Их наличие в списке не означает, что schema или реализация уже созданы либо проверены.
- Verification-разделы задают необходимые доказательства. На момент создания комплекта интеграционные проверки не выполнялись, mocked integration не засчитывается как PASS.
