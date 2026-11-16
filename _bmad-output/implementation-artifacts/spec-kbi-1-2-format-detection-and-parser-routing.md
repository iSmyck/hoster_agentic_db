---
title: 'KBI.1.2 Format detection and parser routing'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: '90c516eff798fc7446ffdad6c2db8582a7dc5dfc'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-1-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-1-1-upload-endpoint-and-object-store-staging.md'
warnings: []
deferred:
  - summary: >-
      OOXML limits use ZipInfo.file_size; a lying header can still decompress huge payloads.
    evidence: |-
      ooxml_security_check sums advertised file_size. Spec chose ZipInfo.file_size; actual-byte cap is extra surface.
    location: >-
      src/kb-ingestion/app/parsers/ooxml.py
    severity: medium
  - summary: >-
      PPTX slide XML sorted lexicographically (slide10 before slide2).
    evidence: |-
      Content ordering is KBI.1.3/epic context, not 1.2 routing AC.
    location: >-
      src/kb-ingestion/app/parsers/pptx_parser.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Конвертация должна детерминированно выбрать экстрактор по MIME и расширению. Сейчас HTML/JPG не покрыты тестами, битый PPTX даёт 500, zip-bomb и MDX не отсекаются, evidence-gate для PDF не доказан.

**Approach:** `extraction_router` выбирает маршрут до предпросмотра. Известные форматы идут в approved extractor; конфликт MIME/расширения — расширение. Несколько маршрутов: сначала evidence-gated, иначе default. Вредоносное и неизвестное — `SECURITY_BLOCKER` / `UNSUPPORTED_FORMAT` как HTTP 400, не 500.

## Boundaries & Constraints

**Always:**
- Известные форматы: PDF, DOCX, XLSX, HTML, Markdown, PNG, JPG. PPTX — контейнер медиа, тоже маршрутизируется.
- Выбор: расширение файла, затем MIME. Если оба заданы и расходятся — побеждает расширение.
- PDF: маршрут `docling` только при `KB_INGEST_DOCLING_EVIDENCE_GATE=true`; иначе сразу default `pdf_parser`. Если gated-маршрут бросает `ParserError` — fallback на default.
- Неизвестный тип → `UNSUPPORTED_FORMAT`.
- HTML с `<script` или `javascript:` → `SECURITY_BLOCKER`.
- `.mdx` / `text/mdx` → `SECURITY_BLOCKER`.
- OOXML (docx/pptx/xlsx): >256 zip-членов или uncompressed >50 MiB → `SECURITY_BLOCKER`.
- Битый zip/XML/PDF/текст → `UNSUPPORTED_FORMAT` (ParserError), HTTP 400 `{"code","message"}`. Никогда необработанный `ParseError`/500.
- Поверхность: `POST /api/kb/v1/ingest/convert/run` после staging из KBI.1.1. Роутер также вызываем напрямую в unit-тестах.

**Never:**
- Не включать Docling как default. Не ставить vision/LLM.
- Не классифицировать медиа, не писать `attachment://`, не генерировать front-matter и dry-run report (KBI.1.3–1.6).
- Не менять backup, git-orchestrator, ingestion, retrieval, session, `scripts/local_stack.py`.
- Не писать в Git / canonical corpus.
- Не добавлять auth.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| md mime+ext | `note.md` + `text/markdown` | markdown extractor, тело сохранено | N/A |
| ext wins | `note.md` + `application/pdf` | markdown extractor, не PDF | N/A |
| html ok | `<p>Hello HTML</p>` | 200, markdown содержит `Hello` | N/A |
| html script | `<script>alert(1)</script>` | отказ до тела отчёта | 400 `SECURITY_BLOCKER` |
| png/jpg | `scan.png` / `photo.jpg` | image extractor выбран (не UNSUPPORTED) | N/A |
| pdf default | gate off, blank PDF | `pdf_parser`, не docling | N/A |
| pdf gated fallback | gate on, docling stub fail | fallback `pdf_parser`, тело есть | N/A |
| docx/xlsx/pptx | минимальный валидный файл | extractor выбран, тело непустое | N/A |
| unknown | `blob.bin` octet-stream | отказ | 400 `UNSUPPORTED_FORMAT` |
| mdx | `x.mdx` | отказ | 400 `SECURITY_BLOCKER` |
| zip bomb | docx/pptx с >256 members | отказ | 400 `SECURITY_BLOCKER` |
| bad pptx xml | zip + невалидный slide XML | отказ, не 500 | 400 `UNSUPPORTED_FORMAT` |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/parsers/extraction_router.py` — `detect_format`, `_ROUTES`, `extract`; PDF dual-route; ловить не-ParserError.
- `src/kb-ingestion/app/parsers/docling_parser.py` — stub, только при gate.
- `src/kb-ingestion/app/parsers/html_parser.py` — script/javascript blocker.
- `src/kb-ingestion/app/parsers/docx_parser.py` — zip limits уже есть (`_docx_security_check`).
- `src/kb-ingestion/app/parsers/pptx_parser.py` — нет zip-limit, `ET.fromstring` без try → 500.
- `src/kb-ingestion/app/parsers/xlsx_parser.py` — нет zip-limit; openpyxl exception → ParserError.
- `src/kb-ingestion/app/parsers/pdf_parser.py` / `markdown_parser.py` / `image_parser.py` — default extractors.
- `src/kb-ingestion/app/core/config.py` — `DOCLING_EVIDENCE_GATE` default false.
- `src/kb-ingestion/app/api/router.py` — `convert_run` мапит `ConversionError` в HTTP detail.
- `src/kb-ingestion/app/services/converter.py` — вызывает `extraction_router.extract`; не менять media/FM кроме проброса ParserError.
- `src/kb-ingestion/tests/test_convert.py` — смоук; матрицу 1.2 вынести/добавить в `tests/test_extraction_router.py`.
- `src/shared/object_store/` — не трогать (KBI-102/901).
- `src/backup/` — read-only.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/parsers/extraction_router.py` -- MIME/ext, MDX blocker, unexpected exception → ParserError, PDF gated fallback -- детерминизм
- `src/kb-ingestion/app/parsers/pptx_parser.py` -- zip limits + ParseError → UNSUPPORTED_FORMAT -- закрыть 500
- `src/kb-ingestion/app/parsers/docx_parser.py` -- общий OOXML guard если выделен helper -- тот же лимит
- `src/kb-ingestion/app/parsers/xlsx_parser.py` -- zip limits до openpyxl -- bomb
- `src/kb-ingestion/app/parsers/html_parser.py` -- сохранить script blocker -- AC malicious
- `src/kb-ingestion/tests/test_extraction_router.py` -- вся I/O матрица; HTTP для html/mdx/bomb/bad-xml -- доказательство, не смоук

