---
title: 'T17 Conditional evidence-gated extraction, media and OCR quality'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/components/ingestion-connectors.md
  - specs/corporate-kb/content-standard.md
  - specs/corporate-kb/adr/ADR-016-repository-per-space.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-8-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Non-Markdown extraction cannot be activated without owner-authorized real samples, golden/loss evidence, media/OCR classification and human verification. Markdown-only workloads must be explicitly recorded N/A by ADR/owner decision when the conditional scope is not activated.

**Approach:** Create a T17 harness that exercises synthetic YAML fixtures for extraction route gating, pinned Docling assessment, golden/loss fixtures by format, media class handling, malicious input rejection, approved-provider/data-profile/egress enforcement, and explicit BLOCKED/N-A handling when owner samples are absent.

## Boundaries & Constraints

**Always:**
- Activation requires owner-supplied authorized representative samples and agreement on formats, quality review and data/media profile.
- Only synthetic or sanitized derivative fixtures and hashes enter the workspace; real corpus samples require separate owner authorization.
- The pinned Docling integration is assessed first; a second pipeline requires documented unmet need, approved ADR and separate compatibility/license/rollback assessment.
- Golden fixtures measure page/slide counts, encoding, reading order, table structure/numbers, links/anchors and omissions/duplications by format and risk.
- Empty/garbled output, unsupported formats, extraction loss and OCR disagreement are quarantined with the original recoverable.
- Decorative content is excluded; illustrative assets keep captions; substantive automatic descriptions are explicitly labelled and cite the original page/slide; critical/handwritten knowledge enters the index only after required human transcription/verification.
- Malicious or malformed samples are rejected before corpus/preview; failed extraction never advances source `merged` or publishes a partial index.

**Never:**
- Do not activate non-Markdown extraction without owner-authorized real samples and ADR.
- Do not fabricate golden/loss evidence or OCR quality results from synthetic fixtures as real sample PASS.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Route activation gate | Owner samples, formats, quality agreement, data/media profile | Activation allowed only with all required owner inputs | Missing owner authorization → BLOCKED / N-A |
| Docling assessment | Pinned Docling integration | Assessed; compatibility/license/rollback documented | Undocumented second pipeline → FAIL |
| Golden fixtures | Format, page/slide count, encoding, reading order, tables, links | Golden metrics recorded per format; supported → PASS | Unsupported format / unmet threshold → FAIL |
| Loss/quarantine | Empty/garbled output, unsupported format, OCR disagreement | Quarantined with original recoverable; source not merged | Partial index published / original lost → FAIL |
| Media classes | Decorative/illustrative/substantive/critical/handwritten | Decorative excluded; illustrative+caption; substantive labelled+cite; critical verified | Critical/handwritten auto-indexed → FAIL |
| Malformed/malicious | Malformed samples, executable HTML/MDX, secrets, oversized | Rejected before corpus/preview | Allowed into corpus → FAIL |
| Provider/profile/egress | Approved provider, data profile, egress route | Only approved combination used; unplanned fallback blocked | Unapproved route/fallback/PII egress → FAIL |

</frozen-after-approval>

## Open Questions

- Owner has not authorized real non-Markdown samples or decided to activate the conditional scope.

## Code Map

- `_bmad-output/test-artifacts/t17/run_t17_tests.py` — main harness.
- `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml` — synthetic extraction/media/OCR fixtures.
- `specs/corporate-kb/content-standard.md` — DocOps/media/content rules.
- `specs/corporate-kb/components/ingestion-connectors.md` — extraction seams.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t17/run_t17_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t17/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t17/extraction-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t17/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `8-3-t17-...` → `done`.

**Acceptance Criteria:**
- [x] Given activation gate fixtures, non-Markdown extraction routes remain BLOCKED or N-A until owner-supplied authorized samples, format agreement, quality review and data/media profile exist.
- [x] Given Docling assessment fixtures, the pinned Docling integration is assessed first and a second pipeline requires documented unmet need, approved ADR and separate compatibility/license/rollback assessment.
- [x] Given golden fixtures, page/slide counts, encoding, reading order, table structure/numbers, links/anchors and omissions/duplications are measured per format and risk.
- [x] Given loss fixtures, empty/garbled output, unsupported formats, extraction loss and OCR disagreement are quarantined with the original recoverable and source `merged` is not advanced.
- [x] Given media-class fixtures, decorative content is excluded, illustrative assets keep captions, substantive auto-descriptions are labelled and cite the original, and critical/handwritten knowledge requires human verification before indexing.
- [x] Given malicious/malformed fixtures, samples are rejected before corpus/preview.
- [x] Given provider/profile/egress fixtures, only approved providers, data profiles and egress routes are used; unplanned fallback or PII egress is blocked.
- [x] Given completed run, evidence contains no real samples/secrets/absolute paths and real sample authorization is recorded as BLOCKED.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns via `harness_common.py`; validators operate on synthetic YAML fixtures. Real extraction/OCR quality evidence on owner-authorized samples remains BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the gating rules and quality checks that must be satisfied before any non-Markdown extraction route is activated. It treats the absence of owner-authorized real samples as a BLOCKED/N-A condition, not a PASS, and does not fabricate OCR or golden-set results.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t17/run_t17_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t17/run_t17_tests.py` -- expected: writes `extraction-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t17/extraction-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t17/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
