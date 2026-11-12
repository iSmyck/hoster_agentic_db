---
title: 'ACT-011 — Minimal production runbooks and operational checklists'
type: 'chore'
created: '2026-11-12'
status: 'done'
baseline_revision: '0790f6caad67f2f6f33b41ce75a7bde3411cec49'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Owner approved a minimal production target for launch (single-node PostgreSQL, daily backups, basic monitoring, repo runbooks). ACT-011 needs concrete runbooks and checklists before it can be marked done. ACT-008 (backup encryption, retention, and runbook decisions) can be closed as part of this work.

**Approach:** Create Markdown runbooks and operational checklists in `specs/corporate-kb/runbooks/` covering incident response, rollback/recovery, privileged bypass governance, security review, monitoring/alerting, and backup/retention. Record owner-backed decisions for backup encryption and retention. Update sprint status.

## Boundaries & Constraints

**Always:**
- Keep runbooks in the repo as Markdown so they version with the code.
- Align with the minimal production target: single-node PostgreSQL, daily backups, basic hoster monitoring.
- Reference existing decisions (G1-D6, D3-DEC1–4, owner ACT-011 decision).
- Do not invent new architectural components; only document operational procedures.
- Update sprint status and close ACT-008/ACT-011 after verification.

**Never:**
- Add new code, tables, or infrastructure resources.
- Commit secrets or real endpoints.
- Claim production SLOs or HA guarantees beyond the agreed minimal target.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Incident response | Service outage | Runbook provides escalation path, rollback option, communication template | Reference backup/recovery runbook |
| Privileged bypass | Emergency merge/approval override | Governance doc defines approver role, audit trail, time limits | Reference incident response |
| Security review | New release candidate | Checklist covers dependency scan, secret scan, ACL review, logs review | Block release if check fails |
| Backup failure | Daily backup missing | Runbook provides retry, escalation, and recovery-from-previous-backup steps | Reference retention policy |

## Code Map

- `specs/corporate-kb/runbooks/` -- destination for all runbooks (directory may need creation).
- `specs/corporate-kb/adr/` -- reference architecture decisions that constrain operations.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- status updates.
- `specs/corporate-kb/evidence/phase-e/` -- evidence destination (reviewable proof of ACT-011 closure).

## Tasks & Acceptance

**Execution:**
- `specs/corporate-kb/runbooks/README.md` -- index of runbooks and how to keep them current. RATIONALE: discoverability.
- `specs/corporate-kb/runbooks/incident-response.md` -- outage triage, escalation, rollback, communication template, post-mortem format. RATIONALE: operational readiness.
- `specs/corporate-kb/runbooks/rollback-and-recovery.md` -- rollback Git state, restore PostgreSQL from backup, restore object-store from mirror, validation steps. RATIONALE: recovery procedures.
- `specs/corporate-kb/runbooks/privileged-bypass-governance.md` -- who can bypass approval, under what conditions, audit trail requirements, time limits, post-incident review. RATIONALE: security governance.
- `specs/corporate-kb/runbooks/security-review-checklist.md` -- per-release checks: dependency vulnerabilities, secret scan, ACL review, audit-log review, XSS/input-sanitization checks. RATIONALE: repeatable security gate.
- `specs/corporate-kb/runbooks/monitoring-alerting-checklist.md` -- metrics to watch, alert thresholds, on-call runbook references, log locations. RATIONALE: observability.
- `specs/corporate-kb/runbooks/backup-and-retention.md` -- backup schedule, retention policy, encryption approach (hoster-provided at-rest), restore drill cadence. RATIONALE: closes ACT-008.
- `specs/corporate-kb/evidence/phase-e/act011-closure-evidence.md` -- sanitized evidence summary. RATIONALE: reviewable proof.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- set ACT-008 and ACT-011 to done, update overall_percent to 80. RATIONALE: reflect closure.

**Acceptance Criteria:**
- Given the runbooks directory, when reviewed, then it contains all listed runbooks with clear owner/responsible party and step-by-step procedures.
- Given the backup runbook, when read, then it defines retention periods, encryption method, and restore drill cadence without ambiguity.
- Given the sprint status file, when updated, then ACT-008 and ACT-011 are `done` and overall_percent is 80.
- Given the evidence report, when reviewed, then it lists runbooks created and references the owner decision that authorized the minimal production target.

## Spec Change Log

## Review Triage Log

### 2026-11-12 — Review pass (self-review)
- verdicts: 2 findings — high 0, medium 0, low 0, false 0, maybe-false 2
- findings:
  - `[maybe-false]` `[defer]` Runbooks contain hoster-specific placeholders for commands/endpoints because hoster inputs (ACT-009) are not yet available. The procedures and decision boundaries are documented; concrete commands will be filled in when hoster inputs arrive.
  - `[maybe-false]` `[defer]` Minimal single-node target limits runbook scope; HA/DR procedures are explicitly deferred and will be needed if the production target is upgraded later.

## Design Notes

These runbooks are intentionally minimal. They assume the single-node PostgreSQL + daily backup target approved by the owner. HA/DR runbooks (Patroni, cross-DC replication) are explicitly out of scope and should be added only when the owner upgrades the production target.

## Verification

**Commands:**
- `ls specs/corporate-kb/runbooks/` -- expected: all listed Markdown files present.
- `python -c "import yaml; yaml.safe_load(open('_bmad-output/implementation-artifacts/sprint-status.yaml'))"` -- expected: no parse errors.
- `grep -E 'ACT-008|ACT-011' _bmad-output/implementation-artifacts/sprint-status.yaml` -- expected: both marked done.

**Manual checks (if no CLI):**
- Inspect `specs/corporate-kb/runbooks/` for completeness.
- Inspect `specs/corporate-kb/evidence/phase-e/act011-closure-evidence.md` for closure summary.
- Inspect `sprint-status.yaml` action_items for ACT-008/ACT-011 status.

## Auto Run Result

- Summary: ACT-011 closed by creating minimal production runbooks and operational checklists. ACT-008 closed simultaneously by recording backup encryption, retention, and restore-drill decisions in `backup-and-retention.md`. Sprint status updated; overall_percent raised to 80.
- Files changed:
  - `specs/corporate-kb/runbooks/README.md` — index and maintenance rules.
  - `specs/corporate-kb/runbooks/incident-response.md` — outage triage and escalation.
  - `specs/corporate-kb/runbooks/rollback-and-recovery.md` — Git/PostgreSQL/object-store recovery.
  - `specs/corporate-kb/runbooks/privileged-bypass-governance.md` — emergency override governance.
  - `specs/corporate-kb/runbooks/security-review-checklist.md` — per-release security gate.
  - `specs/corporate-kb/runbooks/monitoring-alerting-checklist.md` — metrics/thresholds/on-call.
  - `specs/corporate-kb/runbooks/backup-and-retention.md` — schedule/retention/encryption; closes ACT-008.
  - `specs/corporate-kb/evidence/phase-e/act011-closure-evidence.md` — closure evidence.
  - `_bmad-output/implementation-artifacts/sprint-status.yaml` — ACT-008/ACT-011 done, overall_percent 80.
- Review findings: 2 maybe-false deferred (hoster placeholders, HA/DR scope).
- Follow-up review recommended: false.
- Verification performed:
  - `ls specs/corporate-kb/runbooks/` → all files present.
  - YAML parse check → OK.
  - ACT-008/ACT-011 status check → both done; overall_percent 80.
- Residual risks:
  - Runbooks are minimal; HA/DR and customer-managed encryption remain deferred.
  - Hoster-specific operational commands are placeholders pending ACT-009 resolution.
