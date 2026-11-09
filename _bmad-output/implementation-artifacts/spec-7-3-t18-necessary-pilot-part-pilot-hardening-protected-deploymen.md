---
title: 'T18 Necessary pilot part: pilot hardening, protected deployment and operational acceptance'
type: 'feature'
created: '2026-11-09'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '152b00ff6aaa7b95c7b958d822bf54e8a54d1650'
context:
  - specs/corporate-kb/operations.md
  - specs/corporate-kb/database.md
  - specs/corporate-kb/components/git-orchestrator.md
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-7-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no executable evidence that the internal pilot deployment is hardened, that runbooks are rehearsed, that security/regression checks deny bypass, and that two independent non-engineering business users can complete the canonical review/decision/restore scenario.

**Approach:** Create a T18 harness that exercises synthetic YAML fixtures for pilot environment isolation, credential/egress separation, runbook rehearsal completeness, backup/restore drill semantics, security/regression checks, privileged-bypass incident governance, and business-user acceptance on exact proposal fixtures. Live pilot environment and corpus remain BLOCKED.

## Boundaries & Constraints

**Always:**
- Pilot environment is isolated: repositories=Spaces, config/adapters, PostgreSQL/index/object storage, secrets, backups and egress separated; runtime workers have migrations disabled and non-DDL roles; only owning external migrators perform rehearsed schema upgrades before traffic.
- Proposal/merge, connector, CI/index and retrieval credentials remain separated; default egress is closed except approved routes; no client code branch introduced; no production resource/corpus created without separate authorization.
- Startup, cutover, merge recovery/quarantine, export, backup, restore, upgrade and rollback runbooks are rehearsed with exact versions/refs, commands, sanitized outputs, failure handling, residual BLOCKED items and independently reviewed results.
- Backup/restore drill validates decisions/assets/authorization closure, freshly rebuilds `kb_authz`, starts `kb_ops` under global merge freeze with conservative target barriers, and points `kb_index` to a new full validated snapshot before activation.
- Security/regression checks deny direct push/merge/auto-merge for every non-privileged business/engineering/bot/connector/CI/source-managed identity; each owning component writes only its schema; runtime DDL and cross-client resource access fail; secret/log redaction canaries disclose nothing.
- Privileged GitLab Owner bypass is treated as an out-of-band integrity incident: detection, immediate quarantine and G0-D3 emergency runbook.
- Two independent non-engineering business users complete the full pending queue → read/edit → diff/rationale/evidence → accept/reject/cancel → history/restore scenario without Git/CLI.

**Never:**
- Do not create a production knowledge-base corpus or pilot environment without separate owner authorization.
- Do not claim full T18/G3 or second-client acceptance (Epic 8 scope).
- Do not treat privileged Owner bypass as an approved managed path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Pilot isolation | Spaces, config, PostgreSQL/index/objects, secrets, backups, egress | All separated; runtime non-DDL; migrators only for rehearsed upgrades | Shared resource / DDL runtime → FAIL |
| Credential/egress separation | Proposal/merge, connector, CI/index, retrieval credentials; egress default deny | Credentials separated; default egress closed; approved routes only | Leaked merge credential / open default egress → FAIL |
| Runbook rehearsal | Startup/cutover/recovery/export/backup/restore/upgrade/rollback checklists | Exact versions/refs/commands, sanitized outputs, failure handling, BLOCKED items | Missing step / undocumented BLOCKED → FAIL |
| Backup/restore drill | Decisions/assets/authorization closure | kb_authz rebuilt; kb_ops under global freeze; kb_index to validated snapshot before activation | Activation before validation / missing closure → FAIL |
| Security/regression | Direct push/merge/auto-merge, schema writes, DDL, cross-client access, secret canaries | Denied for non-privileged identities; component schema isolation; no disclosure | Bypass allowed / disclosure → FAIL |
| Privileged bypass governance | Owner bypass attempt | Detected, quarantined, G0-D3 emergency runbook | Treated as managed path → FAIL |
| Business user acceptance | Two non-engineering users, exact proposal fixtures | Complete review/decision/restore scenario; canonical decisions; history cursor; revert-MR | Git/CLI used / self-approval → FAIL |

</frozen-after-approval>

## Open Questions

_Нет открытых вопросов._

## Code Map

- `_bmad-output/test-artifacts/t18/run_t18_tests.py` — main harness.
- `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml` — synthetic pilot hardening/deployment fixtures.
- `specs/corporate-kb/operations.md` — runbook design (design_not_executed).
- `specs/corporate-kb/database.md` — schema ownership and rebuild semantics.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t18/run_t18_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t18/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t18/pilot-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t18/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `7-3-t18-...` → `done`.

**Acceptance Criteria:**
- [x] Given pilot isolation fixtures, repositories=Spaces, config/adapters, PostgreSQL/index/object storage, secrets, backups and egress are separated; runtime workers have migrations disabled and non-DDL roles.
- [x] Given credential/egress fixtures, proposal/merge, connector, CI/index and retrieval credentials are separated; default egress is closed except approved routes; no client code branch is introduced.
- [x] Given runbook fixtures, startup/cutover/recovery/export/backup/restore/upgrade/rollback runbooks are rehearsed with exact versions/refs, commands, sanitized outputs, failure handling and residual BLOCKED items.
- [x] Given backup/restore drill fixtures, decisions/assets/authorization closure is validated, `kb_authz` is freshly rebuilt, `kb_ops` starts under global merge freeze with conservative barriers and `kb_index` points to a new validated snapshot before activation.
- [x] Given security/regression fixtures, direct push/merge/auto-merge is denied for non-privileged identities, each component writes only its schema, runtime DDL and cross-client access fail, and secret/log redaction canaries disclose nothing.
- [x] Given privileged-bypass fixtures, Owner bypass is detected, quarantined and handled via the G0-D3 emergency runbook, not as an approved path.
- [x] Given business-user acceptance fixtures, two independent non-engineering users complete the full pending queue → read/edit → diff/rationale/evidence → accept/reject/cancel → history/restore scenario without Git/CLI.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths and live pilot environment/corpus is recorded as BLOCKED.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns; validators operate on synthetic YAML fixtures. Live protected deployment, pilot environment and real corpus remain BLOCKED; full T18/G3 and second-client acceptance belong to Epic 8.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the internal pilot hardening slice: isolation, credential/egress separation, runbook rehearsal, backup/restore drill semantics, security/regression checks, privileged-bypass incident governance and business-user acceptance on synthetic fixtures. It does not create a production pilot environment or claim full G3 readiness.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t18/run_t18_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t18/run_t18_tests.py` -- expected: writes `pilot-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t18/pilot-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t18/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
