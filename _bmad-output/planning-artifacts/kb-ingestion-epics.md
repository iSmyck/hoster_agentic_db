---
status: final
stepsCompleted:
  - requirements-extraction
  - epic-design
  - story-generation
  - final-validation
inputDocuments:
  - _bmad-output/implementation-artifacts/spec-phase-c-ingestion-source-connectors.md
  - specs/corporate-kb/content-standard.md
  - specs/corporate-kb/components/ingestion-connectors.md
  - specs/corporate-kb/contracts/front-matter.schema.json
  - specs/corporate-kb/contracts/source-origin.schema.json
project: corp_ai_db
module: kb-ingestion
updated: '2026-11-14'
---

# kb-ingestion — Epic / Story Breakdown

## Overview

`kb-ingestion` — отдельный модуль для intake, конвертации, первичной структуризации KB и continuous source-sync. Модуль не содержит source-specific connectors (SharePoint/FTP clients живут в n8n). Взаимодействие с core только через API: GO, Identity, shared object store.

**Decisions (owner-approved):**
- Auto-merge для source-sync разрешён через per-source config `auto_merge=true`.
- Режим называется `source-sync`.
- Diagram→Mermaid — evidence-gated route с optional Kroki validation.
- Object-store adapter выносится в `src/shared/object_store/`.
- Parsing: простые Python-экстракторы; Docling — evidence-gated.
- Job queue: PostgreSQL + poll worker.
- Media classification: rule-based; LLM/vision — future gate.

---

## Epic KBI.1 — Single-document conversion (`convert`)

| Field | Value |
|---|---|
| ID | KBI.1 |
| Title | Single-document conversion |
| Goal | Принять один документ любого формата и сконвертировать в canonical Markdown со staged attachments и front-matter draft. |
| Scope boundaries | Только conversion, никаких canonical writes. Source-specific fetching вынесен в n8n. |

### Stories

#### Story KBI.1.1 — Upload endpoint and object-store staging

*As a platform I accept one file via uniform endpoint so that n8n can feed documents from any source.*

- Given a file upload with `space_id`, `client_id`, `data_profile`
  - When `POST /api/kb/v1/ingest/convert` is called
  - Then the raw file is staged in object store with `object_id`, `sha256`, `version_id`, `size`, `media_type`
- Given a `pii_permitted` file without `legal_basis`
  - When the upload is received
  - Then it is rejected with `LEGAL_BASIS_REQUIRED` before staging
- Given a file exceeding size limit
  - When the upload is received
  - Then it is rejected with `SIZE_LIMIT_EXCEEDED`

#### Story KBI.1.2 — Format detection and parser routing

*As a platform I detect the file format and select an extractor so that conversion is deterministic.*

- Given a staged file with known format (PDF, DOCX, XLSX, HTML, Markdown, PNG, JPG)
  - When conversion starts
  - Then the parser router selects an approved extractor by MIME type and extension
- Given an unsupported or malicious format
  - When conversion starts
  - Then it is rejected with `UNSUPPORTED_FORMAT` or `SECURITY_BLOCKER`
- Given a format with multiple possible extractors
  - When the router selects
  - Then it uses the evidence-gated route priority and falls back to default

#### Story KBI.1.3 — Media extraction and classification

*As a platform I extract embedded media and classify it so that critical content is gated.*

- Given a DOCX/PDF/PPTX with embedded images
  - When media extraction runs
  - Then each image is staged as a separate object with `sha256` and `media_type`
- Given an extracted image
  - When classification runs
  - Then it is labeled `decorative` / `illustrative` / `substantive` / `critical` / `handwritten`
- Given a `critical` or `handwritten` image without verification
  - When conversion completes
  - Then `status=blocked` and `verification_status=pending` is recorded

#### Story KBI.1.4 — Image integration into Markdown

*As a platform I integrate extracted images into Markdown so that the document is self-contained.*

