---
title: 'KBI.1.3 Media extraction and classification'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: '90c516eff798fc7446ffdad6c2db8582a7dc5dfc'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-1-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-kbi-1-2-format-detection-and-parser-routing.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** AC требует staged attachments с `sha256`/`media_type` из DOCX/PDF/PPTX и классы `decorative|illustrative|substantive|critical|handwritten`. PDF `page.images` требует Pillow (его нет). Tiny PNG с `critical` в имени сейчас decorative из‑за size&lt;512.

**Approach:** Извлекать встроенные изображения из DOCX/PPTX (`word/media`, `ppt/media`) и PDF XObject `/Subtype /Image` без Pillow. Классификатор rule-based: watermark/icon/logo → decorative; signature/handwritten → handwritten; critical/diagram/schematic → critical (токен имени важнее size&lt;512); иначе size&gt;50000 substantive, иначе illustrative. critical/handwritten без verification → `status=blocked`, `verification_status=pending`. Staging в object store как отдельный объект.

## Boundaries & Constraints

**Always:**
- Каждый extracted image: `store.put` → `object_id`, `sha256`, `version`, `size`, `media_type`.
- Классы только пяти enum. `requires_verification` = critical|handwritten.
- Имя `watermark|icon|logo` → decorative даже если файл большой.
- Имя `signature|handwritten|handwriting` → handwritten; `critical|diagram|schematic` → critical. Эти токены побеждают эвристику size&lt;512.
- size&lt;512 без таких токенов и без `primary_asset` → decorative.
- PDF: обход Resources XObject, не `page.images` (Pillow запрещён в этой стори).
- Convert surface: `POST /api/kb/v1/ingest/convert/run`.
- PPTX slide headings `## Slide N` с numeric sort (`slide2` before `slide10`) — источник текста; медиа всё равно из `ppt/media`.

**Never:**
- Не добавлять Pillow / pypdf[image]. Не vision/LLM. Не Mermaid.
- Не требовать `attachment://` в markdown (KBI.1.4). Не front-matter schema (KBI.1.5). Не correction_tasks контракт (KBI.1.6) — `status=blocked` достаточно.
- Не менять backup, GO, local_stack. Не Git write. Не auth.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| docx media | DOCX + `word/media/figure.png` ≥512B | attachment sha256+media_type, class illustrative | N/A |
| pptx media | PPTX + `ppt/media/photo.png` ≥512B | staged object, count store +1 | N/A |
| pdf xobject | PDF with `/Subtype /Image` XObject | embedded_media ≥1, staged sha256 | N/A |
| decorative | filename watermark, any size | media_class=decorative, not blocked | N/A |
| handwritten | signature-scan.png 67B | handwritten, blocked, pending | N/A |
| critical tiny | chart-critical.png 67B | critical, blocked, pending | N/A |
| substantive | 50001 bytes, generic name | substantive, not_required | N/A |
| logo | logo.png large | decorative | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/parsers/pdf_parser.py` — сейчас `page.images` → ImportError без Pillow. Заменить обходом XObject.
- `src/kb-ingestion/app/parsers/docx_parser.py` / `pptx_parser.py` — media уже читается.
- `src/kb-ingestion/app/services/media_processor.py` — size&lt;512 раньше critical tokens.
- `src/kb-ingestion/app/services/converter.py` — classify + `store.put` + blockers.
- `src/kb-ingestion/tests/test_convert.py` — смоук PPTX не проверяет class/blocked.
- Новый: `src/kb-ingestion/tests/test_media.py` — матрица 1.3.

## Tasks & Acceptance

**Execution:**
- `src/kb-ingestion/app/parsers/pdf_parser.py` -- XObject extract without Pillow -- PDF AC
- `src/kb-ingestion/app/services/media_processor.py` -- token order vs size -- critical tiny
- `src/kb-ingestion/app/parsers/pptx_parser.py` -- numeric slide order -- deferred 1.2 KEEP
- `src/kb-ingestion/tests/test_media.py` -- вся матрица + HTTP convert/run для handwritten/critical/pdf -- доказательство

**Acceptance Criteria:**
- Given DOCX/PDF/PPTX with embedded images, when media extraction, then each image staged with sha256 and media_type.
- Given extracted image, when classify, then one of five labels.
- Given critical or handwritten without verification, when convert completes, then status=blocked and verification_status=pending.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 18 findings — high 0, medium 6, low 6, false 4, maybe-false 0
- findings:
  - `[medium]` `[patch]` PDF convert/run missing critical blocked — added `test_http_pdf_critical_xobject_blocked`
  - `[medium]` `[patch]` DCTDecode media_type untested — `test_pdf_dctdecode_media_type_jpeg`
  - `[medium]` `[patch]` primary_asset skipped for `(empty pdf)` — converter treats placeholders as empty
  - `[low]` `[patch]` PNG magic without `.png` suffix — `_image_media_type` checks `\x89PNG`
  - `[medium]` `[defer]` Form-nested XObjects not walked — extra recursion, real PDFs; record for later
  - `[low]` `[reject]` correction_tasks in converter — 1.6 surface, spec Never says not required here; leave code
  - `[false]` `[reject]` pptx_parser hunk missing — file was already untracked; numeric sort present
  - `[false]` `[reject]` blocker KeyError — converter always sets code/detail
  - `[low]` `[defer]` pdf get_data fail untested — rare; wrapper exists
  - `[low]` `[defer]` outer pdf extraction failed untested — same
  - `[low]` `[reject]` spec Code Map stale — spec-edit forbidden
  - `[low]` `[reject]` missing EOF newlines — cosmetic
  - `[medium]` `[defer]` PNG FlateDecode without magic — heuristic; PNG magic now covers common case
  - `[false]` `[reject]` must omit correction_tasks from report — existing 1.6 field; not a 1.3 regression
  - `[low]` `[reject]` HTTP PDF decorative/class not fully mirrored — critical PDF HTTP added
  - `[false]` `[reject]` intent forbids attachment:// in converter — Never = not 1.3 AC, leftover 1.4 code OK
  - `[low]` `[reject]` primary_asset not in verbatim AC — needed for image-only docs; patched
  - `[low]` `[reject]` PPTX HTTP omits class — sha256+count is the matrix row

## Auto Run Result

- PDF XObject extract without Pillow; classifier tokens beat size; PPTX numeric slides; media staged with sha256.
- Review patches: placeholder primary_asset, DCTDecode test, PDF critical HTTP, PNG magic.
- Follow-up: true (≥2 medium patches). Residual: Form XObjects.
- Verification: `pytest test_media.py` 23 passed; ruff clean. No commit (AGENTS.md).

## Design Notes

PDF fixture: PdfWriter blank page + Image XObject stream (`/DeviceRGB` 1×1) in `/Resources /XObject`. Читать `obj.get_data()`, не `page.images`.

Filter `/DCTDecode` → `image/jpeg`, иначе `image/png` если имя `.png`, иначе `image/jpeg`.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests/test_media.py src/kb-ingestion/tests/test_extraction_router.py` -- expected: PASS
- `uv run ruff check src/kb-ingestion` -- expected: чисто
