---
title: 'T03b Per-Space policy enforcement and revocation'
type: 'feature'
created: '2026-11-08'
status: 'draft'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '788e299a5316c7d5df685a8f11b043ff36135a10'
context:
  - specs/corporate-kb/contracts/authz-context.schema.json
  - specs/corporate-kb/contracts/approval-policy.schema.json
  - specs/corporate-kb/contracts/access-policy.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-2-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Нет executable evidence для per-Space access/approval policy enforcement: longest-prefix rule selection, disjoint Spaces, path normalization, revocation epoch и anti-enumeration errors.

**Approach:** Создать T03b harness, который на synthetic fixtures валидирует `AuthzContext-v2`, access/approval policy schemas, longest-prefix selection, per-Space isolation и revocation epoch semantics.

## Boundaries & Constraints

**Always:**
- Каждый Space — независимый repository binding, policy bundle, revision SHAs, group snapshot, revocation epoch.
- Policy path mapping lossless: `/` ↔ empty prefix, `/pricing` ↔ `pricing`.
- Longest-normalized-prefix rule selection; parent-prefix groups not unioned.
- Errors use `{code, message, request_id, retryable}` с sanitized details.

**Never:**
- Не использовать real IdP/AuthZ endpoints или credentials.
- Не вводить production corpus.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Per-Space isolation | Two Spaces with different policy bundles/revisions | PASS: no shared binding | Shared bundle → FAIL |
| Longest-prefix | `/pricing/current.md` with `/` and `/pricing` rules | `/pricing` rule selected PASS | Union of parent groups → FAIL |
| Path normalization | `/pricing`, `pricing`, `/pricing/`, `..` | `/pricing` ↔ `pricing` PASS; `/pricing/` and `..` FAIL | — |
| Revocation epoch | Context with old epoch vs new policy | Old epoch rejected/stale PASS | Stale allowed → FAIL |
| Error shape | Denied request | `{code,message,request_id,retryable}` PASS | Missing field → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t03a/run_identity_tests.py` — reference harness pattern.
- `specs/corporate-kb/contracts/authz-context.schema.json` — per-Space authz context.
- `specs/corporate-kb/contracts/approval-policy.schema.json` — approval policy schema.
- `specs/corporate-kb/contracts/access-policy.schema.json` — access policy schema.
- `_bmad-output/implementation-artifacts/epic-2-context.md` — policy and revocation decisions.

## Tasks & Acceptance

**Execution:**
- [ ] `_bmad-output/test-artifacts/t03b/run_policy_tests.py` — main harness.
- [ ] `_bmad-output/test-artifacts/t03b/fixtures/` — synthetic per-Space policy YAML fixtures.
- [ ] `_bmad-output/test-artifacts/t03b/validators/` — AuthzContext, policy, longest-prefix, revocation, error-shape validators.
- [ ] `_bmad-output/test-artifacts/t03b/policy-results.json` + `summary.md`.
- [ ] `specs/corporate-kb/evidence/t03b/` — sanitized evidence.
- [ ] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `2-3-t03b-...` → `done`.

**Acceptance Criteria:**
- Given two Spaces with independent versioned policies, when AuthzContext validator runs, then each Space has its own repository binding, bundle, revision SHAs, group snapshot and revocation epoch.
- Given overlapping prefixes, when longest-prefix validator runs, then exactly one rule is selected and parent-prefix groups are not unioned.
- Given absolute/relative policy paths with Unicode/separator variants, when path validator runs, then `/` ↔ empty prefix and `/pricing` ↔ `pricing` round-trip losslessly, and ambiguous variants are rejected.
- Given old revocation epoch, when revocation validator runs, then context is marked stale/rejected.
- Given denied request, when error-shape validator runs, then response uses `{code,message,request_id,retryable}` with sanitized details.
- Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

T03b harness reuse T01/T02/T03a reporters and sanitize patterns. Validators operate on synthetic YAML policy fixtures and JSON schemas; live IdP/AuthZ/GO checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t03b/run_policy_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t03b/run_policy_tests.py` -- expected: write reports.
- `python -m json.tool _bmad-output/test-artifacts/t03b/policy-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t03b/` -- expected: no matches.