- Given extracted images with `object_id`
  - When Markdown is generated
  - Then images are referenced as `![alt](attachment://{object_id})`
- Given a `decorative` image
  - When Markdown is generated
  - Then it is excluded from output
- Given an image with generated alt text
  - When alt text is produced
  - Then it is marked `automatic=true` in the attachment manifest

#### Story KBI.1.5 — Front-matter draft generation

*As a platform I generate a front-matter-v2 draft so that subsequent structuring has a valid base.*

- Given converted Markdown and attachments
  - When front-matter draft is generated
  - Then it contains `schema_version=document-front-matter-v2`, `id`, `title`, `parent_id=null`, `ownership_mode=migrated`, `links=[]`, `valid_until=null`, `archived=false`, `attachments[]`, `origin`
- Given a `source_managed` input
  - When front-matter draft is generated
  - Then `origin` is required and matches `ownership_mode`

#### Story KBI.1.6 — Dry-run report and blockers

*As a user I review a dry-run report so that I can resolve blockers before KB structuring.*

- Given a completed conversion
  - When dry-run report is requested
  - Then it returns `path→object_id` map, `attachments[]`, `blockers[]`, `losses[]`, `errors[]`
- Given any blocker
  - When the report is generated
  - Then no canonical write has occurred and a correction task may be created

### Technical tasks

| ID | Title | Files / components | Size |
|---|---|---|---|
| KBI-101 | Implement upload endpoint and request validation | `src/kb-ingestion/app/api/router.py`, schemas | M |
| KBI-102 | Wire shared object-store adapter | `src/shared/object_store/`, `src/kb-ingestion/app/adapters/object_store.py` | M |
| KBI-103 | Implement parser router and format detection | `src/kb-ingestion/app/parsers/extraction_router.py` | M |
| KBI-104 | Implement DOCX/PDF/HTML extractors | `src/kb-ingestion/app/parsers/` | L |
| KBI-105 | Implement media extraction and rule-based classifier | `src/kb-ingestion/app/services/media_processor.py` | M |
| KBI-106 | Implement Markdown image integration | `src/kb-ingestion/app/services/converter.py` | M |
| KBI-107 | Implement front-matter-v2 draft generator | `src/kb-ingestion/app/validators/front_matter.py` | M |
| KBI-108 | Implement dry-run report builder | `src/kb-ingestion/app/services/converter.py` | M |
| KBI-109 | Unit tests for conversion pipeline | `src/kb-ingestion/tests/test_convert.py` | L |

---

## Epic KBI.2 — Agent KB structuring (`structure`)

| Field | Value |
|---|---|
| ID | KBI.2 |
| Title | Agent KB structuring |
| Goal | Превратить batch converted Markdown в структурированную KB через agent proposal и human approval. |
| Scope boundaries | Agent только предлагает структуру; human review обязателен перед GO submit. |

### Stories

#### Story KBI.2.1 — Batch read of converted Markdown

*As an agent I read a batch of converted Markdown so that I can analyze the corpus.*

- Given a list of `markdown_object_id`
  - When the agent reads the batch
  - Then it retrieves all documents with content, attachments, and front-matter drafts
- Given a document with `status=blocked`
  - When the agent reads the batch
  - Then it is excluded from structuring and reported

#### Story KBI.2.2 — Tree and link proposal generation

*As an agent I propose a KB tree and stable links so that the knowledge base is navigable.*

- Given a batch of documents
  - When the agent analyzes content
  - Then it proposes `parent_id` for each document and `links[]` between related documents
- Given ambiguous or conflicting structure
  - When the agent generates a proposal
  - Then it marks low-confidence nodes for human attention

#### Story KBI.2.3 — Structure proposal review

*As a specialist I review the proposed KB structure so that I can correct it before publication.*

- Given a `StructureProposal`
  - When the specialist opens it
  - Then they see tree preview, links graph, and per-document front-matter
