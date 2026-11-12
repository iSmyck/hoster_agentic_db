# ACT-011 Closure Evidence

**Date:** 2026-11-12  
**Story:** ACT-011 — Minimal production runbooks and operational checklists  
**Related:** ACT-008 — Backup encryption, retention and runbook decisions  
**Owner decision:** Owner approved the minimal production target: single-node PostgreSQL with daily backups, basic hoster monitoring, security checklist review, and Markdown runbooks in repo. HA/DR and external pen-tests deferred post-launch.

## What Was Delivered

All runbooks were created in `specs/corporate-kb/runbooks/` as Markdown files versioned with the repository:

| Runbook | Purpose |
|---|---|
| [runbooks/README.md](../../runbooks/README.md) | Index of runbooks and maintenance rules |
| [runbooks/incident-response.md](../../runbooks/incident-response.md) | Outage triage, escalation, rollback, communication template, post-mortem format |
| [runbooks/rollback-and-recovery.md](../../runbooks/rollback-and-recovery.md) | Git rollback, PostgreSQL restore, object-store restore, validation |
| [runbooks/privileged-bypass-governance.md](../../runbooks/privileged-bypass-governance.md) | Emergency override governance, audit trail, time limits, post-incident review |
| [runbooks/security-review-checklist.md](../../runbooks/security-review-checklist.md) | Per-release security gate |
| [runbooks/monitoring-alerting-checklist.md](../../runbooks/monitoring-alerting-checklist.md) | Metrics, thresholds, log locations, on-call references |
| [runbooks/backup-and-retention.md](../../runbooks/backup-and-retention.md) | Schedule, retention, encryption, restore drills; closes ACT-008 |

## Owner-Backed Decisions Recorded

- **Backup encryption:** hoster-provided at-rest encryption; customer-managed keys deferred.
- **Retention:** 30 days daily backups, 12 weeks weekly archives, 90 days logs.
- **Restore drill cadence:** monthly.
- **Scope:** single-node PostgreSQL, daily backups, basic hoster monitoring; HA/DR deferred per [G1-D6](../../architecture.md) and [D3-DEC1](../../adr/ADR-019-t19-t20-deferred-business-gate.md).

## Sprint Status

- ACT-008 status changed to `done`.
- ACT-011 status changed to `done`.
- `overall_percent` updated to `80`.

## Verification Performed

1. `ls specs/corporate-kb/runbooks/` — all listed Markdown files present.
2. `python -c "import yaml; yaml.safe_load(open('_bmad-output/implementation-artifacts/sprint-status.yaml'))"` — no parse errors.
3. `grep -E 'ACT-008|ACT-011' _bmad-output/implementation-artifacts/sprint-status.yaml` — both marked `done`.

## Known Limitations / Risks

- Runbooks are minimal and assume the owner-approved single-node target.
- HA/DR, customer-managed encryption keys, and external penetration tests remain in the backlog.
- Actual hoster-specific commands and endpoints are placeholders until hoster inputs are received; this is acceptable because the runbooks describe procedures and decision boundaries, not concrete infrastructure resources.
