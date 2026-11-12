# Local stack smoke test

Generated: 2026-11-12T08:39:58.345821+00:00

- PASS: 17
- FAIL: 0
- BLOCKED: 0
- TOTAL: 17

## health.identity — PASS

- Expected: identity health endpoint returns 200
- Actual: status=200

## health.session — PASS

- Expected: session health endpoint returns 200
- Actual: status=200

## health.go — PASS

- Expected: go health endpoint returns 200
- Actual: status=200

## health.retrieval — PASS

- Expected: retrieval health endpoint returns 200
- Actual: status=200

## health.backup — PASS

- Expected: backup health endpoint returns 200
- Actual: status=200

## health.openwebui — PASS

- Expected: openwebui health endpoint returns 200
- Actual: status=200

## health.gitlab — PASS

- Expected: GitLab API is reachable
- Actual: status=200

## session.create_author — PASS

- Expected: session service creates a token for author-1
- Actual: token issued

## session.validate_author — PASS

- Expected: session token validates and returns author-1 stable_id
- Actual: status=200, body={"session_id":"67ff85a5-d654-4144-9a74-be13f44a03dc","stable_id":"author-1","access_policy_revision":"0000000000000000000000000000000000000000","approval_policy_revision":"0000000000000000000000000000

## go.draft_save — PASS

- Expected: GO saves a draft for author-1
- Actual: status=200

## go.draft_get — PASS

- Expected: GO returns the saved draft
- Actual: status=200

## go.history — PASS

- Expected: GO returns commit history for docs/g1-proposal.md
- Actual: status=200, commits=0

## openwebui.kb_page — PASS

- Expected: Open WebUI /kb page is reachable
- Actual: status=200

## openwebui.oidc_config — PASS

- Expected: Open WebUI /api/config shows auth and OIDC provider enabled
- Actual: status=200, auth=True, providers=['oidc']

## keycloak.oidc_token — PASS

- Expected: Keycloak issues an OIDC access token for the test user
- Actual: token present

## session.oidc_validate — PASS

- Expected: Session service accepts the Keycloak OIDC access token
- Actual: status=200, stable_id=http://localhost:8082/realms/corp-kb:a32bd08b-ab6f-4992-86b9-3aff36229078, role=user

## go.identity_me_oidc — PASS

- Expected: GO /api/kb/v1/identity/me returns stable identity for OIDC token
- Actual: status=200, stable_id=http://localhost:8082/realms/corp-kb:a32bd08b-ab6f-4992-86b9-3aff36229078, role=user
