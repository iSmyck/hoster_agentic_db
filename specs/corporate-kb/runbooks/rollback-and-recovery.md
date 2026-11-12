# Rollback and Recovery Runbook

**Owner:** Backend + DevOps  
**Scope:** Revert Git state, restore PostgreSQL from backup, and restore object-store data from a mirror for the minimal production target.

> **Scope note:** Cross-site DR and point-in-time recovery to the second are deferred per owner decisions [D3-DEC1](../adr/ADR-019-t19-t20-deferred-business-gate.md) and [G1-D6](../architecture.md). This runbook covers daily-backup-based recovery only.

## 1. Roll Back Git State

Use this when a bad merge, configuration change, or corrupted branch must be reverted.

### 1.1 Identify the Last Known Good State

```bash
git log --oneline -20 --all -- <space-repository>
git show-ref --heads --tags | grep kb-decisions
git reflog --all -- <space-repository>
```

Record the full SHA of the last known good `main` commit.

### 1.2 Revert via Managed Path (Preferred)

1. Open a correction task in GO for the affected Space.
2. Provide:
   - `space_id`
   - target `main` SHA to restore
   - rationale with incident reference
3. GO creates a recovery proposal and DecisionRecord.
4. Required approver(s) review and accept per the Space approval policy.
5. GO applies the revert and tags the decision.

### 1.3 Emergency Revert via Privileged GitLab Owner (Break-Glass)

1. Authorize per [privileged-bypass-governance.md](privileged-bypass-governance.md).
2. Affected targets are immediately marked `recovery_required` / quarantine.
3. Managed-write freeze is declared for the Space.
4. After manual reset, GO reconciliation is run to restore managed state.
5. A post-mortem is opened.

## 2. Restore PostgreSQL from Backup

### 2.1 Before You Start

- Confirm the incident is not a disk-space or network issue first.
- Identify the latest valid daily backup from the hoster backup console or object-store mirror.
- Notify the on-call channel.

### 2.2 Restore Steps

1. Stop application writes to the database (scale GO / identity pods to 0 or enable read-only mode).
2. Create a snapshot of the current corrupted volume if possible (forensic evidence).
3. Restore the backup to a new database instance or overwrite the existing one per hoster procedure.
4. Run integrity checks:
   ```bash
   psql -d kb_ops -c "SELECT COUNT(*) FROM proposal_records;"
   psql -d kb_authz -c "SELECT COUNT(*) FROM group_snapshots;"
   psql -d kb_index -c "SELECT COUNT(*) FROM active_index_pointer;"
   ```
5. Restart services and run smoke tests (see [local-stack evidence](../evidence/local-stack/README.md) for smoke-test shape).
6. Verify GitLab and object-store connectivity from GO.

### 2.3 Validation Checklist

- [ ] `kb_ops`, `kb_authz`, `kb_index` schemas are reachable.
- [ ] Latest proposal/decision records match the restored backup time.
- [ ] Identity adapter can resolve test users.
- [ ] Retrieval adapter returns results for a known query.
- [ ] Open WebUI `/kb` editor loads without errors.

## 3. Restore Object Store from Mirror

Use this when MinIO / hoster S3 buckets are corrupted or deleted.

1. Identify the latest mirror snapshot (daily, same schedule as PostgreSQL).
2. Stop ingestion and media uploads.
3. Restore the affected bucket(s) from mirror:
   - `kb-attachments`
   - `kb-backups`
   - `kb-exports`
4. Re-run integrity verification (D.4.1) if available.
5. Resume ingestion/uploads.

## 4. Validation Steps After Any Recovery

1. Run the local-stack smoke test shape or equivalent health checks.
2. Verify one end-to-end user journey:
   - log in
   - open a Space
   - read a document
   - run a search
3. Check monitoring dashboards for lingering errors.
4. Confirm the daily backup job completed successfully after recovery.
5. Update the incident post-mortem with actual recovery timings.

## 5. Cross-References

- [incident-response.md](incident-response.md)
- [backup-and-retention.md](backup-and-retention.md)
- [privileged-bypass-governance.md](privileged-bypass-governance.md)
- [Architecture state ownership](../architecture.md#51-канон-и-проекции)
