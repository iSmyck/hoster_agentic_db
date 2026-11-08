# T00 evidence — OIDC identity adapter capabilities

## Scope

Проверен synthetic Keycloak `26.8.2`, image digest `sha256:3879c623248408de29a5303178b5816c77e8dfef3890c361f8c0bbeaa979ba3b`. Использовались только synthetic realms, users, groups, UUID и email `*.t00.invalid`.

Raw result: `_bmad-output/test-artifacts/t00/identity/capability-results.json`

SHA-256 raw result: `9fec4c4200911639fd87ebb9c17ea04f1f43b1f1e9b39f25be699e1d63f9c664`

## Result

**9 PASS / 0 FAIL / 0 BLOCKED** для sandbox identity adapter profile.

| Capability | Result |
|---|---|
| OIDC discovery, issuer, token/userinfo endpoints | PASS |
| Stable `issuer + sub` survives username/email rename | PASS |
| Duplicate/ambiguous identity rejected | PASS |
| Direct group plus nested parent resolution | PASS |
| Second reader isolation | PASS |
| Removal from last external group clears managed groups | PASS |
| Personal grant survives external membership removal | PASS |
| Missing/empty OIDC groups claim is fail-closed | PASS |
| Failed snapshot does not produce AuthzContext | PASS |
| Cross-issuer same username/email/sub collision rejected | PASS |

## Upstream Open WebUI implication

The synthetic adapter result is **not** an Open WebUI stock PASS. Static audit shows that upstream LDAP links users by email, does not persist objectGUID/entryUUID, treats OIDC provider alias instead of issuer+sub, does not build nested AD closure, and does not revoke memberships on empty group claims. Therefore ADR-010 requires the external identity/AuthZ adapter and ownership-aware group reconciliation; upstream stock JIT alone is insufficient.

## Required implementation consequences

1. Persist `(issuer, sub)` or `(directory, objectGUID/entryUUID)` in `kb_authz`, not email/login.
2. Use the IdP/Admin API as the authoritative group source; OIDC claims are hints, not safe revocation evidence.
3. External memberships are managed projections and must be removed independently from personal grants.
4. AuthzContext is fail-closed unless policy and group snapshots are `ready` and epoch-matched.
5. Group re-evaluation must run at least every 15 minutes and immediately before merge/export/closed-page delivery; the ≤30 minute SLO is an owner-approved policy, not a measured production SLA.

## Limitations

- LDAPS/OpenLDAP runtime was not executed.
- No production AD, hoster IdP or real users were used.
- OpenWebUI browser/OIDC login was not part of this adapter harness.
- This evidence proves adapter feasibility, not completion of the adapter implementation.
