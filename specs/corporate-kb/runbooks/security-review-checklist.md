# Security Review Checklist

**Owner:** Security + QA  
**Scope:** Per-release security gate for the Corporate Agentic Knowledge Platform minimal production target.

## 1. Release Candidate Information

| Field | Value |
|---|---|
| Release version / tag | |
| Branch / SHA | |
| Release owner | |
| Review date | |
| Reviewers | |

## 2. Dependency Vulnerability Scan

- [ ] Run dependency scanner on Python requirements and Node packages.
- [ ] Review scan output for CRITICAL and HIGH findings.
- [ ] For any accepted risk, document the finding ID, impact, and compensating control.
- [ ] Confirm no known exploitable vulnerabilities in the pinned baseline:
  - Open WebUI `v0.13.0` (`c38885a1a737da4968f157092f304f3b5481d0bf`)
  - GitLab CE `19.5.3-ce.0`
  - PostgreSQL `18.6` + pgvector `0.8.7`
  - Keycloak `26.8.2`

## 3. Secret Scan

- [ ] Run secret-detection scan on the release branch.
- [ ] Verify no committed secrets, tokens, or private keys.
- [ ] Check that deployment secrets are loaded from the secret mechanism, not source code.
- [ ] Verify no secrets in test fixtures or synthetic data.

## 4. ACL and Access Review

- [ ] Confirm GitLab protected-branch rules still enforce `push_access_level=0`, `merge_access_level=40`.
- [ ] Confirm GO is the only identity with merge permission after cutover.
- [ ] Review Space access/approval policies for stale group mappings.
- [ ] Verify revocation epoch is enforced by the identity adapter.
- [ ] Confirm object-store ACLs restrict bucket access to expected service identities.

## 5. Audit-Log Review

- [ ] Review GO audit logs for the release window.
- [ ] Look for failed authorization spikes, unusual proposal patterns, or bypass attempts.
- [ ] Review GitLab audit log for any privileged Owner actions outside GO.
- [ ] Confirm DecisionRecord tags (`kb-decisions/*`) are present and consistent.

## 6. XSS and Input-Sanitization Checks

- [ ] Confirm TipTap editor output is sanitized before preview and render (DOMPurify).
- [ ] Verify that user-provided Markdown / front matter is not rendered as raw HTML.
- [ ] Run input-fuzzing checks on GO endpoints for injection payloads.
- [ ] Confirm agent tool schemas do not expose merge, grant, or arbitrary execution capabilities.

## 7. Network and Egress

- [ ] Confirm production ingress/egress policy is documented and unchanged.
- [ ] Verify no new outbound dependencies were added without review.
- [ ] Confirm hoster.ai studio connection uses the managed model connection only.

## 8. Sign-Off

| Role | Name | Date | Result |
|---|---|---|---|
| Security Lead | | | Pass / Fail / Conditional |
| QA Lead | | | Pass / Fail / Conditional |
| Release Owner | | | Pass / Fail / Conditional |

## 9. Conditional Release

If the checklist result is **Conditional**:

1. Document each condition and the compensating control or follow-up issue.
2. Owner must approve the conditional release in writing.
3. Blockers must be tracked as backlog items with owners and due dates.

## 10. Out of Scope

The following are explicitly deferred and not part of this checklist:

- External penetration test (deferred post-launch per owner decision).
- Production AD / live-SLO integration (deferred per [G1-D6](../architecture.md)).
- Full A01–A36 fault matrix live destructive acceptance (optional; synthetic acceptance is the gate).

## 11. Cross-References

- [monitoring-alerting-checklist.md](monitoring-alerting-checklist.md)
- [incident-response.md](incident-response.md)
- [privileged-bypass-governance.md](privileged-bypass-governance.md)
