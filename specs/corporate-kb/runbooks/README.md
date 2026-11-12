# Production Runbooks

This directory contains the minimal operational runbooks for the Corporate Agentic Knowledge Platform. They are intentionally scoped to the **owner-approved minimal production target**:

- Single-node PostgreSQL
- Daily backups
- Basic hoster monitoring
- Markdown runbooks versioned in this repository

High-availability, cross-site DR, Patroni, and external penetration-test runbooks are explicitly out of scope for launch and are recorded in the backlog per decisions [G1-D6](../architecture.md), [D3-DEC1](../adr/ADR-019-t19-t20-deferred-business-gate.md), and the owner ACT-011 decision.

## Runbook Index

| Runbook | Purpose | Primary Owner |
|---|---|---|
| [incident-response.md](incident-response.md) | Triage, escalate, roll back, and communicate during an outage or integrity incident. | DevOps + Security |
| [rollback-and-recovery.md](rollback-and-recovery.md) | Roll back Git state, restore PostgreSQL from backup, and restore object-store data from a mirror. | Backend + DevOps |
| [privileged-bypass-governance.md](privileged-bypass-governance.md) | Emergency override of approval/merge rules: who may act, under what conditions, and how it is audited. | Security + Owner |
| [security-review-checklist.md](security-review-checklist.md) | Repeatable per-release security gate before a release candidate is accepted. | Security + QA |
| [monitoring-alerting-checklist.md](monitoring-alerting-checklist.md) | Metrics, thresholds, log locations, and on-call references for the minimal target. | DevOps |
| [backup-and-retention.md](backup-and-retention.md) | Backup schedule, retention policy, encryption approach, and restore-drill cadence. Closes ACT-008. | DevOps + Backend |

## Keeping Runbooks Current

1. **After every incident**, update the runbook that was invoked with lessons learned within two business days.
2. **After every release**, review the security and monitoring checklists for stale thresholds, new components, or changed log paths.
3. **After every restore drill**, update [backup-and-retention.md](backup-and-retention.md) with actual timings and any deviations.
4. **Owner approval is required** before expanding scope (HA, cross-DC DR, external pen-test). Backlog items D.3, D.4.2–D.4.4, and E.3 remain deferred.

## References

- [Architecture decisions](../adr/README.md)
- [Sprint status](../../../_bmad-output/implementation-artifacts/sprint-status.yaml)
- [ACT-011 closure evidence](../evidence/phase-e/act011-closure-evidence.md)
