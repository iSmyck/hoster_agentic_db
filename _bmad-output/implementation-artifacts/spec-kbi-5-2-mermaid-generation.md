---
title: 'KBI.5.2 Mermaid generation'
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
      StubVisionLLM only; live vision LLM / paid egress not claimed.
    evidence: |-
      Default StubVisionLLM.configured=False. No HTTP vision client.
    location: >-
      src/kb-ingestion/app/adapters/vision_llm.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Diagram остаётся только картинкой; нет editable Mermaid.

**Approach:** Если route enabled и candidate: StubVisionLLM генерирует source. `automatic=true`, связь с image `object_id`. Markdown: fenced `mermaid` блок.

## Boundaries & Constraints

**Always:**
- Generation только при `mermaid_route.enabled`.
- Attachment: `mermaid_source`, `mermaid_status=generated|validated`, `automatic=true`.
- Live vision не вызывается.

**Never:**
- Не paid LLM. Не включать route без 5.4.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| enabled candidate | schematic + route on | mermaid_source set, automatic, fence | N/A |
| disabled | candidate, route off | mermaid_status=skipped, image markdown | N/A |
| non-diagram | figure.png, route on | mermaid_status=none, vision not called | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/adapters/vision_llm.py` — StubVisionLLM + GOLDEN_MERMAID.
- `src/kb-ingestion/app/services/converter.py` — generate when enabled.
- `src/kb-ingestion/tests/test_mermaid.py` — 5.2 rows.

## Tasks & Acceptance

**Acceptance Criteria:**
- Given a diagram_candidate and enabled Mermaid route, when conversion runs, then a vision LLM generates Mermaid source.
- Given generated Mermaid, when it is produced, then it is marked automatic=true and linked to the original image.

## Spec Change Log

- 2026-11-17: stub generation; mermaid fence; automatic + object_id.
- 2026-11-17 review: skip vision for non-candidates.

## Review Triage Log

### 2026-11-17 — Review pass
- `[medium]` `[defer]` live vision LLM
- `[low]` `[patch]` vision called for figure.png — gated on diagram_candidate

## Auto Run Result

- Enabled route writes mermaid fence and keeps image object_id on the attachment.
- Verification: 194 passed; ruff clean. Commit withheld.
