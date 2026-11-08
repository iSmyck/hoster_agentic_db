# T00 evidence — OpenLDAP runtime capabilities

## Scope

Real OpenLDAP `osixia/openldap:1.5.0`, ARM64 digest `sha256:6eeadde8221baec7c2166109d66a0bc502e63e71828900e6fb5a0d0d76468a20`, TLS enabled, synthetic users/groups only. Transport checks used LDAPS and StartTLS with a synthetic CA.

Raw result: `_bmad-output/test-artifacts/t00/ldap/capability-results.json`

SHA-256 raw result: `23e3826934a1b7ca4e076f8419b88ffbb9c5fde29079bc7309f1e49c9ee1b1ac`

## Result

**8 PASS / 0 FAIL**

| Capability | Result |
|---|---|
| LDAPS read with read-only service bind | PASS |
| StartTLS read with read-only service bind | PASS |
| `entryUUID` remains stable after email rename | PASS |
| Nested group closure includes direct and parent groups | PASS |
| Read-only bind cannot modify entries | PASS |
| Empty password is rejected | PASS |
| Removing the last user membership clears managed groups and preserves personal grant | PASS |
| Identity lookup after email rename remains unique | PASS |

## Operational finding

OpenLDAP `groupOfNames` requires at least one `member`; deleting the last member fails with object class violation. The leaver scenario therefore used a valid `replace member` operation. Group cleanup and empty-group policy must be handled explicitly by the identity adapter.

## Consequence

LDAP can be included in the selected MVP identity profile, with the mandatory adapter for stable identity, nested groups and ownership-aware revocation. Stock Open WebUI LDAP is still not an ADR-010 implementation: upstream links by email and does not prove these guarantees.

## Limitations

- This was a real OpenLDAP runtime, not a production AD tenant.
- No production hoster AD, live subscriptions or measured ≤30 minute revocation SLO was tested.
- No OpenWebUI stock LDAP browser login was executed.
