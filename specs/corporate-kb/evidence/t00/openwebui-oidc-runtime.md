# T00 evidence — stock Open WebUI OIDC runtime

## Scope

Stock Open WebUI `v0.13.0` was connected to synthetic Keycloak `26.8.2` using the `corporate-kb-t00` realm and confidential client `kb-t00-oidc`. The check used a browserless HTTP login form flow; no JavaScript browser, production IdP, real users, tokens, emails, authorization code or state values were stored.

Raw result: `_bmad-output/test-artifacts/t00/identity/openwebui-oidc-results.json`

## Result

**4 PASS / 2 FAIL / 0 BLOCKED**

| Check | Result | Consequence |
|---|---|---|
| OIDC provider advertised by stock `/api/config` | PASS | The upstream OIDC seam is available |
| Keycloak login form → Open WebUI callback | PASS | Stock OIDC login works in the synthetic setup |
| Session and PostgreSQL user persistence | PASS | OIDC user survives backend restart |
| Initial groups claim synchronization | PASS | Stock group claim mapping works for present groups |
| Issuer + sub persistence | **FAIL** | Open WebUI stores `provider_alias + sub`; issuer is not part of the identity key |
| Revocation after missing `groups` claim | **FAIL** | Stale membership remains after the IdP group is removed |

## Design conclusion

Stock OIDC is usable only as an authentication/session seam. It is not sufficient for ADR-010 stable identity and revocation. The external identity/AuthZ adapter remains mandatory for issuer-scoped identity, nested groups and authoritative group snapshots.

## Limitations

- No browser JavaScript, accessibility, CSRF matrix or production IdP was tested.
- The synthetic session user became `admin` because the first Open WebUI user has bootstrap admin semantics; this is not a corporate role-mapping result.
- The two FAILs are security evidence and must remain visible in G0 review.
