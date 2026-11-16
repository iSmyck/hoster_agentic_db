---
title: 'KBI.5.4 Evidence gate and activation'
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
      Human spot-check and license_ok are operator flags, not an independent review record.
    evidence: |-
      POST /mermaid/activate stores booleans on MermaidRoute.
    location: >-
      src/kb-ingestion/app/services/mermaid_route.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Mermaid нельзя включать без evidence: provider, golden, spot-check, license, Kroki.

**Approach:** `POST /api/kb/v1/ingest/mermaid/activate`. Enabled iff все условия. Disabled: diagram остаётся image+alt.

## Boundaries & Constraints

**Always:**
- Условия: vision.configured, kroki.available, human_spot_check, license_ok, golden fixtures pass (server-side).
- Activate 200 `{enabled, reasons[]}`. Не enabled при любом reason.
- Default app: disabled.

**Never:**
- Не live vision. Не owner-approval за владельца.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| all gates | flags + stubs ready | enabled true | N/A |
| no spot-check | human_spot_check false | enabled false, reason | N/A |
| golden fail | invalid_next before activate | GOLDEN_FIXTURES_FAILED | N/A |
| disabled convert | default app, diagram image | skipped, image markdown | N/A |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/services/mermaid_route.py` — evidence gate + cached golden.
- `src/kb-ingestion/app/api/router.py` — GET `/mermaid/status`, POST `/mermaid/activate`.
- `src/kb-ingestion/tests/test_mermaid.py` — 5.4 rows.

## Tasks & Acceptance

**Acceptance Criteria:**
- Given golden fixtures and human spot-check, when route activation is requested, then it is enabled only if quality thresholds and license checks pass.
- Given a disabled route, when a diagram is processed, then it remains an image with alt text.

## Spec Change Log

- 2026-11-17: activate/status; golden cached at activate; default disabled.
- 2026-11-17 review: golden failure cannot be client-claimed.

## Review Triage Log

### 2026-11-17 — Review pass
- `[medium]` `[patch]` client could claim golden_pass — server runs StubVisionLLM.golden_pass()
- `[low]` `[defer]` spot-check is a boolean, not a DecisionRecord

## Auto Run Result

- Default route off; activation requires vision, Kroki, spot-check, license, and golden match.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 194 passed; ruff clean.
- Commit withheld: user rule — no commit unless explicit.