- Given a correction
  - When the specialist edits `parent_id` or `links`
  - Then the proposal is updated and versioned

#### Story KBI.2.4 — Submit proposals to GO

*As a specialist I submit approved structure proposals so that documents enter the canonical KB.*

- Given an approved `StructureProposal`
  - When submit is triggered
  - Then GO receives one ProposalRecord per document with correct `base_sha`, `author_stable_id`, `requester_stable_id`
- Given a proposal with invalid front-matter
  - When submit is triggered
  - Then it is rejected with `FRONT_MATTER_INVALID`

### Technical tasks

| ID | Title | Files / components | Size |
|---|---|---|---|
| KBI-201 | Implement batch reader for converted Markdown | `src/kb-ingestion/app/services/agent_structurer.py` | M |
| KBI-202 | Implement tree/link proposal agent | `src/kb-ingestion/app/services/agent_structurer.py` | L |
| KBI-203 | Implement StructureProposal API and persistence | `src/kb-ingestion/app/api/router.py`, models | M |
| KBI-204 | Implement GO proposal submission | `src/kb-ingestion/app/adapters/go_client.py` | M |
| KBI-205 | Unit tests for structuring | `src/kb-ingestion/tests/test_structure.py` | M |

---

## Epic KBI.3 — Source-sync (`source-sync`)

| Field | Value |
|---|---|
| ID | KBI.3 |
| Title | Source-sync |
| Goal | Отслеживать источники и обновлять KB по delta документов с configurable validation/auto-merge. |
| Scope boundaries | Source credentials живут в n8n/vault; модуль получает delta через uniform input или connector callback. |

### Stories

#### Story KBI.3.1 — Source registry and configuration

*As an operator I register a source so that the platform monitors it for changes.*

- Given a source config with `source_type`, `source_ref`, `credentials_ref`, `poll_interval`, `space_id`, `data_profile`, `validation_required`, `auto_merge`
  - When `POST /api/kb/v1/ingest/sources` is called
  - Then the source is persisted and validated
- Given `auto_merge=true` without `trusted=true`
  - When the source is registered
  - Then it is rejected with `AUTO_MERGE_REQUIRES_TRUSTED`

#### Story KBI.3.2 — Delta detection and cursor management

*As a platform I detect source deltas so that only changes are processed.*

- Given a registered source with `cursor`
  - When a sync run starts
  - Then new/changed/deleted documents are identified by `source_version` and `sha256`
- Given a document with unchanged hash
  - When the sync run processes it
  - Then it is a no-op
- Given a deleted source document
  - When the sync run processes it
  - Then a deletion proposal is created

#### Story KBI.3.3 — Auto-merge policy engine

*As a platform I apply auto-merge policy so that trusted sources can update KB without human review.*

- Given `auto_merge=true` and `validation_required=false`
  - When a delta proposal is accepted by policy
  - Then GO performs merge without human DecisionRecord and records `actor_type=source_sync`
- Given a diff exceeding bounds (max files/lines)
  - When auto-merge is attempted
  - Then it falls back to MR + human review
- Given a `curated` document targeted by source-sync
  - When auto-merge is attempted
  - Then it is refused with `CURATED_DOCUMENT_PROTECTED`

#### Story KBI.3.4 — Notification on merge

*As an editor I receive a notification when a subscribed document changes so that I can review updates.*

- Given a merge commit in `main` for a subscribed path
  - When the merge is proven
  - Then notifications are sent to subscribed editors via configured channels
- Given a notification failure
  - When delivery fails
  - Then it is retried and logged; the merge is not rolled back

#### Story KBI.3.5 — Scheduler / poller

*As an operator I schedule sync runs so that sources are monitored at the configured interval.*

- Given a source with `poll_interval`
  - When the scheduler runs
  - Then a sync run is queued at the specified cadence
- Given overlapping sync runs for the same source
  - When a new run is queued
  - Then the previous run is deduplicated or queued sequentially

