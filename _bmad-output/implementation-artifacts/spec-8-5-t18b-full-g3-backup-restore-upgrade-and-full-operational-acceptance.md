---
title: 'T18b Full G3 backup/restore/upgrade and full operational acceptance'
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
  - specs/corporate-kb/contracts/docops-correction-task.schema.json
  - specs/corporate-kb/baseline.md
  - _bmad-output/implementation-artifacts/epic-8-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Full T18/G3 acceptance requires clean disaster-recovery and upgrade rehearsals for a second client, observability and incident handling, and independent owner review. The required second-client environment and real connector evidence are not available.

**Approach:** Create a T18b harness that exercises synthetic YAML fixtures for clean restore validation, correction-task backup reconciliation, unknown-merge quarantine, metrics/alerts/runbooks, upgrade/rollback rehearsal, cross-client negative controls, and explicit BLOCKED handling for unavailable G3 components. The harness does not claim full T18/G3 acceptance.

## Boundaries & Constraints

**Always:**
- Clean restore validates refs, MR/note/audit metadata, decisions/assets/authorization closure and hashes; freshly rebuilds `kb_authz`; recovers Git-derived `kb_ops` projections under global merge freeze with conservative barriers; and points `kb_index` to a new full validated snapshot before activation.
- A separate durable non-Git-derived correction backup preserves correction-task current projections, append-only events, restricted evidence and idempotency records; restore validates hashes/event sequences/perimeter and performs linked-MR reconciliation without fabricating, deleting, resolving or cancelling tasks.
- Unknown merge outcomes remain quarantined; missing assets, incomplete closure or missing/corrupt correction backup block READY.
- Cross-client negative controls fail closed; owner-approved RPO/RTO, retention, backup cadence and recovery evidence are recorded.
- Metrics/alerts/runbooks cover startup, cutover/activation, merge latency, locks/fencing/recovery age/quarantine, decision mismatch, CI/webhook/HEAD drift, revocation, source cursors, export/backup closure, source sync, TTFT/full response and restore/upgrade; telemetry excludes secrets, raw documents/chunks/queries/rationale/evidence, provider payloads, signed URLs and PII snippets.
- Upgrade/rollback rehearsals evaluate dependency pins, SBOM/license diff, branding/notices, external migration order, cold offline startup and every registered auth/grant/tool/editor/retrieval/connector seam; failures block the upgrade.
- Full T18/G3 acceptance demonstrates the E08.4 second-client deployment, E08.2 selected-connector evidence, clean backup/restore and upgrade results through independent review, with one external source update flowing through human decision and GO merge without auto-merge.

**Never:**
- Do not claim full T18/G3 acceptance without E08.4 second-client deployment, E08.2 real connector evidence, completed runbooks and independent owner review.
- Do not fabricate recovery, upgrade or G3 acceptance evidence.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean restore | Refs, MR/note/audit metadata, decisions, assets, closure, hashes | Validated; kb_authz rebuilt; kb_ops under freeze; kb_index snapshot before activation | Activation before validation / missing closure → FAIL |
| Correction backup | Non-Git-derived current projection, events, evidence, idempotency | Hash/event-sequence/perimeter checks; linked-MR reconciliation; no canonical write mutation | Fabrication/deletion/resolution of tasks → FAIL |
| Unknown merge quarantine | Unresolved merge outcomes | Remain quarantined; empty DB/terminal/superseded/generic TTL does not clear | Auto-clear / optimistic READY → FAIL |
| Metrics/alerts/runbooks | Startup/cutover/recovery/export/backup/restore/upgrade/rollback | Coverage exists; telemetry redacted; thresholds owner-approved | Missing runbook / secret in telemetry → FAIL |
| Upgrade/rollback rehearsal | Dependency pins, SBOM/license, branding, migration order, seams | Rehearsed; failures block upgrade; rollback path preserved | Upgrade waived as debt / missing rollback → FAIL |
| Cross-client negative controls | Second client attempts first-client access | Fail closed | Cross-client read/write succeeds → FAIL |
| Full G3 acceptance | E08.4 + E08.2 + clean restore/upgrade + independent review | One external source update flows through human decision + GO merge | Auto-merge / missing independent review → FAIL |

