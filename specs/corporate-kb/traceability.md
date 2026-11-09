# Corporate KB — traceability и acceptance coverage

## 1. Правила чтения и статус

Канонические источники: [R01–R18](spec.md#4-нормативные-требования), [I01–I14](spec.md#5-инварианты-и-security-boundary), [A01–A36](spec.md#13-acceptance-matrix-и-traceability), [T00–T20](spec.md#11-backlog-с-зависимостями-и-критериями), [E00–E08](spec.md#19-эпики-и-traceability), [AD-1–AD-17](architecture-spine.md) и [ADR-03–ADR-17](adr/README.md).

**Все связи ниже имеют уровень DESIGN. Ни один R/I/A не VERIFIED; A01–A36, integration, migrations и production tests не выполнялись.** Наличие machine contract означает проектное покрытие, а не подтверждение upstream capability или реализации. R/A/T соответствия взяты из spec v1.3; I и component/Epic mappings уточняют design coverage и не создают новых требований.

**T00 DONE, G0 APPROVED 2026-11-08:** [baseline.md](baseline.md), [evidence/t00](evidence/t00/README.md) и [g0-review.md](g0-review.md) (APPROVED). Synthetic capability evidence (GitLab 42 completed probes, Keycloak 9/9, pgvector 22/22) не меняет уровень связей: это evidence для G0, не выполненные acceptance и не universal security PASS. TipTap adapter selected (G0-D8); realtime CRDT вне MVP.

[test-plan.md](test-plan.md) учитывается как `design_not_executed`; его полные сценарии A01–A36 и fault matrix соответствуют текущей нормативной A-матрице spec v1.3. Дублирующий R/I-index из test-plan удалён: этот документ — единый R/I navigation source. Ниже сохранены критерии и прямые R/A/T связи именно spec v1.3.

Сокращения компонентов: [UI] — Open WebUI fork; [GO] — Git Orchestrator; [IAM] — Identity/AuthZ; [RET] — retrieval + CI/index workers; [ING] — ingestion/connectors; [OPS] — deployment/operations. DB — [database.md] и [DBC]; machine contracts перечислены ссылками в каждой строке. [FM] = `document-front-matter-v2`, [AUTHZ] = `authz-context-v2`, [EXPORT] = `export-manifest-v2`, [TOOLS] = `agent-tools-v2`. [MAP] — обязательный versioned canonical↔API↔event↔DB mapping, [T01] — CF-01–CF-30 DESIGN_NOT_EXECUTED consumer vectors, [DOCOPS] — revision-bound `valid_until` projection. [CORR] = correction-task API lifecycle, [CORRSCHEMA] = closed `docops-correction-task-v1` GO-owned `kb_ops` operational record, не canonical content/DecisionRecord. MAP/T01 применяются ко всем связанным строкам и дополнительно развёрнуты в §4.1; это DESIGN coverage, не выполненные tests.

## 2. Матрица R01–R18

| ID | AD / ADR | Components | DB / contracts | Acceptance | Tasks / Epics | Статус |
|---|---|---|---|---|---|---|
| R01 | AD-2,AD-13,AD-15; [ADR-04],[ADR-07],[ADR-08],[ADR-09],[ADR-16] | [UI],[GO],[IAM] | Upstream users/chats + kb_ops/kb_authz read contracts; [API],[TOOLS],[FM],[CORR],[CORRSCHEMA] | A01,A20 | T00,T02,T07,T08,T14,T18 / E00,E02,E04,E07,E08 | DESIGN |
| R02 | AD-1,AD-4,AD-13,AD-15; [ADR-08],[ADR-09],[ADR-10],[ADR-16] | [UI],[GO],[RET],[ING],[IAM] | kb_authz.spaces; kb_index.documents/links/attachments; [FM],[DOCOPS],[API],[DBC],[MAP],[T01] | A01,A21,A32 | T00,T01,T02,T08,T10,T12,T13 / E00,E01,E02,E04,E05,E06 | DESIGN |
| R03 | AD-1,AD-13; [ADR-03],[ADR-04],[ADR-08],[ADR-09] | [UI],[GO],[RET] | GO canonical direct-read contract + kb_index.documents/chunks; [API],[TOOLS],[IDX],[MAP],[T01] | A02,A21 | T00,T02,T08,T09,T10,T14 / E00,E02,E04,E05,E07 | DESIGN |
| R04 | AD-4,AD-9; [ADR-03],[ADR-05],[ADR-15],[ADR-16] | [UI],[RET],[IAM] | kb_index generations/runs/snapshots/documents/chunks/embeddings/publication_fences/pointers; [IDX],[AUTHZ],[API],[TOOLS],[EVENTS],[DBC],[MAP],[T01] | A03,A21,A35 | T00,T01,T09,T10,T14,T19,T20* / E00,E01,E04,E05,E07 + deferred | DESIGN |
| R05 | AD-4,AD-5,AD-6,AD-12,AD-15,AD-17; [ADR-03],[ADR-04],[ADR-06],[ADR-07],[ADR-09],[ADR-10],[ADR-12],[ADR-15],[ADR-16],[ADR-17] | [UI],[IAM],[GO],[RET],[ING],[OPS] | kb_authz all + per-Space context bindings; kb_ops proposals/decisions/correction tasks; [ACCESS],[APPROVAL],[AUTHZ],[PROP],[DEC],[EXPORT],[API],[EVENTS],[MAP],[T01],[CORR],[CORRSCHEMA] | A04,A11,A18,A22,A24,A25,A26,A30,A31,A32,A33,A36 | T00,T01,T02,T03,T05,T06,T07,T09,T10,T13,T14,T16,T18,T20* / E00–E08 + deferred | DESIGN |
| R06 | AD-1,AD-2,AD-3,AD-5,AD-6,AD-7; [ADR-04],[ADR-08],[ADR-11],[ADR-12],[ADR-13],[ADR-17] | [GO],[UI],[ING],[IAM] | kb_ops proposals/versions/decisions; [PROP],[DEC],[AUTHZ],[API],[TOOLS],[GL],[CORR],[CORRSCHEMA] | A05,A17 | T00,T05,T06,T09,T12,T15,T16 / E00,E04,E06,E08 | DESIGN |
| R07 | AD-1,AD-6,AD-13; [ADR-04],[ADR-08],[ADR-09],[ADR-11],[ADR-12],[ADR-14],[ADR-15] | [UI],[GO],[IAM],[ING] | kb_ops proposals/versions; [PROP],[DEC],[ORIGIN],[API],[TOOLS],[GL],[EXPORT],[CORR],[CORRSCHEMA] | A05,A22 | T00,T03,T05,T06,T07,T09,T10,T12,T15,T16,T18 / E00,E02,E04,E05,E06,E08 | DESIGN |
| R08 | AD-1,AD-6,AD-7,AD-13; [ADR-04],[ADR-08],[ADR-09],[ADR-12],[ADR-13],[ADR-14] | [UI],[GO],[IAM] | kb_ops decisions/proposals; [DEC],[PROP],[ACCESS],[APPROVAL],[AUTHZ],[API],[GL],[EXPORT],[MAP],[T01],[CORR],[CORRSCHEMA] | A06,A07,A27,A30,A34,A36 | T00,T03,T05,T06,T07,T13 / E00,E02,E04,E06 | DESIGN |
| R09 | AD-1,AD-3,AD-7,AD-13; [ADR-08],[ADR-09],[ADR-11],[ADR-13],[ADR-14] | [GO],[UI] | kb_ops proposals/versions/decisions/merge/reconciliation; [PROP],[DEC],[API],[GL],[EXPORT],[DBC],[CORR],[CORRSCHEMA] | A08,A10,A27,A28,A34 | T00,T04,T05,T07,T13,T18 / E00,E03,E04,E06,E08 | DESIGN |
| R10 | AD-6,AD-7; [ADR-04],[ADR-08],[ADR-09],[ADR-12],[ADR-13],[ADR-14] | [GO],[IAM],[UI] | kb_ops decisions/merge_operations/target_barriers/target_barrier_decisions/idempotency/reconciliation/correction_tasks; [DEC],[AUTHZ],[ACCESS],[APPROVAL],[API],[GL],[DBC],[MAP],[T01],[CORR],[CORRSCHEMA] | A06,A07,A08,A09,A28,A29,A34,A36 | T00,T03,T04,T05,T06,T07,T13,T18 / E00,E02,E03,E04,E06,E08 | DESIGN |
| R11 | AD-1,AD-4,AD-9,AD-15; [ADR-03],[ADR-05],[ADR-06],[ADR-10],[ADR-11],[ADR-15],[ADR-16] | [RET],[IAM],[GO],[ING] | kb_index all + kb_authz per-Space policies; [IDX],[AUTHZ],[ACCESS],[EVENTS],[API],[EXPORT],[DBC],[MAP],[T01] | A02,A03,A11,A12,A22,A25,A31,A32,A33,A35 | T00,T01,T03,T09,T10,T12,T13,T14,T18,T19,T20* / E00,E01,E02,E04,E05,E06,E07,E08 + deferred | DESIGN |
| R12 | AD-1,AD-3,AD-10,AD-15; [ADR-04],[ADR-05],[ADR-06],[ADR-08],[ADR-11],[ADR-16] | [ING],[GO],[RET],[IAM] | kb_ops.source_sync_states/space_cutovers/index_requests + kb_index; [FM],[ORIGIN],[SRC],[API],[IDX],[EXPORT],[EVENTS],[GL],[DOCOPS],[MAP],[T01] | A13,A23,A31,A35 | T00,T01,T10,T12,T15,T16,T17 / E00,E01,E05,E06,E08 | DESIGN |
| R13 | AD-9,AD-10,AD-13,AD-15; [ADR-03],[ADR-05],[ADR-06],[ADR-08],[ADR-09],[ADR-11],[ADR-16] | [ING],[GO],[RET],[UI] | kb_ops.source_sync_states + kb_index documents/dependencies; [FM],[ORIGIN],[PROP],[API],[EVENTS],[EXPORT] | A14 | T00,T12,T15,T16 / E00,E06,E08 | DESIGN |
| R14 | AD-1,AD-7,AD-11,AD-15,AD-17; [ADR-06],[ADR-08],[ADR-14],[ADR-15],[ADR-16],[ADR-17] | [GO],[IAM],[ING],[RET],[OPS] | Git refs/notes/tags + rebuildable kb_ops/kb_authz/kb_index + durable correction-task backup; [EXPORT],[DEC],[FM],[ORIGIN],[AUTHZ],[API],[GL],[DBC],[MAP],[T01],[CORR],[CORRSCHEMA] | A15,A27,A32,A36 | T00,T03,T05,T13,T18 / E00,E02,E04,E06,E08 | DESIGN |
| R15 | AD-4,AD-5,AD-11,AD-14; [ADR-03],[ADR-04],[ADR-06],[ADR-07],[ADR-10] | [UI],[RET],[ING],[OPS],[IAM] | kb_index.profiles/embeddings + source extraction; [LLM],[AUTHZ],[ORIGIN],[IDX],[TOOLS],[EXPORT] | A16 | T00,T03,T11,T14,T17,T18,T20* / E00,E02,E04,E07,E08 + deferred | DESIGN |
| R16 | AD-4,AD-5,AD-12; [ADR-03],[ADR-04],[ADR-07],[ADR-09],[ADR-10],[ADR-11],[ADR-12],[ADR-13],[ADR-16] | [UI],[GO],[IAM],[ING],[RET] | Separate writers/scopes; [TOOLS],[AUTHZ],[API],[EVENTS],[PROP],[DEC],[GL],[DBC],[MAP],[T01] | A04,A17,A18,A23,A24,A29 | T00,T03,T06,T07,T12,T14,T16 / E00,E02,E04,E06,E07,E08 | DESIGN |
| R17 | AD-2,AD-4,AD-8,AD-11,AD-17; [ADR-06],[ADR-07],[ADR-08],[ADR-10],[ADR-15],[ADR-16],[ADR-17] | [OPS],[UI],[GO],[IAM],[RET],[ING] | Independent instances/resources; [DBC],[EXPORT],[AUTHZ],[LLM],[GL] | A19,A20,A33 | T00,T01,T03,T14,T18,T20* / E00,E01,E02,E07,E08 + deferred | DESIGN |
| R18 | AD-16 и все AD через evidence; [ADR-03]–[ADR-17] по scope | [UI],[GO],[IAM],[RET],[ING],[OPS] | Все machine contracts + synthetic fixtures/fault matrix; [API],[TOOLS],[EVENTS],[DBC],[MAP],[T01],[CORR],[CORRSCHEMA] | A28,A33; regression coverage всего acceptance suite | T00,T01,T05,T06,T11,T14,T17,T18,T19,T20* / E00,E01,E04,E07,E08 + deferred | DESIGN |

`*` T20 не имеет явной строки Requirements в spec v1.3. Его связи с R04,R05,R11,R15,R17,R18 — только design-derived кандидаты для будущего planning, не новые нормативные назначения. Для ADR-03–ADR-17 диапазон в R18 означает применимость по scope, а не одинаковый owner всех решений.

## 3. Матрица I01–I14

| ID | AD / ADR | Components | DB / contracts | Acceptance coverage | Tasks / Epics | Статус |
|---|---|---|---|---|---|---|
| I01 | AD-1,AD-3; [ADR-08],[ADR-11],[ADR-13] | [GO],[ING],[RET] | kb_ops.space_cutovers/proposals; [GL],[API] CutoverRecord,[DEC],[PROP] | A05,A13,A31,A34 | T00,T05,T06,T12,T13 / E00,E04,E06 | DESIGN |
| I02 | AD-2,AD-3,AD-5; [ADR-04],[ADR-07],[ADR-08],[ADR-11],[ADR-16],[ADR-17] | [GO],[UI],[ING],[IAM],[RET] | GitLab rules + GO boundary; [GL],[API],[TOOLS],[DEC],[AUTHZ] | A04,A05,A13,A17,A31 | T00,T03,T05,T06,T12,T15,T16 / E00,E02,E04,E06,E08 | DESIGN |
| I03 | AD-5,AD-6,AD-12; [ADR-03],[ADR-04],[ADR-09],[ADR-10],[ADR-12] | [IAM],[GO],[UI],[ING] | kb_authz identities/groups/contexts + kb_ops principals; [AUTHZ],[PROP],[DEC],[TOOLS],[API] | A05,A18,A24,A26,A30 | T00,T03,T05,T06,T07,T09,T14 / E00,E02,E04,E07 | DESIGN |
| I04 | AD-2,AD-5,AD-6; [ADR-04],[ADR-07],[ADR-11],[ADR-12],[ADR-13],[ADR-17] | [GO],[IAM],[UI],[ING],[RET] | Scoped credentials и single writers; [AUTHZ],[TOOLS],[API],[GL],[DBC] | A04,A17,A18,A34 | T00,T03,T05,T06,T09,T12,T16 / E00,E02,E04,E06,E08 | DESIGN |
| I05 | AD-1,AD-6,AD-7,AD-13; [ADR-04],[ADR-08],[ADR-09],[ADR-12],[ADR-13],[ADR-14] | [GO],[UI] | kb_ops exact SHA + merge evidence; [PROP],[DEC],[API],[GL],[EXPORT] | A06,A08,A27,A34 | T00,T04,T05,T07 / E00,E03,E04 | DESIGN |
| I06 | AD-3,AD-6,AD-7,AD-12; [ADR-04],[ADR-09],[ADR-10],[ADR-11],[ADR-12],[ADR-13] | [GO],[IAM],[UI],[ING] | decisions/idempotency/authz; [AUTHZ],[DEC],[PROP],[API],[GL],[EXPORT] | A06,A08,A29,A30,A31,A34,A36 | T00,T03,T05,T06,T07,T12,T13 / E00,E02,E03,E04,E06 | DESIGN |
| I07 | AD-1,AD-7,AD-8; [ADR-12],[ADR-13],[ADR-14],[ADR-15] | [GO],[IAM] | decisions/merge_operations/target_barriers/reconciliation; [DEC],[PROP],[API],[GL],[EXPORT],[DBC] | A07,A27,A28,A34 | T00,T05,T06,T07,T13,T18 / E00,E04,E06,E08 | DESIGN |
| I08 | AD-3,AD-9; [ADR-03],[ADR-05],[ADR-08],[ADR-11],[ADR-16] | [RET],[GO] | kb_index snapshots/active_pointers + GO cutovers; [IDX],[EVENTS],[API],[DBC] | A03,A22,A31,A35 | T00,T10,T12,T14 / E00,E05,E06,E07 | DESIGN |
| I09 | AD-4,AD-11,AD-12,AD-15; [ADR-03],[ADR-04],[ADR-06],[ADR-07],[ADR-09],[ADR-10],[ADR-16],[ADR-17] | [IAM],[GO],[UI],[RET],[ING] | Space-scoped schemas/policies; [ACCESS],[APPROVAL],[AUTHZ],[FM],[EXPORT],[API],[DBC] | A04,A11,A22,A25,A32,A36 | T00,T01,T02,T03,T07,T09,T10,T12,T13,T14,T16,T18 / E00,E01,E02,E04,E05,E06,E07,E08 | DESIGN |
| I10 | AD-1,AD-7,AD-8,AD-9,AD-11; [ADR-05],[ADR-06],[ADR-08],[ADR-13],[ADR-14],[ADR-15],[ADR-17] | [GO],[IAM],[RET] | Rebuildable projections + single writers; correction-task durable non-Git-derived backup; [DBC],[EXPORT],[EVENTS],[DEC],[IDX],[CORR],[CORRSCHEMA] | A12,A15,A28,A33 | T00,T01,T05,T10,T13,T18 / E00,E01,E04,E05,E06,E08 | DESIGN |
| I11 | AD-7,AD-8,AD-9,AD-16; [ADR-03],[ADR-05],[ADR-06],[ADR-13],[ADR-15] | [RET],[GO] | generations/profiles/runs/closures/pointers/reconciliation; [IDX],[EVENTS],[DBC] | A02,A03,A12,A35 | T00,T01,T10,T12,T13,T14,T19 / E00,E01,E05,E06,E07 + deferred | DESIGN |
| I12 | AD-4,AD-5,AD-6,AD-12; [ADR-03],[ADR-04],[ADR-10],[ADR-12] | [IAM],[GO],[UI],[RET],[ING] | AuthzContext/policy revisions во всех channels; [AUTHZ],[ACCESS],[APPROVAL],[DEC],[TOOLS],[EVENTS],[API] | A04,A17,A18,A36 | T00,T03,T05,T06,T09,T13,T14 / E00,E02,E04,E06,E07 | DESIGN |
| I13 | AD-9,AD-11,AD-15; [ADR-03],[ADR-05],[ADR-06],[ADR-08],[ADR-16] | [ING],[RET],[GO],[IAM] | kb_index.attachments/dependencies + immutable object versions; [FM],[ORIGIN],[IDX],[EXPORT],[EVENTS],[DBC] | A15,A22,A32 | T00,T10,T12,T13,T15,T16,T17,T18 / E00,E05,E06,E08 | DESIGN |
| I14 | AD-3,AD-9,AD-13; [ADR-05],[ADR-08],[ADR-09],[ADR-11] | [UI],[GO],[RET] | proposals/decisions/cutovers/snapshots; [API] DecisionResult/CutoverRecord,[IDX],[EVENTS],[DBC] | A07,A28,A31,A35 | T00,T04,T05,T07,T08,T10,T12,T18 / E00,E03,E04,E05,E06,E08 | DESIGN |

## 4. Acceptance-by-acceptance coverage A01–A36

Все сценарии имеют design owner, machine-contract coverage и существующие T/E. **Статус каждого — DESIGN, не VERIFIED.** Для A20/A24 фактический upstream auth/Notes contract должен быть добавлен в baseline после pin; текущие ссылки фиксируют только собственную design boundary.

| A | Проверяемый результат | R / основные I | Components | Machine contracts | Tasks / Epics | Уровень |
|---|---|---|---|---|---|---|
| A01 | Tree/deep link/WYSIWYG/review без Git/CLI; stable UUID сохраняется после rename внутри repository=Space; front-matter-v2 links/valid_until/archive/origin и DocOps projection проверяются | R01,R02 / I09,I14 | [UI],[GO] | [FM],[DOCOPS],[API],[MAP],[T01] | T02,T08 / E02,E04 | DESIGN |
| A02 | Direct read page/section из exact Git revision с bounds/cursor/truncation; stale candidate не подставляется | R03,R11 / I08,I11,I12 | [UI],[GO],[RET] | [API],[TOOLS],[IDX],[AUTHZ] | T09,T10 / E04,E05 | DESIGN |
| A03 | Exact+semantic per-Space fan-out только по eligible activated published main с citations/fresh independent bindings и полным snapshot/cursor set; preflight/pending/rejected исключены | R04,R11 / I08,I09,I11,I12 | [RET],[IAM],[GO] | [IDX],[EVENTS],[AUTHZ],[API],[DBC],[MAP],[T01] | T10,T14 / E05,E07 | DESIGN |
| A04 | Reader не пишет через UI/API/tools/channels; server/GO/GitLab независимо отклоняют direct push/merge/grants | R05,R16 / I02,I04,I12 | [UI],[GO],[IAM],[ING] | [AUTHZ],[ACCESS],[APPROVAL],[TOOLS],[API],[GL] | T03,T06 / E02,E04 | DESIGN |
| A05 | Create/edit создаёт branch+MR+ProposalRecord с exact base/proposal/principals; main unchanged до verified GO merge; agent ограничен body create/AgentAnchoredPatch, forbidden whole/editProposalVersion diffs отклонены | R06,R07 / I01,I02,I03,I04 | [GO],[UI],[IAM],[ING] | [PROP],[ORIGIN],[AUTHZ],[API],[TOOLS],[GL],[MAP],[T01] | T05,T06 / E04 | DESIGN |
| A06 | Новый commit/rebase создаёт ProposalVersion/SHA; старый approval/DecisionRecord не применяется к новой версии | R08,R10 / I03,I05,I06 | [GO],[UI],[IAM] | [DEC],[PROP],[AUTHZ],[API],[GL] | T05,T07 / E04 | DESIGN |
| A07 | Accept/reject/cancel и reload идемпотентны по decision_id; note+tag сохраняются, replay возвращает Git-derived результат | R08,R10 / I06,I07,I14 | [UI],[GO] | [DEC],[PROP],[API],[GL] | T05,T07 / E04 | DESIGN |
| A08 | Изменение target между proposal и accept даёт STALE_BASE и новую ProposalVersion | R09,R10 / I05,I06 | [GO],[UI] | [PROP],[DEC],[API],[GL] | T04,T05 / E03,E04 | DESIGN |
| A09 | Два concurrent accepts/different proposals сериализуются per target; второй conflict без второго apply | R10 / I05,I06,I07,I14 | [GO],[IAM] | [DEC],[API],[GL],[DBC] | **T05b/E04.2 primary Full/direct; T06/E04.3 Supporting enforcement**; отсутствует в T04a/T05a | DESIGN |
| A10 | Restart/history/revert-MR/attribution сохраняют Git ancestry и principals без history rewrite; merge recovery не подменяет revision/principals | R09 / I05,I14 | [GO],[UI] | [PROP],[DEC],[API],[GL] | **T04a/E03.1 Full/direct — restart/history/revert; T05b/E04.2 Supporting — merge-recovery ancestry/principals** / E03,E04 | DESIGN |
| A11 | Revoke закрывает search/tree/snippets/chunks/files/history/export/tools/subscriptions без ожидания reindex | R05,R11 / I06,I09,I12,I13 | [IAM],[RET],[GO] | [AUTHZ],[EVENTS],[IDX],[EXPORT] | T03,T10,T13 / E02,E05,E06 | DESIGN |
| A12 | Late generation/archive/CI outage/webhook loss обрабатываются ancestry reconciliation; одновременные old/new publishers используют per-Space/profile fence/CAS и stale pointer не откатывается | R11 / I08,I10,I11 | [RET],[GO] | [IDX],[EVENTS],[DBC],[MAP],[T01] | T10 / E05 | DESIGN |
| A13 | Nested dry-run сохраняет links/files/provenance без writes; controlled bulk только unpublished; rerun после cutover через GO/MR | R12 / I01,I02,I08,I14 | [ING],[GO],[RET] | [API] ImportManifest/CutoverRecord,[FM],[ORIGIN],[GL],[IDX] | T12 / E06 | DESIGN |
| A14 | Curated conflict/deletion не затирает знания; source_managed требует human decision, live_operational read-only | R13 / I02,I10,I13 | [ING],[GO],[UI] | [ORIGIN],[PROP],[API],[EVENTS] | T15,T16 / E08 | DESIGN |
| A15 | Export-v2 clone+decisions/assets manifests с explicit outcomes/attempt/recovery и complete/ready closure → clean instance + grants + conservative recovery + full rebuild; отдельный non-Git-derived correction backup/restore и linked-MR reconciliation без второго canonical write path; accepted-before-merge и missing/rejected assets не подменяются merge/hash | R14 / I09,I10,I13 | [GO],[IAM],[ING],[RET],[OPS] | [EXPORT],[DEC],[FM],[ORIGIN],[AUTHZ],[GL],[DBC],[MAP],[T01],[CORR],[CORRSCHEMA] | T13,T18 / E06,E08 | DESIGN |
| A16 | Native inference/extraction/embedding/OCR используют approved inventory/profile/egress без secrets и unplanned fallback | R15 / I03,I12,I13 | [ING],[RET],[UI] | [LLM],[ORIGIN],[IDX],[AUTHZ] | T11,T17 / E07,E08 conditional | DESIGN |
| A17 | All-channel bypass и bot/connector/CI/human direct merge отклонены; auto-merge невозможен | R06,R16 / I02,I03,I04 | [GO],[IAM],[UI],[ING] | [TOOLS],[AUTHZ],[PROP],[API],[GL] | T06 / E04 | DESIGN |
| A18 | Prompt injection не подменяет actor/run/groups/tenant/policy и не расширяет tools/publication capabilities | R05,R16 / I03,I04,I12 | [IAM],[GO],[UI] | [AUTHZ],[PROP],[DEC],[API],[TOOLS] | T03,T06,T14 / E02,E04,E07 | DESIGN |
| A19 | Второй клиент разворачивается config-only с независимыми repositories/PostgreSQL/index/objects/secrets/backups/egress | R17 / I09,I10 | [OPS],[GO],[IAM],[RET],[ING] | [DBC],[EXPORT],[LLM],[GL] | **T18a/E08.4 и T18b/E08.5 Full/direct**; отсутствует в E07.3 | DESIGN |
| A20 | Managed KB opt-in не мигрирует и не изменяет existing personal Notes/ordinary chats и их privacy | R01,R17 / I09,I12 | [UI],[IAM],[OPS] | [API] managed boundary,[AUTHZ],[DBC] upstream ownership; actual seam — T00 | T00,T14,T18 / E00,E07,E08 | DESIGN |
| A21 | Exact codes/Cyrillic/Unicode paths/repeated headings/long pages/stable links проходят schema/read/search/patch без ambiguity | R02,R03,R04 / I08,I09,I12 | [UI],[GO],[RET] | [FM],[API],[TOOLS],[IDX] | T01,T09,T10,T14 / E01,E04,E05,E07 | DESIGN |
| A22 | Open MR/evidence/attachments/unverified media не утекают в published index/чужие answers; review payload авторизуется отдельно | R05,R07,R11 / I08,I09,I12 | [IAM],[RET],[GO] | [AUTHZ],[PROP],[FM],[IDX],[EXPORT],[API] | T03,T07,T10 / E02,E04,E05 | DESIGN |
| A23 | XSS/executable HTML-MDX/traversal/symlink/secrets/oversized/decompression inputs отклоняются до corpus/preview | R12,R16 / I01,I02,I03 | [ING],[GO],[UI] | [API],[FM],[ORIGIN],[LLM] | T07,T12,T17 / E04,E06,E08 conditional | DESIGN |
| A24 | LDAP/OIDC login отклоняет empty/invalid credentials; stable IDs/JIT работают без создания business GitLab user | R05,R16 / I03,I09 | [IAM],[UI] | [AUTHZ],[IAMC],[API]; actual provider seams — T00 | T00,T03 / E00,E02 | DESIGN |
| A25 | Group removal → потеря Space/search/tools/history ≤30 минут; merge/export/private payload denied при ближайшем recheck | R05,R11 / I06,I09,I11,I12 | [IAM],[RET],[GO] | [AUTHZ],[EVENTS],[IDX],[EXPORT],[IAMC] | T03,T10,T13 / E02,E05,E06 | DESIGN |
| A26 | Login/email rename сохраняет stable_id и history; mover меняет Space grants и group review queue | R05 / I03,I09,I12 | [IAM],[GO] | [AUTHZ],[APPROVAL],[PROP],[DEC],[IAMC] | T03 / E02 | DESIGN |
| A27 | Accept/reject/cancel создают совпадающий DecisionRecord note+tag на exact proposal; mismatch → invalid; invalid+unknown сохраняет quarantine/second-MR denial, supersedes не очищает barrier; export-v2 outcome/recovery проверяется | R08,R09,R14 / I05,I07,I10 | [GO],[UI],[OPS] | [DEC],[PROP],[EXPORT],[GL],[DBC],[MAP],[T01] | T05,T07,T13 / E04,E06 | DESIGN |
| A28 | Crash после GitLab merge до projection восстанавливается из commit/note/tag без duplicate; target-wide barrier блокирует новые merges; conclusive failed guarded retry и terminal conflicted/invalid проверяются полным decision/attempt/barrier tuple | R09,R10,R18 / I07,I10,I14 | [GO],[OPS] | [DEC],[API],[GL],[DBC],[MAP],[T01] | **T05b/E04.2 primary Full/direct; T06/E04.3 enforcement; T13a/T13b и T18 supporting** / E04,E06,E08 | DESIGN |
| A29 | Target race между precondition и merge не даёт второй apply при changed HEAD; loser conflict и ноль main writes | R10,R16 / I05,I06,I07 | [GO],[IAM],[UI] | [DEC],[AUTHZ],[API],[GL],[DBC] | T05,T06 / E04 | DESIGN |
| A30 | Approver=author/requester/version editor → self-approval denied; новый editor не утверждает собственную версию | R05,R08 / I03,I04,I06,I12 | [UI],[GO],[IAM] | [ACCESS],[APPROVAL],[AUTHZ],[PROP],[DEC],[API] | T03,T05,T07 / E02,E04 | DESIGN |
| A31 | Cutover HEAD drift останавливает activation; freeze/protection обязательны; preflight non-serving, separate same-SHA published request/run/snapshot и per-Space/profile CAS pointer предшествуют Space activation | R05,R11,R12 / I01,I02,I08,I11,I14 | [ING],[GO],[RET],[IAM] | [API] CutoverRecord,[IDX],[EVENTS],[GL],[AUTHZ],[MAP],[T01] | T03,T10,T12 / E02,E05,E06 | DESIGN |
| A32 | Пользователь одного Space не получает данные другого; clone/mirror/late jobs и policy/cutover/grant/document/pointer/source/error associations не смешивают repositories; composite perimeter negatives обязательны | R02,R05,R11,R14 / I09,I12,I13 | [UI],[IAM],[RET],[GO] | [ACCESS],[AUTHZ],[FM],[IDX],[EXPORT],[DBC],[MAP],[T01] | T02,T03,T10,T13 / E02,E05,E06 | DESIGN |
| A33 | Component не пишет чужие upstream/managed grants/kb_schemas; DB role denial и migration ownership проверены | R05,R11,R17,R18 / I10,I12 | [IAM],[GO],[RET],[OPS] | [DBC],[AUTHZ],[API],[EVENTS] | T01,T03,T18 / E01,E02,E08 | DESIGN |
| A34 | Squash/rebase/FF или parent/trailer/note/tag/hash mismatch не признаются merged; invalid+unknown и second-MR denial сохраняют target recovery/quarantine, terminal/supersedes не очищает barrier | R08,R09,R10 / I02,I04,I05,I07 | [GO],[IAM] | [DEC],[PROP],[GL],[EXPORT],[DBC],[MAP],[T01] | T00,T05,T06 / E00,E04 | DESIGN |
| A35 | Cutover preflight не serving и не активируется; separate published non-preflight имеет тот же SHA/closure/policy/hashes; incremental без independently proven full equivalence не публикуется; concurrent CAS stale write даёт zero rows | R04,R11,R12 / I08,I11,I14 | [RET],[GO],[ING] | [IDX],[API] CutoverRecord,[EVENTS],[ORIGIN],[DBC],[MAP],[T01] | T10,T12 / E05,E06 | DESIGN |
| A36 | Per-Space policy bundle/access+approval revision mismatch, borrowed group snapshot или потеря group/path role/revocation между review и merge/export → отказ без writes/payload; longest-prefix и actor/Space epochs проверяются | R05,R08,R10,R14 / I06,I09,I12,I13 | [GO],[IAM],[ING],[OPS] | [AUTHZ],[ACCESS],[APPROVAL],[DEC],[EXPORT],[API],[MAP],[T01] | T03,T05,T13 / E02,E04,E06 | DESIGN |

## 4.1. T01 CF-01–CF-30 и v2 contract coverage

[T01] — machine-readable каталог `t01-contract-tests-v1`, статус **DESIGN_NOT_EXECUTED**. [MAP] — `canonical-projection-mapping-v1`, статус PROPOSED. Ниже — design navigation от каждого CF к существующим acceptance scenarios, а не новые прямые R/A/T assignments и не выполненные проверки.

| T01 vector | Основное v2/DB/consumer поведение | Acceptance coverage |
|---|---|---|
| CF-01 | `authz-context-v2` per-Space bindings, multi-Space fan-out/cursor/events | A03,A04,A11,A25,A32,A36 |
| CF-02 | Unique approval rules/prefixes и longest-prefix selection | A26,A30,A36 |
| CF-03 | `archived ↔ archive`, restore/replacement/descendants | A01,A12,A21,A32 |
| CF-04 | Origin required/equality и запрет canonical live_operational | A05,A13,A14,A21,A23 |
| CF-05 | Stable `DOC-0001` без lowercase rewrite | A13,A14,A21 |
| CF-06 | Front-matter-v2 `valid_until` + revision-bound DocOps queue/event + [CORR]/[CORRSCHEMA] lifecycle, exact revision, evidence и canonical-write negatives | A01,A03,A07,A21,A22,A26,A27,A36 |
| CF-07 | `agent-tools-v2` restricted create/`AgentAnchoredPatchChange`; human-only edit/whole replacement | A04,A05,A17,A18,A21 |
| CF-08 | Separate connector credential, dry-run/proposal/cursor boundary | A05,A13,A14,A17,A32 |
| CF-09 | Path/body/header equality и canonical tool route | A04,A05,A17,A18,A32 |
| CF-10 | Authorized business history/review queue + correction get/resolve/cancel authorization, CAS, terminal transitions и no-MR semantics [CORR] | A01,A07,A10,A22,A26,A27,A36 |
| CF-11 | Exact preflight/serving/ready hashes/rewrite/closure invariants | A03,A31,A35 |
| CF-12 | Separate same-SHA preflight/published request/run/snapshot IDs | A31,A35 |
| CF-13 | Per-Space/profile publication CAS across generations | A03,A12,A31,A35 |
| CF-14 | Export-v2 assets complete/missing/rejected/hash rules | A15,A32 |
| CF-15 | Accepted/rejected/cancelled explicit outcomes и recovery без premature merge | A07,A15,A27,A28,A34 |
| CF-16 | Единый export format и ready only при complete manifest | A15,A32 |
| CF-17 | Note/tag/record/merge linkage и три разных hashes | A15,A27,A34 |
| CF-18 | DecisionResult merged proof/quarantine/invalid closure semantics | A07,A27,A28,A34 |
| CF-19 | Import/truncation/evidence-range conditionals | A02,A05,A13,A21,A23 |
| CF-20 | Global idempotency key registry и race/replay negatives, включая correction create/resolve/cancel actor/route/path/payload/CAS vectors [CORR] | A05,A07,A17,A28,A29 |
| CF-21 | Failed guarded retry vs unknown/terminal conflicted/invalid | A07,A09,A27,A28,A29,A34 |
| CF-22 | Full-perimeter composite FK и cutover activation guard | A13,A31,A32,A33,A35 |
| CF-23 | Exact decision/merge/base/proposal/target recovery linkage | A27,A28,A29,A34 |
| CF-24 | Approval revision, closure equivalence и profile linkage roundtrip | A03,A31,A33,A35 |
| CF-25 | Все canonical/API/event/DB enum/state/ID/path mappings [MAP], включая отдельный correction-task lifecycle и kb_ops backup/rebuild [CORR] | A01,A02,A03,A07,A12,A13,A14,A25,A27,A31,A35,A36 |
| CF-26 | `live_operational` без document/proposal/index/cursor effects | A14,A32 |
| CF-27 | Resolved stable link сохраняет тот же target UUID/perimeter | A01,A02,A03,A21,A32 |
| CF-28 | Lossless absolute↔relative policy paths и NFC/duplicate rejection | A21,A26,A30,A36 |
| CF-29 | Нормативная crash table integration §7 (spec §7.1/§7.3), не §7.7 | A27,A28,A34 |
| CF-30 | Весь synthetic contract/consumer suite; unavailable real checks BLOCKED | A01–A36 |

Все CF ссылаются на существующие schemas/OpenAPI/events/DBC через [T01]. Реальные GitLab/IdP/PostgreSQL/CI/hoster.ai checks не заменяются этими vectors и остаются предметом соответствующих integration tests.

## 5. Полное T00–T20, E00–E08 и implementation-phase E09–E13 coverage

Acceptance IDs ниже — прямые ссылки из backlog spec v1.3, а не утверждение о выполненных проверках. Детальные dependencies и фактические состояния: [tasks.md](tasks.md).

| Task | Requirements из spec | Прямые Acceptance links | Существующий Epic / DESIGN coverage |
|---|---|---|---|
| T00 | R01–R18 | A20,A24,A34; отдельно requirement-to-test mapping всего acceptance suite | E00 / DESIGN; baseline evidence не входит в эту matrix |
| T01 | R18 | A21,A33 | E01 / DESIGN |
| T02 | R01,R02,R03 | A01,A32 | E02 / DESIGN; canonical exact-revision whole/section direct read с bounds/cursor/truncation |
| T03 | R05,R16 | A04,A11,A18,A22,A24,A25,A26,A30,A31,A32,A33,A36 | E02 / DESIGN |
| T04 | R09,R10 | A08,A10 | E03 / DESIGN |
| T05 | R06–R10 | A05,A06,A07,A08,A09,A10,A27,A28,A29,A30,A34,A36 | E04 / DESIGN |
| T06 | R05,R06,R07,R08,R16 | A04,A05,A09,A17,A18,A28,A29,A34 | E04 / DESIGN |
| T07 | R07,R08 | A06,A07,A22,A23,A27,A30 | E04 / DESIGN |
| T08 | R01,R02,R03 | A01 | E04 / DESIGN |
| T09 | R03,R06,R07 | A02,A21 | E04 / DESIGN |
| T10 | R04,R11 | A02,A03,A11,A12,A21,A22,A25,A31,A32,A35 | E05 / DESIGN |
| T11 | R15,R18 | A16 | E04 G1 profile + E07 / DESIGN; real hoster evidence не заменяется mock |
| T12 | R12,R13 | A13,A23,A31,A35 | E06 / DESIGN |
| T13 | R14 | A11,A15,A25,A27,A32,A36 | E06 / DESIGN; отдельный durable non-Git-derived correction backup/restore и linked-MR reconciliation без второго canonical write path |
| T14 | R18 | A03,A18,A20,A21 | E01 initial + E05 checks + E07 acceptance / DESIGN |
| T15 | R13 | A14 | E06 minimal + E08 full / DESIGN |
| T16 | R12,R13,R16 | A14 | E08 / DESIGN |
| T17 | R12,R18 | A16,A23 | E08 conditional / DESIGN |
| T18 | R14,R17,R18 | A15,A19,A20,A28,A33 | E07 necessary part + E08 operations / DESIGN; full/G3 явно после T16; отдельный correction backup/restore и linked-MR reconciliation |
| T19 | R04,R11,R18 | Отдельные A не назначены; состав определяется после benchmark gate | Отдельный deferred epic после E08; ID не создан / DESIGN |
| T20 | **В spec не указаны** | Отдельные A не назначены | Отдельный deferred epic после E08; ID не создан / DESIGN; R/I mapping требует подтверждения |

### 5.1. Final-story and implementation-phase R/I/A/F/S/CF mapping

**G0 APPROVED 2026-11-08; T00 DONE.** Ниже — окончательная story/split mapping после approved Sprint Change Proposal и story-level mapping для implementation-phase E09–E13. Все rows остаются **DESIGN**, кроме завершённого baseline E00.1/T00; F (Full/direct) и S (Supporting) не означают VERIFIED/DONE. Parent T00–T20 navigation выше сохраняется, но не заменяет эту mapping. E09–E13 deliver implementation code и не заменяют T01–T18b. Полные story formulations — [epics.md](../../_bmad-output/planning-artifacts/epics.md).

| Story / final task | R | I | Full/direct (F) | Supporting (S) | Contract / boundary |
|---|---|---|---|---|---|
| E00.1 / T00 | R18 | I01–I14 audit coverage | — | A20,A24,A34; A01–A36 mapping-only, не product acceptance | Baseline/G0 evidence, не product acceptance |
| E01.1 / T01 | R18 | I08,I09,I10,I11,I12 | A21,A33 только contract-harness scope | Применимые A01–A20,A22–A32,A34–A36 через CF-30 design coverage | [MAP],[T01] |
| E02.1 / T02 | R01,R02,R03 | I08,I09,I11,I12,I13,I14 | A01,A32 | A02,A21,A22 | R05/A04 отсутствуют; [FM],[API],[MAP],[T01] |
| E02.2 / T03a | R05,R16 | I02,I03,I04,I09,I10,I12 | A24,A26 | A04,A18,A33 | Stable identity/nested groups; [AUTHZ],[IAMC] |
| E02.3 / T03b | R01,R05,R16 | I01,I02,I03,I04,I06,I08,I09,I10,I11,I12,I13,I14 | A04,A11,A18,A25,A26,A32,A33,A36 | A22,A30,A31 | Full per-Space policy/enforcement; [ACCESS],[APPROVAL],[AUTHZ] |
| E03.1 / T04a | R02,R09,R10 | I05,I06,I14 | A08,A10 | — | Stale-save/history only; A09 отсутствует |
| E03.2 / T04b | R01,R02,R09 | I01,I02,I03,I05,I06,I09,I14 | — | A01,A08,A23 | TipTap WYSIWYG; realtime CRDT вне MVP |
| E04.1 / T05a | R02,R06,R07,R09,R10 | I01,I02,I03,I04,I05,I06,I08,I09,I12 | A05 | A08,A22,A30 | ProposalVersion only; A09 отсутствует; [PROP] |
| E04.2 / T05b | R06,R07,R08,R09,R10 | I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14 | A06,A07,A08,A09,A27,A28,A29,A30,A34,A36 | A10 — merge-recovery ancestry/principals; Full/direct history/revert остаётся E03.1 | A09/A28 primary exact merge/recovery; [DEC],[GL],[DBC] |
| E04.3 / T06 | R05,R06,R07,R08,R10,R16 | I01,I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14 | A04,A05,A17,A18,A29,A34 | A09,A28,A36 | Adversarial enforcement; privileged Owner incident/quarantine |
| E04.4 / T07 | R01,R05,R06,R07,R08,R09,R10 | I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I12,I13,I14 | A06,A07,A22,A23,A27,A30 | A01,A26,A36 | Exact business review; [PROP],[DEC],[API] |
| E04.5 / T08 | R01,R02,R03,R05,R16 | I06,I08,I09,I11,I12,I13,I14 | A01 | A02,A21,A22,A25,A32 | Scoped canonical direct read |
| E04.6 / T09 | R03,R05,R06,R07,R10,R16 | I01,I02,I03,I04,I06,I08,I09,I11,I12 | A02,A21 | A04,A05,A17,A18,A30 | Restricted single-page agent proposals; [TOOLS] |
| E04.7 / T07b | R01,R05,R06,R07,R08,R09,R10 | I01,I02,I03,I04,I05,I06,I07,I08,I09,I10,I12,I13,I14 | — | A01,A07,A22,A26,A27,A36 | Только [CORR],[CORRSCHEMA],[MAP],[T01]; новые A IDs отсутствуют |
| E05.1 / T10a | R02,R04,R11,R18 | I01,I02,I08,I09,I10,I11,I12,I14 | A12,A22,A35 | A03,A31 | Build/preflight artifact; [IDX],[EVENTS],[MAP],[T01] |
| E05.2 / T10b | R03,R04,R05,R11,R16,R18 | I01,I02,I06,I08,I09,I10,I11,I12,I13,I14 | A02,A03,A11,A21,A22,A25,A32,A35 | A31 | Serving/pointer lifecycle; [IDX],[AUTHZ],[API] |
| E06.1 / T12a | R02,R12,R13,R15,R16,R18 | I01,I02,I03,I08,I09,I12,I13,I14 | A13,A23 | A16,A22 | Dry-run/admission; [FM],[ORIGIN],[API] |
| E06.2 / T12b | R04,R05,R06,R09,R11,R12,R13,R18 | I01,I02,I06,I08,I09,I10,I11,I12,I13,I14 | A13,A31,A35 | A36 | Cutover/activation; [IDX],[GL],[EVENTS] |
| E06.3 / T13a | R02,R05,R09,R10,R14,R18 | I05,I06,I07,I09,I10,I11,I12,I13,I14 | A11,A25,A27,A32,A36 | A15,A28 | Portable export; [EXPORT],[DEC],[MAP],[T01] |
| E06.4 / T13b | R02,R05,R09,R10,R11,R14,R18 | I05,I06,I07,I09,I10,I11,I12,I13,I14 | A15,A32 | A11,A25,A27,A28,A36 | Mirror/backup/clean restore; отдельный durable non-Git-derived correction current/events/evidence/idempotency backup/restore и linked-MR reconciliation без второго canonical write path; [EXPORT],[DBC],[CORR],[CORRSCHEMA] |
| E07.1 / T11 | R15,R16,R18 | I03,I04,I09,I12,I13 | A16 | A18,A20 | Approved inference lifecycle; [LLM] |
| E07.2 / T14 | R01,R03,R04,R05,R11,R15,R18 | I01–I14 в явно выбранном regression scope | A03,A18,A20,A21 | Применимые A01–A36 без автоматического VERIFIED | Actual-pipeline evaluation; [T01] |
| E07.3 / necessary T18 | R01,R05,R14,R15,R17,R18 | I01–I14 по operational-hardening scope | — | A01,A06,A07,A08,A09,A10,A15,A20,A22,A23,A28,A33 | A19/second-client acceptance отсутствует |
| E08.1 / T15 | R06,R07,R08,R09,R10,R12,R13,R16,R18 | I01,I02,I03,I04,I05,I06,I07,I09,I10,I12,I13,I14 | A14 | A17,A32 | Source registry/cursors; [ORIGIN],[PROP],[EVENTS] |
| E08.2 / T16 | R05,R06,R12,R13,R14,R15,R16,R18 | I01,I02,I03,I04,I06,I07,I09,I10,I11,I12,I13,I14 | A14 | A16,A23,A25,A32 | One selected real connector; [SRC],[AUTHZ] |
| E08.3 / T17 conditional | R02,R04,R12,R13,R15,R18 | I01,I02,I03,I08,I09,I12,I13 | A16,A23 только при activated conditional scope | A22 | Evidence-gated extraction/media/OCR |
| E08.4 / T18a | R05,R15,R17,R18 | I04,I07,I09,I10,I11,I12,I13,I14 | A19,A20,A33 | — | Second config-only client/resource isolation/no code fork |
| E08.5 / T18b | R05,R06,R09,R10,R11,R13,R14,R15,R17,R18 | I01,I02,I03,I04,I05,I06,I07,I09,I10,I11,I12,I13,I14 | A15,A19,A20,A33 | A14,A28 | Full operational/G3 явно после T16/E08.2; отдельный non-Git-derived correction backup/restore и linked-MR reconciliation без второго canonical write path; [EXPORT],[DBC],[OPS],[CORR],[CORRSCHEMA] |
| E09.1 / I01 | R01,R18 | I01,I09,I10 | A01 | — | CF-01; implementation-phase project/local infrastructure bootstrap |
| E09.2 / I02 | R05,R16 | I05,I09,I10 | A04,A24,A25,A26 | A30,A32 | CF-02; identity models и `kb_authz` migrations |
| E09.3 / I03 | R05,R16 | I05,I09 | A04,A24 | A25,A26,A30,A32 | CF-02; stable identity resolution и group snapshots |
| E09.4 / I04 | R05,R16 | I05,I09 | A25,A26 | A04,A24,A30,A32,A33 | CF-02; policy activation, AuthzContext и path approval |
| E10.1 / I05 | R02,R05,R06,R09 | I01,I02,I06,I08 | A08 | A05,A06,A09 | CF-03; read-only GO/GitLab bootstrap, write endpoints отсутствуют |
| E10.2 / I06 | R06,R07,R08,R09 | I02,I06,I08,I09 | A05,A06,A07,A08,A09,A27,A28,A29,A30 | — | CF-03,CF-04; ProposalRecord = GitLab MR с `kb_ops` operational projection |
| E11.1 / I07 | R01,R02,R03,R09 | I01,I02,I06 | A01,A08 | A10 | CF-01,CF-03; pinned Open WebUI fork и typed KB API client |
| E12.1 / I08 | R04,R11,R16 | I03,I05,I06 | A03,A12,A21 | A02,A11,A25,A31,A32 | CF-05; index worker, exact/semantic search и per-payload AuthZ |
| E13.1 / I09 | R12,R13,R16 | I06,I08,I09 | A13,A14,A23 | A31,A35 | CF-06; dry-run importer, source registry и durable cursors |

Обязательные reverse assignments:

- **T03a/T03b:** E02.2/E02.3; identity/policy/enforcement разделены, R05/A04 не заявляются в E02.1.
- **T04a/T04b:** E03.1/E03.2; editor conflict — A08, A09 отсутствует и проверяется в E04.2/E04.3. TipTap WYSIWYG не включает realtime CRDT.
- **A10 final ownership:** E03.1/T04a — **Full/direct** для restart/history/revert-MR/attribution; E04.2/T05b — **Supporting** для merge-recovery ancestry/principals без history rewrite. Оба назначения присутствуют в epics Requirements/Evidence и в §5.1.
- **T05a/T05b:** E04.1/E04.2; A05 — ProposalVersion, A09/A28 — exact merge/concurrent accepts/crash recovery.
- **T07/T07b:** E04.4/E04.7; T07b имеет только Supporting existing A IDs и [CORR]/[CORRSCHEMA].
- **T10a/T10b:** E05.1/E05.2; build/preflight отделён от serving/pointer lifecycle.
- **T12a/T12b:** E06.1/E06.2; dry-run/admission отделён от cutover/activation. T12a может начаться после T03/T04 параллельно T05/T10 только как отдельная работа; полный T12/T12b требует T03,T04,T05 и T10 artifacts.
- **T13a/T13b:** E06.3/E06.4; portable export отделён от mirror/backup/clean restore. E06.4 явно включает отдельный durable non-Git-derived correction-task/event/evidence/idempotency backup/restore и linked-MR reconciliation без второго canonical write path.
- **T18 necessary/T18a/T18b:** E07.3/E08.4/E08.5; A19 назначен только E08.4/E08.5. Full T18/G3/E08.5 явно зависит от T16/E08.2 и включает correction backup/restore/linked-MR reconciliation без второго canonical write path.
- Forward acceptance dependencies удалены: E02.1 не требует E02.2/E02.3 для своего scope, E03.1/E04.1 не требуют E04.2 для A09, E07.3 не требует E08.4/E08.5 для internal-pilot evidence.

| Epic | Состав без переименования | Coverage |
|---|---|---|
| E00 | T00 | Baseline/design review; все R/I требуют capability audit, прямые A20,A24,A34 и A01–A36 mapping |
| E01 | T01 + начальный T14 | Contracts, fixtures, sandbox, negative/fault harness; A21,A33 и последующая общая regression |
| E02 | T02,T03 | Documents/UI/ACL; A01,A04,A24–A26,A30,A32,A33 и связанные cross-component A |
| E03 | T04 | Draft/save/history/revert; A08,A10 |
| E04 | T05,T06,T07,T07b,T08,T09 + G1 profile T11 | Governed human/agent workflow, correction tasks и G1; A05–A10,A17,A18,A27–A30,A34 и связанные A |
| E05 | T10 + проверки T14 | Published index/retrieval; A02,A03,A11,A12,A21,A22,A25,A31,A32,A35 |
| E06 | T12,T13 + минимальный T15 | Controlled import/cutover/export/rebuild; A13,A15,A23,A31,A35,A36 и связанные A |
| E07 | T11,T14 + необходимая часть T18 | Internal pilot/quality/security/runbook acceptance; A03,A16,A18,A20,A21 |
| E08 | T15,T16,T18 + условный T17 | Source/connector/repeatable dedicated delivery; A14–A16,A19,A20,A23,A28,A33 |
| E09 | I01,I02,I03,I04 | Identity + AuthZ adapter implementation; story-level A01,A04,A24,A25,A26,A30,A32,A33; CF-01,CF-02 |
| E10 | I05,I06 | Git Orchestrator read-only bootstrap и governed proposal/decision lifecycle; story-level A05,A06,A07,A08,A09,A27,A28,A29,A30; CF-03,CF-04 |
| E11 | I07 | Open WebUI fork KB seams; A01,A08 Full/direct, A10 Supporting; CF-01,CF-03 |
| E12 | I08 | Retrieval + indexing implementation; A03,A12,A21 Full/direct, A02,A11,A25,A31,A32 Supporting; CF-05 |
| E13 | I09 | Dry-run importer и source registry; A13,A14,A23 Full/direct, A31,A35 Supporting; CF-06 |

## 6. Coverage audit и открытые пробелы

- **R:** R01–R18 присутствуют в матрице; ни один не отмечен VERIFIED. R04 не включает A02, R05 включает A31, R11 включает A22, R18 не включает A34 — точно как spec acceptance matrix.
- **I:** I01–I14 присутствуют; cutover, no-bypass, exact SHA, recovery, repository=Space, rebuild, index ordering, ACL и statuses имеют design owners/contracts. Test-plan больше не содержит независимый I-index.
- **A:** A01–A36 перечислены по одному разу в acceptance-by-acceptance matrix; пропусков нет. Все DESIGN.
- **T:** T00–T20 учтены без дублирования live states; фактический tracker — [tasks.md](tasks.md). T20 не имеет явных Requirements/Acceptance в spec и не должен получать их молча.
- **E:** E00–E08 сохранены; implementation-phase E09–E13 и их stories I01–I09 имеют R/I/A/F/S/CF mapping в §5.1. T19/T20 намеренно относятся к отдельным будущим эпикам; новые deferred IDs не созданы.
- **AD/ADR:** AD-1–AD-17 и существующие [ADR-03–ADR-17](adr/README.md) связаны с требованиями; ADR-17 owner-approved 2026-11-09 отдельно от исторического G0; withdrawn ADR-01/02 не используются. Наличие ADR не означает G0 approval.
- **Contracts:** все JSON schemas, OpenAPI, agent tools, events, DB catalog, integration protocol docs, [MAP], [T01], [DOCOPS], [CORR] и [CORRSCHEMA] связаны хотя бы с одной строкой. V2 names, correction-task v1 и explicit state mappings зафиксированы как DESIGN output, не successful tests.
- **Final-story coverage:** §5.1 содержит все split IDs T03a/b,T04a/b,T05a/b,T07b,T10a/b,T12a/b,T13a/b,T18a/b с R/I/A/F/S. A04 отсутствует в E02.1, A09 — в E03.1/E04.1, A19 — в E07.3; A28 primary — E04.2; A10 — Full/direct E03.1 и Supporting E04.2. E02 не заявляет published retrieval R04, а T02/R03 покрывает canonical direct read. Полный T12/T12b требует T05, full T18/G3 — T16; E06.4/E08.5 связаны с [CORR]/[CORRSCHEMA] для отдельного non-Git-derived restore без второго canonical write path.
- **Available baseline/approval inputs:** [baseline.md](baseline.md), pinned code references и owner [g0-review.md](g0-review.md) APPROVED 2026-11-08 имеются; **T00 DONE, G0 APPROVED**.
- **Отсутствующие verification inputs:** product contract/conformance execution, real application integration outputs, T04 browser, T11 hoster inputs, T13/T16 object-store ACL, operational rehearsals и production/legal gates остаются BLOCKED/DESIGN по соответствующим tasks; отсутствие этих inputs не falsify как PASS.
- **Test-plan:** полные A01–A36 и fault matrix сохранены; R04−A02, R05+A31, R11+A22, R18−A34 больше не имеют расходящегося duplicate index. [operations.md](operations.md) существует как `design_not_executed`; rehearsals не выполнялись.

[UI]: components/open-webui-fork.md
[GO]: components/git-orchestrator.md
[IAM]: components/identity-access.md
[RET]: components/retrieval-indexing.md
[ING]: components/ingestion-connectors.md
[OPS]: operations.md
[database.md]: database.md
[ADR-03]: adr/ADR-003-retrieval-adapter.md
[ADR-04]: adr/ADR-004-execution-capability-boundary.md
[ADR-05]: adr/ADR-005-index-delivery.md
[ADR-06]: adr/ADR-006-portability-retention.md
[ADR-07]: adr/ADR-007-client-packaging-license.md
[ADR-08]: adr/ADR-008-git-native-canonical-storage.md
[ADR-09]: adr/ADR-009-platform-review-ux.md
[ADR-10]: adr/ADR-010-ldap-oidc-identity.md
[ADR-11]: adr/ADR-011-two-phase-publication.md
[ADR-12]: adr/ADR-012-business-approval-without-gitlab-users.md
[ADR-13]: adr/ADR-013-merge-serialization-recovery.md
[ADR-14]: adr/ADR-014-canonical-decision-record.md
[ADR-15]: adr/ADR-015-postgresql-schema-ownership.md
[ADR-16]: adr/ADR-016-repository-per-space.md
[ADR-17]: adr/ADR-017-gitlab-deployment-topology.md
[API]: contracts/openapi.yaml
[TOOLS]: contracts/agent-tools.yaml
[EVENTS]: contracts/events.yaml
[DBC]: contracts/database-catalog.yaml
[FM]: contracts/front-matter.schema.json
[ACCESS]: contracts/access-policy.schema.json
[APPROVAL]: contracts/approval-policy.schema.json
[AUTHZ]: contracts/authz-context.schema.json
[PROP]: contracts/proposal-record.schema.json
[DEC]: contracts/decision-record.schema.json
[IDX]: contracts/index-snapshot.schema.json
[EXPORT]: contracts/export-manifest.schema.json
[ORIGIN]: contracts/source-origin.schema.json
[GL]: contracts/gitlab-integration.md
[IAMC]: contracts/identity-integration.md
[LLM]: contracts/inference-integration.md
[SRC]: contracts/source-storage-integration.md
[MAP]: contracts/projection-mapping.md
[T01]: contracts/t01-contract-tests.yaml
[DOCOPS]: contracts/docops-review-metadata.schema.json
[CORR]: contracts/docops-correction-api.md
[CORRSCHEMA]: contracts/docops-correction-task.schema.json