### Technical tasks

| ID | Title | Files / components | Size |
|---|---|---|---|
| KBI-301 | Implement source registry API and models | `src/kb-ingestion/app/api/router.py`, models | M |
| KBI-302 | Implement delta detection and cursor store | `src/kb-ingestion/app/services/source_sync.py` | L |
| KBI-303 | Implement auto-merge policy engine | `src/kb-ingestion/app/services/source_sync.py` | M |
| KBI-304 | Implement notification service | `src/kb-ingestion/app/services/notifier.py` | M |
| KBI-305 | Implement scheduler/poller | `src/kb-ingestion/app/jobs/scheduler.py` | M |
| KBI-306 | Implement deletion proposal flow | `src/kb-ingestion/app/services/source_sync.py` | M |
| KBI-307 | Unit tests for source-sync | `src/kb-ingestion/tests/test_source_sync.py` | L |

---

## Epic KBI.4 — Content-standard enforcement and job queue

| Field | Value |
|---|---|
| ID | KBI.4 |
| Title | Content-standard enforcement and job queue |
| Goal | Обеспечить front-matter-v2, data barrier и надежную обработку ingestion jobs. |
| Scope boundaries | Enforcement перед любым canonical write; queue использует PostgreSQL. |

### Stories

#### Story KBI.4.1 — Front-matter-v2 validator

*As a platform I validate front-matter so that canonical documents follow the schema.*

- Given a document with `additionalProperties` or `access` key
  - When validation runs
  - Then it is rejected with `FRONT_MATTER_INVALID`
- Given `ownership_mode=source_managed` without `origin`
  - When validation runs
  - Then it is rejected with `ORIGIN_REQUIRED`
- Given `archived=true` without `archive` object
  - When validation runs
  - Then it is rejected with `ARCHIVE_INVARIANT_VIOLATION`

#### Story KBI.4.2 — Data barrier gate

*As a platform I enforce data profiles so that PII is not leaked.*

- Given `data_profile=strict` and PII detected
  - When data barrier runs
  - Then the file is rejected and a correction task is created
- Given `data_profile=pii_permitted` without legal basis
  - When data barrier runs
  - Then it is rejected with `LEGAL_BASIS_REQUIRED`
- Given `pii_permitted` content and external provider
  - When extraction/inference is attempted
  - Then external egress is blocked

#### Story KBI.4.3 — Job queue with retry and DLQ

*As an operator I observe ingestion jobs so that failures are handled safely.*

- Given a transient job failure
  - When the worker processes it
  - Then it retries with bounded exponential backoff
- Given a permanent failure
  - When retry budget is exhausted
  - Then the job moves to dead-letter queue with sanitized reason
- Given a running queue
  - When metrics are scraped
  - Then queue lag, attempt count, and outcome are observable

### Technical tasks

| ID | Title | Files / components | Size |
|---|---|---|---|
| KBI-401 | Implement front-matter-v2 validator | `src/kb-ingestion/app/validators/front_matter.py` | M |
| KBI-402 | Implement data barrier gate | `src/kb-ingestion/app/validators/data_barrier.py` | M |
| KBI-403 | Implement PostgreSQL job queue and worker | `src/kb-ingestion/app/jobs/` | L |
| KBI-404 | Implement retry/DLQ and observability | `src/kb-ingestion/app/jobs/`, metrics | M |
| KBI-405 | Unit tests for validators and queue | `src/kb-ingestion/tests/test_validators_queue.py` | M |

---

## Epic KBI.5 — Diagram→Mermaid (evidence-gated)

| Field | Value |
|---|---|
| ID | KBI.5 |
| Title | Diagram→Mermaid |
| Goal | Определять диаграммы и конвертировать их в Mermaid с evidence gate и optional Kroki validation. |
| Scope boundaries | Route disabled по умолчанию; требует golden fixtures, human spot-check, Kroki availability. |