</frozen-after-approval>

## Open Questions

- E08.4 second-client environment, E08.2 real connector evidence and independent G3 reviewer unavailable.

## Code Map

- `_bmad-output/test-artifacts/t18b/run_t18b_tests.py` — main harness.
- `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml` — synthetic G3 backup/restore/upgrade fixtures.
- `specs/corporate-kb/operations.md` — runbook design.
- `specs/corporate-kb/database.md` — schema ownership and rebuild semantics.
- `specs/corporate-kb/contracts/docops-correction-task.schema.json` — correction-task contract.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/test-artifacts/t18b/run_t18b_tests.py` — main harness.
- [x] `_bmad-output/test-artifacts/t18b/fixtures/scenarios.yaml` — synthetic YAML fixtures.
- [x] `_bmad-output/test-artifacts/t18b/g3-results.json` + `summary.md`.
- [x] `specs/corporate-kb/evidence/t18b/` — sanitized evidence.
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` — `8-5-t18b-...` → `done`.

**Acceptance Criteria:**
- [x] Given clean-restore fixtures, refs/MR/note/audit metadata/decisions/assets/closure/hashes are validated, `kb_authz` is freshly rebuilt, `kb_ops` starts under global merge freeze with conservative barriers and `kb_index` points to a new validated snapshot before activation.
- [x] Given correction-backup fixtures, restore validates hashes/event sequences/perimeter and performs linked-MR reconciliation without fabricating, deleting, resolving or cancelling tasks.
- [x] Given unknown-merge fixtures, unresolved outcomes remain quarantined and missing assets/closure/correction backup blocks READY.
- [x] Given metrics/alerts/runbook fixtures, required coverage exists, telemetry excludes secrets/raw content/provider payloads/signed URLs/PII snippets and owner-approved RPO/RTO/retention/cadence are recorded.
- [x] Given upgrade/rollback fixtures, dependency pins, SBOM/license diff, branding/notices, external migration order, cold offline startup and registered seams are rehearsed and failures block the upgrade.
- [x] Given cross-client fixtures, second-client negative controls against first-client resources fail closed.
- [x] Given full G3 acceptance fixtures, the scenario requires E08.4 second-client deployment, E08.2 real connector evidence, clean restore/upgrade and independent review with one external source update flowing through human decision and GO merge without auto-merge.
- [x] Given completed run, evidence contains no secrets/real endpoints/absolute paths and unavailable G3 components are recorded as BLOCKED.

## Implementation Notes

Harness reuses T01–T10 reporter/sanitize patterns via `harness_common.py`; validators operate on synthetic YAML fixtures. Full T18/G3 acceptance remains BLOCKED until E08.4 second-client deployment, E08.2 real connector evidence and independent owner review exist.

## Spec Change Log


## Review Triage Log


## Design Notes

The harness models the operational acceptance criteria for full T18/G3: clean restore, correction-task backup reconciliation, quarantine discipline, observability/runbooks, upgrade/rollback rehearsal and cross-client negative controls. It records all unavailable real components as BLOCKED and does not fabricate G3 acceptance.

## Verification

**Commands:**
- `uv run python _bmad-output/test-artifacts/t18b/run_t18b_tests.py --dry-run` -- expected: exit 0.
- `uv run python _bmad-output/test-artifacts/t18b/run_t18b_tests.py` -- expected: writes `g3-results.json` and `summary.md`.
- `python -m json.tool _bmad-output/test-artifacts/t18b/g3-results.json >/dev/null` -- expected: valid JSON.
- `grep -R -E '(token|password|secret|localhost:8080|@)' specs/corporate-kb/evidence/t18b/` -- expected: no matches.
- `uv run pytest -q` -- expected: all existing tests pass.
