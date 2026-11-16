---
title: 'KBI.5.3 Kroki validation gate'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '2e50ae6979a2bafc34a3ea1c7de7acd5fc26c58b'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-5-context.md'
warnings: []
deferred:
  - summary: >-
      HttpKrokiClient is unused in create_app; tests inject StubKrokiClient. Live Kroki not claimed.
    evidence: |-
      Default StubKrokiClient.available=False.
    location: >-
      src/kb-ingestion/app/adapters/kroki_client.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Сгенерированный Mermaid может быть синтаксически битым.

**Approach:** StubKroki (HttpKrokiClient unused in tests) валидирует source. Failure: `MERMAID_INVALID` в errors[], mermaid discarded, image preserved.

## Boundaries & Constraints

**Always:**
- Validate только если generation произошла.
- Invalid: mermaid_source=null, mermaid_status=invalid, image в markdown, errors code MERMAID_INVALID.
- Convert 200, не 400 (fallback).

**Never:**
- Не live Kroki PASS. Не удалять image attachment.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| valid | Kroki ok | mermaid_status=validated, fence in markdown | N/A |
| invalid Kroki | fail_next | image kept, mermaid discarded | errors MERMAID_INVALID |
| invalid vision | INVALID source | same fallback | errors MERMAID_INVALID |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/adapters/kroki_client.py` — Stub + Http.
- `src/kb-ingestion/app/services/mermaid_route.py` — convert_diagram.
- `src/kb-ingestion/tests/test_mermaid.py` — 5.3 rows.

## Tasks & Acceptance

**Acceptance Criteria:**
- Given generated Mermaid and configured Kroki, when validation runs, then Kroki attempts to render; failure marks MERMAID_INVALID.
- Given invalid Mermaid, when validation fails, then the image is preserved and Mermaid is discarded.

## Spec Change Log

- 2026-11-17: stub Kroki; fallback image; MERMAID_INVALID in errors.
- 2026-11-17 review: invalid vision output discarded the same way.

## Review Triage Log

### 2026-11-17 — Review pass
- `[low]` `[patch]` invalid LLM output untested — test_invalid_vision_output_discarded
- `[low]` `[defer]` HttpKrokiClient live

## Auto Run Result

- Invalid Mermaid falls back to image; convert stays 200 with errors[].
- Verification: 194 passed; ruff clean. Commit withheld.
