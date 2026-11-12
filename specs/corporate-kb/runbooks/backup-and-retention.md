# Backup and Retention Runbook

**Owner:** DevOps + Backend  
**Scope:** Backup schedule, retention policy, encryption approach, and restore-drill cadence for the minimal production target. This runbook closes ACT-008.

## 1. Owner-Backed Decisions

The following decisions are recorded here per the owner ACT-008 / ACT-011 decision:

| Decision | Value | Rationale |
|---|---|---|
| Backup encryption | Hoster-provided at-rest encryption | Owner-approved minimal target; no customer-managed keys for launch |
| Retention — daily backups | 30 days | Balance between recovery window and storage cost |
| Retention — weekly archive | 12 weeks | Longer-term recovery for critical incidents |
| Retention — logs | 90 days | Operational and security audit need |
| Restore drill cadence | Monthly | Validate backup integrity without excessive operational load |
| Backup scope | PostgreSQL (`kb_ops`, `kb_authz`, `kb_index`), GitLab repositories, object-store buckets | Rebuildable projections excluded from primary backup; re-created from canonical Git + object store |

> **Scope note:** Customer-managed encryption keys, cross-site replication, and DR runbooks are deferred per decisions [G1-D6](../architecture.md) and [D3-DEC1](../adr/ADR-019-t19-t20-deferred-business-gate.md).

## 2. Backup Schedule

| Data Source | Frequency | Window (UTC) | Destination | Encryption |
|---|---|---|---|---|
| PostgreSQL `kb_ops` | Daily | 02:00–04:00 | Hoster backup + object-store mirror | Hoster at-rest |
| PostgreSQL `kb_authz` | Daily | 02:00–04:00 | Hoster backup + object-store mirror | Hoster at-rest |
| PostgreSQL `kb_index` | Daily | 02:00–04:00 | Hoster backup + object-store mirror | Hoster at-rest |
| GitLab repositories | Daily | 03:00–05:00 | Object-store mirror | Hoster at-rest |
| Object-store buckets (`kb-attachments`, `kb-backups`, `kb-exports`) | Daily | 04:00–06:00 | Cross-bucket mirror in same region | Hoster at-rest |
| Configuration / environment variables | On change | Manual | Encrypted secret store | Secret-store encryption |

## 3. Retention Policy

| Backup Type | Retention | Action After Expiry |
|---|---|---|
| Daily PostgreSQL backup | 30 days | Delete automatically |
| Weekly PostgreSQL archive | 12 weeks | Delete automatically |
| Daily GitLab repository mirror | 30 days | Delete automatically |
| Daily object-store bucket mirror | 30 days | Delete automatically |
| Weekly object-store archive | 12 weeks | Delete automatically |
| Audit logs | 90 days | Move to long-term archive if required by compliance |

## 4. Encryption Approach

- **At-rest:** provided by the hoster / object-store platform.
- **In-transit:** TLS 1.2+ for all backup transfers.
- **Keys:** hoster-managed; customer-managed keys are a deferred backlog item (D.4.2).
- **Secrets:** deployment secrets are stored in the secret mechanism, never in backups.

## 5. Backup Failure Response

1. **Detect:** Alert fires when daily backup job is missing or failed by 06:00 UTC.
2. **Investigate:**
   - Check backup job logs for disk-space, network, or credential errors.
   - Verify object-store mirror health.
   - Check hoster status page for maintenance.
3. **Retry:** Manually re-run the failed backup job.
4. **Escalate:** If retry fails, open SEV-2 incident and notify Backend + DevOps.
5. **Recover:** If the previous backup is also unusable, restore from the weekly archive.

## 6. Restore Drill Cadence

Perform a restore drill **monthly** in a non-production environment:

1. Select a recent daily backup and a weekly archive at random.
2. Restore PostgreSQL to the drill instance.
3. Restore GitLab repository mirror and object-store mirror.
4. Run smoke tests:
   - Identity adapter resolves users.
   - GO reads a Space and latest decisions.
   - Retrieval returns results.
5. Record actual RTO and any deviations.
6. Update this runbook with findings.

## 7. Validation Checklist

- [ ] Daily backup jobs completed in the last 7 days.
- [ ] Backup logs show no errors.
- [ ] Object-store mirror contains files from the last backup window.
- [ ] Monthly restore drill completed and documented.
- [ ] Retention job deleted backups older than policy without error.

## 8. Cross-References

- [incident-response.md](incident-response.md)
- [rollback-and-recovery.md](rollback-and-recovery.md)
- [monitoring-alerting-checklist.md](monitoring-alerting-checklist.md)
- [Sprint status — ACT-008 closure](../../../_bmad-output/implementation-artifacts/sprint-status.yaml)
