---
title: 'KBI.4.2 Data barrier gate'
type: 'feature'
created: '2026-11-17'
status: 'done'
route: 'dispatch'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: '2e50ae6979a2bafc34a3ea1c7de7acd5fc26c58b'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-kbi-4-context.md'
  - '{project-root}/specs/corporate-kb/content-standard.md'
warnings: []
deferred:
  - summary: >-
      Scanner is synthetic canary/email/phone regex, not a production NER model.
      Live hoster.ai egress is not executed.
    evidence: |-
      scan_pii looks for SYNTHETIC_PII, email, +7 phone. EGRESS_FORBIDDEN is a provider allow-list.
    location: >-
      src/kb-ingestion/app/validators/data_barrier.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** strict-профиль не ловит PII до GO; pii_permitted без основания и внешний egress не закрыты на одном гейте.

**Approach:** `data_barrier.enforce` на тексте. Synthetic canaries: `SYNTHETIC_PII`, email, `+7` phone. `POST /validate/data-barrier`. Convert/run: PII → status=blocked + correction task. Source pii_permitted без legal_basis не регистрируется.

## Boundaries & Constraints

**Always:**
- `strict` + hit → `PII_BLOCKED`, correction task `PII_REVIEW_REQUIRED`. Hits — kind+offset, не сырой PII.
- `pii_permitted` без непустого `legal_basis` → `LEGAL_BASIS_REQUIRED` (validate, convert/run, source register).
- `pii_permitted` + `inference_provider` ∉ {`internal`,`hoster.ai`} → `EGRESS_FORBIDDEN`.
- `strict` без hit → valid.
- Convert PII: dry-run 200 `status=blocked`, correction task, не ready.
- Только synthetic fixtures.

**Never:**
- Не реальный PII в репозитории/логах. Не внешний HTTP. Не live hoster.ai.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| strict PII | SYNTHETIC_PII in text | отказ + correction task | 400 PII_BLOCKED |
| pii no basis | pii_permitted, legal_basis empty | отказ | 400 LEGAL_BASIS_REQUIRED |
| external | pii_permitted + provider=external/openai | отказ | 400 EGRESS_FORBIDDEN |
| strict clean | ordinary markdown | valid | N/A |
| convert PII | convert/run markdown with canary | status blocked + task | N/A |
| convert basis | convert/run pii_permitted no basis | отказ | 400 LEGAL_BASIS_REQUIRED |
| source register | pii_permitted source, no legal_basis | отказ | 400 LEGAL_BASIS_REQUIRED |

</intent-contract>

## Code Map

- `src/kb-ingestion/app/validators/data_barrier.py` — scan + enforce.
- `src/kb-ingestion/app/services/converter.py` — barrier; PII blocks ready.
- `src/kb-ingestion/app/services/source_sync.py` — legal_basis on register; barrier on markdown.
- `src/kb-ingestion/app/api/router.py` — POST `/validate/data-barrier`.
- `src/kb-ingestion/tests/test_validators_queue.py` — 4.2 rows.

## Tasks & Acceptance

**Execution:**
- `data_barrier.py` -- enforce -- PII/basis/egress
- `converter.py` -- convert/run -- blocked + correction
- `source_sync.py` -- register + markdown -- LEGAL_BASIS / PII_BLOCKED / EGRESS
- `test_validators_queue.py` -- матрица 4.2 -- доказательство

**Acceptance Criteria:**
- Given data_profile=strict and PII detected, when data barrier runs, then the file is rejected and a correction task is created.
- Given pii_permitted without legal_basis, when data barrier or source register or convert/run runs, then LEGAL_BASIS_REQUIRED.
- Given pii_permitted content and external provider, when extraction/inference is attempted, then EGRESS_FORBIDDEN.
- Given convert/run with SYNTHETIC_PII under strict, when dry-run completes, then status=blocked and a PII_REVIEW_REQUIRED correction task exists.

## Spec Change Log

- 2026-11-17: data_barrier; validate endpoint; convert blocked; source legal_basis.
- 2026-11-17 review: convert pii_permitted without basis; source-sync openai egress.

## Review Triage Log

### 2026-11-17 — Review pass (blind + edge + verification + intent)
- verdicts: high 0, medium 0, low patched/deferred
- findings:
  - `[low]` `[patch]` convert/run pii_permitted skipped barrier — LEGAL_BASIS_REQUIRED
  - `[low]` `[patch]` source-sync external provider untested — EGRESS_FORBIDDEN
  - `[low]` `[patch]` hits must not include raw excerpts — kind+offset only
  - `[low]` `[defer]` regex is not production PII NER; live hoster.ai untested
  - `[low]` `[reject]` real PII fixtures — synthetic canaries only

## Auto Run Result

- Strict PII blocks with a correction task; pii_permitted requires legal_basis and an internal/hoster.ai provider.
- Files: `validators/data_barrier.py`, `services/converter.py`, `services/source_sync.py`, `schemas/convert.py`, `schemas/source_sync.py`, `tests/test_validators_queue.py`
- Follow-up review: `true`. Residual: live hoster.ai / production scanner.
- Verification: `uv run pytest -q src/kb-ingestion/tests` → 186 passed; ruff clean.
- Commit withheld: user rule — no commit unless explicit.

## Verification

**Commands:**
- `uv run pytest -q src/kb-ingestion/tests` -- expected: PASS (186)
- `uv run ruff check src/kb-ingestion` -- expected: чисто