### Stories

#### Story KBI.5.1 — Diagram detection

*As a platform I detect diagram images so that they can be converted to Mermaid.*

- Given an extracted image
  - When media classification runs
  - Then it is flagged as `diagram_candidate=true` if it matches diagram heuristics
- Given a non-diagram image
  - When classification runs
  - Then it follows the standard media class pipeline

#### Story KBI.5.2 — Mermaid generation

*As a platform I generate Mermaid from diagrams so that diagrams become editable text.*

- Given a `diagram_candidate` and enabled Mermaid route
  - When conversion runs
  - Then a vision LLM generates Mermaid source
- Given generated Mermaid
  - When it is produced
  - Then it is marked `automatic=true` and linked to the original image

#### Story KBI.5.3 — Kroki validation gate

*As a platform I validate Mermaid syntax so that invalid output is rejected.*

- Given generated Mermaid and configured Kroki
  - When validation runs
  - Then Kroki attempts to render; failure marks `MERMAID_INVALID`
- Given invalid Mermaid
  - When validation fails
  - Then the image is preserved and Mermaid is discarded

#### Story KBI.5.4 — Evidence gate and activation

*As an operator I activate the Mermaid route only after evidence so that quality is controlled.*

- Given golden fixtures and human spot-check
  - When route activation is requested
  - Then it is enabled only if quality thresholds and license checks pass
- Given a disabled route
  - When a diagram is processed
  - Then it remains an image with alt text

### Technical tasks

| ID | Title | Files / components | Size |
|---|---|---|---|
| KBI-501 | Implement diagram detection heuristics | `src/kb-ingestion/app/services/media_processor.py` | M |
| KBI-502 | Implement Mermaid generation adapter | `src/kb-ingestion/app/adapters/vision_llm.py` | M |
| KBI-503 | Implement Kroki validation client | `src/kb-ingestion/app/adapters/kroki_client.py` | S |
| KBI-504 | Implement evidence gate and activation config | `src/kb-ingestion/app/parsers/extraction_router.py` | M |
| KBI-505 | Golden fixtures and tests | `src/kb-ingestion/tests/test_mermaid.py` | M |

---

## Cross-cutting tasks

| ID | Title | Files / components | Size |
|---|---|---|---|
| KBI-901 | Extract shared object-store module | `src/shared/object_store/`, refactor backup | M |
| KBI-902 | Create kb-ingestion module scaffold and migrations | `src/kb-ingestion/`, alembic | M |
| KBI-903 | Integrate identity and GO clients | `src/kb-ingestion/app/adapters/` | M |
| KBI-904 | Write ADR-018 source-sync auto-merge policy | `specs/corporate-kb/adr/ADR-018-source-sync-auto-merge-policy.md` | M |
| KBI-905 | Local stack integration and smoke tests | `scripts/local_stack.py`, `scripts/smoke_local_stack.py` | M |
| KBI-906 | Evidence collection and sanitized reports | `specs/corporate-kb/evidence/kb-ingestion/`, `_bmad-output/test-artifacts/kb-ingestion/` | S |

---

## Traceability

| Epic | Requirements | Acceptance | Tasks |
|---|---|---|---|
| KBI.1 | R02, R12, R13, I13 | A13, A23 | KBI-101–109 |
| KBI.2 | R01, R02, R07, R12 | A01, A05, A22 | KBI-201–205 |
| KBI.3 | R06, R13, I01, I02 | A14, A17, A18 | KBI-301–307 |
| KBI.4 | R12, R16, I10 | A23, A31, A35 | KBI-401–405 |
| KBI.5 | R12, R15, R18 | A16, A23 | KBI-501–505 |
| Cross-cutting | R14, R17, R18 | A15, A19, A20, A33 | KBI-901–906 |

> Note: ADR-018 source-sync auto-merge policy accepted by owner 2026-11-14.
