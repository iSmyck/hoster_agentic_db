---
title: 'kb-ingestion — отдельный модуль ingestion/source-sync'
type: 'feature'
created: '2026-11-14'
status: 'ready-for-dev'
route: 'dispatch'
review_loop_iteration: 0
context:
  - specs/corporate-kb/tasks.md
  - specs/corporate-kb/content-standard.md
  - specs/corporate-kb/components/ingestion-connectors.md
  - specs/corporate-kb/contracts/front-matter.schema.json
  - specs/corporate-kb/contracts/source-origin.schema.json
  - _bmad-output/implementation-artifacts/sprint-status.yaml
---

<!-- Target: 900–1300 tokens. Above 1600 = high risk of context rot. -->

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Phase C превращается в отдельный модуль `kb-ingestion`: нужен intake-пайплайн для файлов от разных клиентов/источников, конвертация в Markdown, первичная структуризация KB агентом и continuous source-sync с configurable validation.

**Approach:** Реализовать `kb-ingestion` как standalone модуль с тремя режимами (`convert`, `structure`, `source-sync`). n8n забирает source-specific fetching; модуль предоставляет uniform endpoint. Source-sync поддерживает auto-merge через настройку; diagram→Mermaid — evidence-gated route с optional Kroki validation.

## Decisions (owner-approved in this session)

- **D1:** Auto-merge для source-sync разрешён через per-source config `auto_merge=true`. ADR-018 accepted 2026-11-14.
- **D2:** Режим называется `source-sync`, не `docops`.
- **D3:** Diagram→Mermaid включён как evidence-gated route; Kroki — optional validation gate.
- **D4:** Object-store adapter извлекается в shared module `src/shared/object_store/` для reuse ingestion + backup.
- **D5:** Parsing: простые Python-экстракторы (DOCX/PDF/HTML) по умолчанию; Docling — evidence-gated route.
- **D6:** Job queue: PostgreSQL table + poll worker.
- **D7:** Media classification: rule-based heuristics по умолчанию; LLM/vision — future gate.

## Boundaries & Constraints

**Always:**
- `convert` никогда не пишет в canonical Git.
- `structure` требует human approval перед submit proposals в GO.
- `source-sync` с `auto_merge=true` работает только для trusted sources с настроенной политикой.
- Все managed writes после cutover идут через GO; auto-merge выполняется только GO по преднастроенной policy.
- Content-standard enforcement перед canonical write.
- Object-store staging: SHA-256, version, object ACL.

**Never:**
- Не реализуем source-specific connectors внутри `kb-ingestion` (SharePoint/FTP clients живут в n8n).
- Не активируем diagram→Mermaid без evidence gate и human spot-check.
- Не делаем auto-merge для `curated` документов.
- Не вводим document-level ACL без ADR.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Convert PDF | PDF + `space_id` | Markdown + staged attachments + front-matter draft | `UNSUPPORTED_FORMAT`, `PII_BLOCKED` |
| Critical media | PDF с critical image | Conversion blocked, `verification_status=pending` | `CRITICAL_MEDIA_PENDING` |
| Structure trigger | Batch converted Markdown | StructureProposal + tree/links preview | `STRUCTURE_INVALID` |
| Source-sync delta | Новый commit в monitored source | ProposalRecord; auto-merge если configured | `CONFLICT_WITH_CURATED`, `AUTO_MERGE_DISABLED` |
| Diagram detected | Image с diagram | Mermaid route (если enabled) или image + alt text | `MERMAID_INVALID` → fallback image |
| Post-cutover direct push | Bulk load after activation | Refused | `DIRECT_PUSH_FORBIDDEN` |

</frozen-after-approval>

## Code Map

- `src/kb-ingestion/app/main.py` — FastAPI factory, module entry point.
- `src/kb-ingestion/app/core/config.py` — MinIO, parser routes, queue, auto-merge policy, Kroki URL.
- `src/kb-ingestion/app/api/router.py` — endpoints: `POST /convert`, `POST /structure`, `POST /sources`, `POST /sources/{id}/sync`.
- `src/kb-ingestion/app/services/converter.py` — format → Markdown orchestration.
- `src/kb-ingestion/app/services/media_processor.py` — extract images, classify, integrate в Markdown.
- `src/kb-ingestion/app/services/agent_structurer.py` — batch Markdown → KB tree proposal.
- `src/kb-ingestion/app/services/source_sync.py` — delta engine, auto-merge policy, cursor management.
- `src/kb-ingestion/app/services/notifier.py` — editor notifications on merge.
- `src/kb-ingestion/app/adapters/object_store.py` — staging adapter (shared).
- `src/kb-ingestion/app/adapters/go_client.py` — proposal/merge API.
- `src/kb-ingestion/app/adapters/identity_client.py` — AuthzContext/stable_id.
- `src/kb-ingestion/app/adapters/kroki_client.py` — Mermaid validation (optional).
- `src/kb-ingestion/app/parsers/` — DOCX/PDF/HTML/Markdown extractors.
- `src/kb-ingestion/app/parsers/extraction_router.py` — evidence-gated route activation.
- `src/kb-ingestion/app/validators/front_matter.py` — front-matter-v2 validation.
- `src/kb-ingestion/app/validators/data_barrier.py` — strict/pii_permitted gate.
- `src/kb-ingestion/app/jobs/` — PostgreSQL queue, worker, retry/DLQ.
- `src/kb-ingestion/app/models/ingestion.py` — models для conversion, source, sync run, queue.
- `src/kb-ingestion/migrations/` — alembic для kb_ingestion schema.
- `src/shared/object_store/` — extracted from backup: adapter + service + models.
- `src/backup/app/adapters/object_store.py` — refactor to use shared module.
- `src/identity/app/api/router.py` — AuthzContext/check endpoints.
- `src/git-orchestrator/app/api/router.py` — proposal/decision/merge endpoints.
- `specs/corporate-kb/contracts/front-matter.schema.json` — canonical schema.
- `specs/corporate-kb/contracts/source-origin.schema.json` — origin record.

