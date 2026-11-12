# Incident Response Runbook

**Owner:** DevOps + Security  
**Scope:** Outages, integrity incidents, and security events affecting the Corporate Agentic Knowledge Platform in the minimal production target (single-node PostgreSQL, daily backups, basic hoster monitoring).

## 1. Severity Levels

| Level | Definition | Examples | Response Time Target |
|---|---|---|---|
| SEV-1 | Complete loss of service or data integrity; no workaround. | PostgreSQL unreachable, GitLab unreachable, active unauthorized admin bypass. | 15 minutes |
| SEV-2 | Major feature degraded; workaround exists but is painful. | Search unavailable, editor read-only, backups failing. | 1 hour |
| SEV-3 | Minor degradation or non-critical failure. | Elevated error rate on a single endpoint, monitoring gap. | 4 hours (business hours) |
| SEV-4 | Informational; no user impact. | Log anomaly, dependency advisory. | Next business day |

> **Scope note:** These are operational response targets, not production SLOs. HA guarantees are deferred per owner decision [G1-D6](../architecture.md).

## 2. Triage Steps

1. **Acknowledge the page/alert** in the on-call channel and create an incident thread.
2. **Classify severity** using the table above.
3. **Identify affected scope:**
   - Open WebUI frontend
   - Git Orchestrator (GO)
   - Identity/AuthZ adapter
   - PostgreSQL (`kb_ops`, `kb_authz`, `kb_index`)
   - GitLab
   - Object store (MinIO / hoster S3)
4. **Check recent changes:**
   - Last deployment / MR merged
   - Last backup completion time (see [backup-and-retention.md](backup-and-retention.md))
   - Hoster status page and maintenance window
5. **Preserve evidence:**
   - Capture error messages and request IDs
   - Note exact UTC timestamps
   - Do not delete logs

## 3. Escalation Path

| Step | Contact | When |
|---|---|---|
| 1. On-call engineer | Primary on-call rotation | All incidents |
| 2. Backend lead | If service degradation persists > 30 min or involves GO / database | SEV-2 and above |
| 3. Security lead | If suspected breach, privileged bypass, or unauthorized data access | SEV-1 / SEV-2 |
| 4. Product owner / business owner | If user-facing outage > 1 hour or data-loss risk | SEV-1 |
| 5. Hoster support | If underlying VM, network, or storage issue is suspected | Any severity |

## 4. Rollback Option

If the incident correlates with a recent deployment or configuration change:

1. Follow [rollback-and-recovery.md](rollback-and-recovery.md) to revert Git state.
2. If the database is corrupted, restore from the latest daily backup per [backup-and-retention.md](backup-and-retention.md).
3. Validate the rollback before declaring the incident resolved.

## 5. Communication Template

Use the following template in the incident channel and, for SEV-1, to stakeholders:

```
INCIDENT: <SEV-1/SEV-2/SEV-3> — <short description>
Started: <UTC timestamp>
Impact: <affected users / features>
Actions: <what is being done>
ETA next update: <UTC timestamp>
Owner: <on-call engineer name>
```

Update every 30 minutes for SEV-1, every hour for SEV-2, or when material new information is available.

## 6. Post-Mortem Format

A post-mortem is required for every SEV-1 and every SEV-2 that required a rollback or recovery.

1. **Summary** — what happened and impact.
2. **Timeline** — detection, response, mitigation, recovery (UTC).
3. **Root cause** — technical and, if applicable, process cause.
4. **Lessons learned** — what went well and what did not.
5. **Action items** — owner and due date for each follow-up.
6. **Runbook updates** — which runbook(s) were updated as a result.

Store post-mortems in the incident-tracking tool or wiki; link them from the incident thread. Do not store sensitive details (tokens, private endpoints) in the post-mortem.

## 7. Cross-References

- [rollback-and-recovery.md](rollback-and-recovery.md)
- [backup-and-retention.md](backup-and-retention.md)
- [privileged-bypass-governance.md](privileged-bypass-governance.md)
