---
title: 'KBI-906 Evidence collection'
type: 'feature'
created: '2026-11-17'
status: 'done'
---

## Intent

**Problem:** Cross-cutting requires sanitized evidence under `specs/corporate-kb/evidence/kb-ingestion/` and raw pytest under `_bmad-output/test-artifacts/kb-ingestion/`.

**Approach:** Write a sanitized index plus a machine JSON summary of pytest/ruff. No secrets, tokens, or live host names beyond `127.0.0.1` placeholders.

## Boundaries & Constraints

**Always:**
- Sanitized markdown in `specs/corporate-kb/evidence/kb-ingestion/`.
- Raw pytest JSON in `_bmad-output/test-artifacts/kb-ingestion/`.
- Mark live MinIO/Identity/GO/GitLab as BLOCKED, not PASS.

**Never:**
- Do not copy `.env`, tokens, or unredacted personal data.
- Do not mark owner live DONE.

## Code Map

- `specs/corporate-kb/evidence/kb-ingestion/README.md`
- `specs/corporate-kb/evidence/kb-ingestion/pytest.md`
- `_bmad-output/test-artifacts/kb-ingestion/pytest-summary.json`

## Tasks & Acceptance

**Acceptance Criteria:**
- Given the evidence index, when read, then it records VERIFIED(synthetic) and lists BLOCKED live gates.
- Given the artifact JSON, when read, then it includes pytest command, pass count, and ruff status.

## Spec Change Log

- 2026-11-17: sanitized index + pytest JSON.

## Review Triage Log

### 2026-11-17 — Review pass
- `[low]` `[reject]` check live smoke as PASS — stack was not run
- `[low]` `[patch]` evidence test asserts BLOCKED live_gates key exists

## Auto Run Result

- Evidence pack present; claim VERIFIED(synthetic) only.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 211 passed; ruff clean.