## Tasks & Acceptance

**Execution:**
- [ ] `src/shared/object_store/` -- extract adapter/service/models from backup -- shared staging semantics.
- [ ] `src/backup/app/adapters/object_store.py` + `services/object_store.py` -- refactor to use shared module -- no behavior change.
- [ ] `src/kb-ingestion/app/main.py` + `core/config.py` + `api/router.py` -- module scaffold with convert/structure/sources endpoints -- foundation.
- [ ] `src/kb-ingestion/app/services/converter.py` -- single-doc conversion orchestration -- `convert` mode.
- [ ] `src/kb-ingestion/app/services/media_processor.py` -- extract, classify, integrate images -- C.1.2 + image integration.
- [ ] `src/kb-ingestion/app/parsers/` -- DOCX/PDF/HTML extractors with loss report -- C.3.
- [ ] `src/kb-ingestion/app/parsers/extraction_router.py` -- evidence-gated routes (Docling, Mermaid) -- C.3 + D3.
- [ ] `src/kb-ingestion/app/adapters/kroki_client.py` -- optional Mermaid syntax validation -- D3.
- [ ] `src/kb-ingestion/app/services/agent_structurer.py` -- batch → KB tree proposal -- `structure` mode.
- [ ] `src/kb-ingestion/app/services/source_sync.py` -- delta engine + auto-merge policy -- `source-sync` mode.
- [ ] `src/kb-ingestion/app/services/notifier.py` -- editor notifications on merge -- D1.
- [ ] `src/kb-ingestion/app/validators/front_matter.py` + `data_barrier.py` -- content-standard enforcement -- C.4.
- [ ] `src/kb-ingestion/app/jobs/` -- PostgreSQL queue + worker + DLQ -- C.4.
- [ ] `src/kb-ingestion/migrations/versions/2026_11_14_0001_initial_kb_ingestion.py` -- schema migration.
- [ ] `src/kb-ingestion/tests/` -- unit/live tests for all modes.
- [x] `specs/corporate-kb/adr/ADR-018-source-sync-auto-merge-policy.md` -- ADR for auto-merge; accepted 2026-11-14.
- [ ] `specs/corporate-kb/evidence/kb-ingestion/` + `_bmad-output/test-artifacts/kb-ingestion/` -- evidence.

**Acceptance Criteria:**
- Given PDF upload, when convert completes, then Markdown is staged with `attachment://` image refs and `sha256` metadata.
- Given critical media, when convert runs, then status=`blocked` and no canonical write occurs.
- Given batch converted Markdown, when structure is triggered, then agent returns tree + links + front-matter-v2 drafts for human review.
- Given source-sync with `auto_merge=true`, when delta arrives, then GO merges without human DecisionRecord and editor is notified.
- Given source-sync with `auto_merge=false`, when delta arrives, then MR is created and waits for human decision.
- Given diagram image and Mermaid route enabled, when conversion runs, then Mermaid is generated and Kroki validation is attempted; invalid Mermaid falls back to image.
- Given `pii_permitted` file without legal basis, when data barrier runs, then rejected before external egress.
- Given post-cutover Space, when direct bulk push attempted, then refused with `DIRECT_PUSH_FORBIDDEN`.

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Design Notes

**Module boundary.** `kb-ingestion` не хранит source credentials; n8n или connector config владеет ими. Модуль общается с core только через API: GO (proposals/merge), Identity (authz), shared object store (staging).

**Auto-merge policy.** Per-source `auto_merge` требует `trusted=true` в source config и bounded diff (max files/lines). Все auto-merges логируются с `actor_type=source_sync`. Rollback через revert-MR. Owner approval зафиксирован в ADR-018.

**Diagram→Mermaid route.** Activation conditions: (1) vision LLM provider configured, (2) golden fixtures pass, (3) human spot-check confirms semantic match, (4) Kroki validation available. Если любое условие не выполнено — route disabled, image preserved.

**Notification.** MVP: webhook или email через n8n. In-app notifications в Open WebUI — future integration.

## Verification

**Commands:**
- `uv run pytest src/kb-ingestion/tests -q` -- expected: all tests pass.
- `uv run ruff check src/kb-ingestion src/shared --select=F` -- expected: clean.
- `uv run ruff format --check src/kb-ingestion src/shared` -- expected: clean.
- `python scripts/local_stack.py up && python scripts/smoke_local_stack.py` -- expected: ingestion service health pass.

**Manual checks:**
- Verify converted Markdown contains `![alt](attachment://...)` refs.
- Verify source-sync auto-merge produces merge commit with correct trailers and notification is sent.
- Verify front-matter-v2 validation rejects `access` key and `additionalProperties` violations.
