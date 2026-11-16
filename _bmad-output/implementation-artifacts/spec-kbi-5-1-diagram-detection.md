---
title: 'KBI.5.1 Diagram detection'
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
      Heuristics are filename tokens only; no pixel/CV detector.
    evidence: |-
      is_diagram_candidate looks at Path(filename).name tokens.
    location: >-
      src/kb-ingestion/app/services/media_processor.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Классификатор ставит `diagram` в `critical`, но нет флага кандидата на Mermaid.

**Approach:** `diagram_candidate` по токенам имени. Не-диаграммы идут обычным media_class pipeline.

## Boundaries & Constraints

**Always:**
- Tokens: `diagram`, `schematic`, `flowchart`, `architecture`, `uml`, `mermaid`.
- Кандидат не меняет пять media_class.
- `chart-critical.png` — critical, candidate=false.
- Convert attachment несёт `diagram_candidate`.

**Never:**
- Не vision. Не Kroki. Не включать route.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| diagram name | wiring-schematic.png | candidate true, class critical | N/A |
| non-diagram | figure.png | candidate false, illustrative | N/A |
| critical not diagram | chart-critical.png | candidate false, critical | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/services/media_processor.py` — is_diagram_candidate.
- `src/kb-ingestion/app/schemas/convert.py` — diagram_candidate on attachment.
- `src/kb-ingestion/tests/test_mermaid.py` — 5.1 rows.

## Tasks & Acceptance

**Acceptance Criteria:**
- Given an extracted image, when media classification runs, then diagram_candidate=true if heuristics match.
- Given a non-diagram image, when classification runs, then it follows the standard media class pipeline.

## Spec Change Log

- 2026-11-17: diagram_candidate flag; tokens listed above.
- 2026-11-17 review: non-diagram does not call vision even when route enabled.

## Review Triage Log

### 2026-11-17 — Review pass
- `[low]` `[patch]` non-diagram might call vision — convert only if candidate
- `[low]` `[defer]` no CV/pixel classifier

## Auto Run Result

- Filename heuristics set diagram_candidate without changing media_class.
- Verification: 194 passed; ruff clean. Commit withheld.
