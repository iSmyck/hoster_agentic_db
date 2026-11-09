---
title: 'T12a Deterministic dry-run import and admission gates'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/contracts/front-matter.schema.json
  - specs/corporate-kb/contracts/source-origin.schema.json
  - specs/corporate-kb/contracts/export-manifest.schema.json
  - specs/corporate-kb/components/ingestion-connectors.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-6-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that a dry-run import is deterministic, produces stable path→ID mapping and provenance, runs admission gates before corpus/preview admission, blocks PII/media/security hazards, and writes zero canonical records.

**Approach:** Create a T12a harness that exercises synthetic YAML fixtures for deterministic dry-run output, mandatory admission gates, path→stable-ID mapping, ownership modes, attachment manifests, and explicit rejection of unsafe inputs.

## Boundaries & Constraints

**Always:**
- Dry-run returns path→stable-ID mapping, tree, provenance, source versions/hashes, relative links/anchors, attachment manifests, ownership mapping, original/extracted hashes, and explicit losses/errors.
- Replaying the same source/config reproduces the manifest; changed inputs create new evidence rather than mutating old evidence.
- Admission gates run before corpus or preview admission: stable source owner and completed data barrier are mandatory.
- Every PII hit requires human disposition; critical/handwritten media is blocked until required human transcription/verification exists.
- Traversal, symlinks, absolute/ambiguous paths, executable HTML/MDX/XSS, secrets, invalid UTF-8, oversized/decompression-bomb inputs and mutable/unhashed attachments are rejected.
- No branch, MR, `main` commit, active index, or merged cursor is created.

**Never:**
- Do not use real source corpus, credentials, or production data.
- Do not treat a dry-run as a canonical write or as approval to load content.
- Do not allow blocked content to enter the preview or corpus with a warning-only downgrade.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Deterministic manifest | Same source/config replay | Identical path→ID mapping, hashes, manifest SHA | Changed output without changed input → FAIL |
| Admission gates | Missing owner/barrier or PII/media hazard | Rejected before corpus/preview with explicit code | Hazard admitted → FAIL |
| Path→ID mapping | Repository-relative NFC paths, source IDs | Stable opaque UUID per path, `DOC-0001` case preserved | Collision/rewrite/absolute path → FAIL |
| Security blockers | Traversal/symlink/executable/secret/invalid UTF-8/oversize/bomb/unhashed attachment | SECURITY_REJECTED with zero writes | Any canonical write or preview exposure → FAIL |
| Zero canonical writes | Dry-run execution | `canonical_writes=0`, no branch/MR/index/cursor | Any Git/main/index side effect → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t12a/run_t12a_tests.py` — main harness.
- `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml` — synthetic dry-run/admission/fixture scenarios.
- `specs/corporate-kb/contracts/front-matter.schema.json` — canonical document front matter.
- `specs/corporate-kb/contracts/source-origin.schema.json` — source ownership/provenance contract.
- `specs/corporate-kb/contracts/export-manifest.schema.json` — manifest closure contract.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t12a/run_t12a_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t12a/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t12a/import-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t12a/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `6-1-t12a-...` → `done`.

**Acceptance Criteria:**
- [x] Given the same source and configuration, replay produces identical path→ID mapping, hashes, and manifest SHA.
- [x] Given missing stable source owner or incomplete data barrier, admission is rejected with explicit code and zero writes.
- [x] Given PII hits or critical/handwritten media, import requires human disposition or verification and blocks admission.
- [x] Given traversal, symlinks, absolute/ambiguous paths, executable content, secrets, invalid UTF-8, oversized/decompression-bomb inputs or mutable/unhashed attachments, the input is rejected before corpus/preview with zero canonical writes.
- [x] Given a dry-run completion, no branch, MR, `main` commit, active index, or merged cursor is created.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns; validators operate on synthetic YAML fixtures. Live source/GitLab/object-store/IdP checks remain BLOCKED.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models a dry-run state machine that records path→stable-ID mapping, provenance, links, attachments, losses/errors and a deterministic manifest SHA. Admission gates are evaluated before any simulated corpus/preview admission. Real source corpus and production credentials are not used.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t12a/run_t12a_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t12a/run_t12a_tests.py` -- expected: writes `import-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t12a/import-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t12a/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
