---
title: 'T03a Stable identity core and nested group snapshots'
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

**Problem:** Нет executable evidence для stable identity core: issuer-scoped `sub`/entryUUID/objectGUID, JIT provisioning, nested group snapshots, rename survival и empty-group handling.

**Approach:** Создать T03a harness, который валидирует identity contracts на synthetic fixtures: stable ID schemas, group snapshots с nested membership, epoch ordering, rename survival и empty-group results.

## Boundaries & Constraints

**Always:**
- Identity key — issuer-scoped `sub`, AD `objectGUID`, OpenLDAP `entryUUID`; email/login не identity key.
- Группы резолвятся полностью; snapshot содержит epoch и explicit empty-group results.
- Хранить evidence в `_bmad-output/test-artifacts/t03a/` и `specs/corporate-kb/evidence/t03a/`.

**Never:**
- Не использовать real LDAP/IdP credentials или production identities.
- Не реализовывать full AuthZ enforcement (E02.3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Stable ID schema | Valid/invalid identity payloads | Valid PASS; missing sub/entryUUID/objectGUID FAIL | Schema error → FAIL |
| Nested groups | Group A contains B, B contains user | Snapshot includes transitive membership PASS | Cycle → FAIL |
| Rename survival | Same sub, changed email | Identity stable, email updated PASS | New identity created → FAIL |
| Empty group | Group with no members | Snapshot records empty group PASS | Missing group → FAIL |
| Epoch ordering | Older sync after newer | Older rejected, newer preserved PASS | Stale overwrite → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t02/run_document_tests.py` — reference harness pattern.
- `specs/corporate-kb/contracts/authz-context.schema.json` — identity/group snapshot schema.
- `specs/corporate-kb/contracts/approval-policy.schema.json` / `access-policy.schema.json` — policy schemas.
- `_bmad-output/implementation-artifacts/epic-2-context.md` — identity/AuthZ decisions.

## Tasks & Acceptance

**Execution:**
- [ ] `_bmad-output/test-artifacts/t03a/run_identity_tests.py` — main harness.
- [ ] `_bmad-output/test-artifacts/t03a/fixtures/` — synthetic identity and group YAML fixtures.
- [ ] `_bmad-output/test-artifacts/t03a/validators/` — identity schema, group snapshot, epoch, rename validators.
- [ ] `_bmad-output/test-artifacts/t03a/identity-results.json` + `summary.md`.
- [ ] `specs/corporate-kb/evidence/t03a/` — sanitized evidence.
- [ ] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `2-2-t03a-...` → `done`.

**Acceptance Criteria:**
- Given valid/invalid identity payloads, when schema validator runs, then valid identities PASS and missing key fields FAIL.
- Given nested group fixtures, when group snapshot validator runs, then transitive membership is complete and ordered, and cycles are rejected.
- Given rename fixture with same sub and changed email, when validator runs, then identity remains stable.
- Given empty group fixture, when snapshot validator runs, then empty result is explicit.
- Given older sync after newer, when epoch validator runs, then stale overwrite is rejected.
- Given completed run, evidence contains no secrets/real endpoints/absolute paths.

## Implementation Notes


## Spec Change Log


## Review Triage Log


## Design Notes

T03a harness reuse T01/T02 reporters and sanitize patterns. Validators operate on synthetic YAML identity/group fixtures and JSON schemas; live LDAP/IdP/GO checks remain BLOCKED.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t03a/run_identity_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t03a/run_identity_tests.py` -- expected: write reports.
- `python -m json.tool _bmad-output/test-artifacts/t03a/identity-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t03a/` -- expected: no matches.
