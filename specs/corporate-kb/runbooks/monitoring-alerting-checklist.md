# Monitoring and Alerting Checklist

**Owner:** DevOps  
**Scope:** Metrics, thresholds, log locations, and on-call references for the minimal production target (single-node PostgreSQL, daily backups, basic hoster monitoring).

> **Scope note:** Advanced SLOs, distributed tracing, and custom dashboards are deferred per owner decision [G1-D6](../architecture.md). Use hoster-provided monitoring where available.

## 1. Metrics to Watch

| Metric | Source | Normal Range | Investigate If |
|---|---|---|---|
| HTTP 5xx rate | Open WebUI / GO access logs | < 0.1% | > 1% for 5 min |
| HTTP 4xx rate | Open WebUI / GO access logs | < 1% | > 5% for 5 min |
| P95 response time | Open WebUI / GO access logs | < 2000 ms | > 5000 ms for 5 min |
| GO queue depth | GO logs / hoster metrics | near 0 | > 100 for 5 min |
| PostgreSQL connections | PostgreSQL `pg_stat_activity` | < 80% max | > 90% |
| PostgreSQL disk usage | Hoster monitoring | < 70% | > 85% |
| PostgreSQL replication lag | N/A for single-node | N/A | N/A |
| Object-store availability | MinIO / S3 health endpoint | 100% | < 99% over 5 min |
| Daily backup completion | Backup job logs | success within window | missing or failed |
| Keycloak / IdP latency | Keycloak logs | < 500 ms | > 2000 ms |

## 2. Alert Thresholds

Configure hoster alerts or cron checks for:

1. **SEV-1:** Service completely unavailable (health endpoint returns non-200 for 2 min).
2. **SEV-1:** Daily backup failure.
3. **SEV-2:** 5xx rate > 1% for 5 min.
4. **SEV-2:** P95 response time > 5000 ms for 5 min.
5. **SEV-2:** PostgreSQL disk usage > 85%.
6. **SEV-3:** 4xx rate > 5% for 5 min.
7. **SEV-3:** Keycloak latency > 2000 ms for 5 min.

## 3. Log Locations

| Component | Log Location | Retention |
|---|---|---|
| Open WebUI | `/var/log/open-webui/` or container stdout | 30 days |
| Git Orchestrator (GO) | `/var/log/kb/go/` or container stdout | 90 days |
| Identity adapter | `/var/log/kb/identity/` or container stdout | 90 days |
| PostgreSQL | hoster-managed PostgreSQL logs | per hoster policy |
| GitLab | GitLab application logs | per GitLab policy |
| Object store | MinIO / S3 access logs | 30 days |
| Backups | backup job logs + object-store mirror metadata | per [backup-and-retention.md](backup-and-retention.md) |

## 4. On-Call Runbook References

Keep this checklist printed or bookmarked in the on-call rotation:

- [incident-response.md](incident-response.md) — triage, escalation, communication.
- [rollback-and-recovery.md](rollback-and-recovery.md) — revert Git state, restore PostgreSQL / object store.
- [backup-and-retention.md](backup-and-retention.md) — backup schedule, retention, restore drill.
- [privileged-bypass-governance.md](privileged-bypass-governance.md) — emergency override rules.

## 5. Daily Health Checks

The on-call engineer should verify once per day:

- [ ] Backup job completed successfully in the last 24 hours.
- [ ] No unacknowledged SEV-1 or SEV-2 alerts older than 30 minutes.
- [ ] PostgreSQL disk usage < 85%.
- [ ] Object-store health endpoint returns 200.
- [ ] GO can read from GitLab and PostgreSQL (run a lightweight probe if available).

## 6. Weekly Review

Each week, review:

1. Alert frequency and false-positive rate.
2. Slowest GO endpoints and highest-error endpoints.
3. PostgreSQL disk growth trend.
4. Any privileged bypass or GitLab Owner actions outside GO.
5. Backup restore-test status.

## 7. Cross-References

- [incident-response.md](incident-response.md)
- [backup-and-retention.md](backup-and-retention.md)
- [security-review-checklist.md](security-review-checklist.md)
