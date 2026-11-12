# Privileged Bypass Governance

**Owner:** Security + Owner  
**Scope:** Emergency override of normal approval, merge, or access rules by a privileged party (e.g., GitLab Owner, infrastructure admin).

## 1. Principle

Managed merges and approvals are the exclusive responsibility of the Git Orchestrator (GO) after cutover. A privileged GitLab Owner or infrastructure admin may *technically* bypass these rules, but such an action is treated as an **out-of-band integrity incident**, not an approved managed path. This runbook defines the narrow circumstances under which a bypass is authorized, how it is recorded, and how it is reviewed.

## 2. Who Can Authorize a Bypass

| Role | Can Authorize | Conditions |
|---|---|---|
| Product / Business Owner | Yes | Service-impacting emergency where GO cannot act in time |
| Security Lead | Yes | Security incident requiring immediate containment |
| GitLab Owner (technical role) | No self-authorization | May execute only after written/verbal owner or security-lead approval |
| Infrastructure Admin | No self-authorization | May execute only after written/verbal owner or security-lead approval |

## 3. Allowed Conditions

A privileged bypass is allowed only when **all** of the following are true:

1. GO is unavailable or cannot complete the required action within the incident response window.
2. The action is necessary to restore service, contain a security incident, or prevent data loss.
3. Normal approvers cannot be reached in time.
4. The bypass is the least-privilege action required.

A bypass is **never** allowed for routine releases, convenience, or to skip business approval.

## 4. Audit Trail Requirements

For every bypass, record the following *before* execution if possible, otherwise immediately after:

1. **Incident reference** — link to the incident thread or ticket.
2. **Authorization** — name and role of the person who approved the bypass.
3. **Executor** — name and role of the person who performed the bypass.
4. **Justification** — concise description of why normal process could not be used.
5. **Actions taken** — exact commands, SHAs, usernames, and timestamps (UTC).
6. **Affected Spaces / repositories** — list of impacted targets.
7. **Time limit** — maximum duration of any temporary permission or state.

Store the record in the secure incident tracker. Do not commit secrets or private endpoints to the runbook or post-mortem.

## 5. Time Limits

- Temporary permissions granted for a bypass must be revoked within **1 hour** of resolution, or by the end of the incident response, whichever is sooner.
- If a longer window is required, re-authorize with the owner and document the extension.
- After revocation, confirm via GitLab audit log and hoster access log that the privilege is gone.

## 6. Post-Incident Review

Within two business days of a bypass:

1. Security lead reviews the audit record.
2. Owner decides whether the bypass was justified and whether process changes are needed.
3. GO reconciliation is run on affected targets to restore managed state and detect drift.
4. Affected targets remain under heightened monitoring for **7 days**.
5. The post-mortem is linked from [incident-response.md](incident-response.md).

## 7. Example Scenarios

| Scenario | Authorized? | Required Record |
|---|---|---|
| GO down during SEV-1; restore service by manually reverting `main` | Yes, with owner approval | Incident ID, authorizer, executor, SHA, time limit |
| Skip business approval to merge a feature before launch | No | N/A — revert and escalate |
| Security lead removes a compromised admin's access outside of normal IAM workflow | Yes, with post-incident owner review | Incident ID, justification, affected accounts |
| Infrastructure admin extends backup retention for an investigation | Yes, with security-lead approval | Ticket ID, retention change, revocation time |

## 8. Cross-References

- [incident-response.md](incident-response.md)
- [rollback-and-recovery.md](rollback-and-recovery.md)
- [Architecture §4.2 dependency matrix](../architecture.md#42-dependency-and-credential-matrix)