**Acceptance Criteria:**
- Given staged known format, when `convert/run`, then выбран approved extractor (не `UNSUPPORTED_FORMAT`).
- Given MIME≠extension, when detect, then extension wins.
- Given PDF и gate off, when extract, then default parser; docling не вызывается.
- Given PDF и gate on и docling fail, when extract, then default parser.
- Given unsupported или malicious, when convert starts, then 400 `UNSUPPORTED_FORMAT` или `SECURITY_BLOCKER`, не 500.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 24 findings — high 0, medium 8, low 5, false 4, maybe-false 0
- findings:
  - `[low]` `[reject]` Code Map in spec stale vs ooxml.py — fix is spec edit (forbidden this pass)
  - `[medium]` `[patch]` 50 MiB uncompressed untested — added `test_ooxml_uncompressed_total_limit_without_huge_file`
  - `[medium]` `[patch]` xlsx zip-bomb untested — added `test_matrix_xlsx_zip_bomb`
  - `[medium]` `[patch]` PDF gate-on fallback did not spy docling — lambdas at call time + spy asserts one call
  - `[low]` `[defer]` PPTX lexicographic slide order — not 1.2 routing AC
  - `[medium]` `[patch]` unexpected Exception wrap untested / no `__cause__` — test + `__cause__` set
  - `[low]` `[reject]` HTTP not covering every happy-path row — spec Tasks limit HTTP to html/mdx/bomb/bad-xml
  - `[medium]` `[patch]` bad docx XML untested — `test_matrix_bad_docx_xml`
  - `[low]` `[reject]` no env sample for gate — docs/spec edit
  - `[low]` `[patch]` docling missing `-> ParseResult` — annotated
  - `[low]` `[reject]` missing final newlines — cosmetic, everyday impact nil
  - `[false]` `[reject]` `.jpeg`/`.htm` not mapped — `_EXTENSION_MAP` already has `.jpeg` and `.htm`
  - `[low]` `[defer]` sprint-status still says 1.2 unproven — tracker update after story close, not code defect
  - `[medium]` `[defer]` zip bomb via lying file_size — spec chose ZipInfo.file_size
  - `[low]` `[reject]` PPTX without slides returns placeholder — empty archive is not the malformed-XML AC
  - `[false]` `[reject]` MDX without .mdx/text/mdx must sniff — intent only names those two signals
  - `[false]` `[reject]` photo.jpeg + octet-stream unsupported — extension `.jpeg` wins
  - `[low]` `[patch]` ExtractFn vs stub typing — same as ParseResult annotation
  - `[medium]` `[patch]` xlsx bomb claim (edge-case) — same test as above
  - `[medium]` `[patch]` VG: xlsx member bomb — same
  - `[medium]` `[patch]` VG: 50 MiB branch — same
  - `[medium]` `[patch]` VG: docling not observed — same
  - `[medium]` `[patch]` VG: bad docx xml — same
  - `[medium]` `[patch]` VG: Exception wrap (filed defer, patched as trivial test) — same
  - `[low]` `[reject]` intent-alignment: HTTP vs router surface — spec R3 split evidence; convert/run error map pre-existed

## Auto Run Result

- Summary: Router MIME/extension (extension wins), MDX/HTML barriers, shared OOXML zip limits, PDF evidence-gated fallback, PPTX/DOCX XML → ParserError 400. Review patches: testability lambdas, matrix gaps.
- Files: `extraction_router.py`, `ooxml.py`, `docx_parser.py`, `pptx_parser.py`, `xlsx_parser.py`, `docling_parser.py`, `test_extraction_router.py`
- Review: patched 8 medium + 2 low; deferred zip-header bomb and PPTX slide sort; rejected spec-edits, extra MDX sniff, full-HTTP matrix
- Follow-up review: `true` (first pass, ≥2 medium patches). Residual: lying zip headers; PPTX slide order for 1.3.
- Verification: `uv run pytest -q src/kb-ingestion/tests/test_extraction_router.py src/kb-ingestion/tests/test_convert_upload.py` → 40 passed; `ruff check src/kb-ingestion` clean
- Commit withheld: AGENTS.md / user rule — no commit unless explicit
- Residual: Docling remains stub; no MinIO

## Design Notes

Общий helper для OOXML zip-limit допустим (`parsers/ooxml.py`), чтобы docx/pptx/xlsx не копировали пороги. Пороги: 256 members, 50 MiB uncompressed (`file_size` из ZipInfo). PPTX slide heading (`## Slide N`) — KBI.1.3/контент, не эта стори.

Docling stub может бросать `ParserError`; роутер обязан fallback, а не отдать ошибку клиенту, пока жив default.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_extraction_router.py src/kb-ingestion/tests/test_convert_upload.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
