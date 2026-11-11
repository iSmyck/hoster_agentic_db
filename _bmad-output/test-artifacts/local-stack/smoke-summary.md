# Local stack smoke test

Generated: 2026-11-10T21:58:53.870054+00:00

- PASS: 12
- FAIL: 0
- BLOCKED: 1
- TOTAL: 13

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

## health.gitlab — BLOCKED

- Expected: GitLab API is reachable (requires token)
- Actual: status=401, no GITLAB_TOKEN configured

## session.create_author — PASS

- Expected: session service creates a token for author-1
- Actual: token issued

## session.validate_author — PASS

- Expected: session token validates and returns author-1 stable_id
- Actual: status=200, body={"session_id":"dba4b98d-fa62-47d5-acdd-ab313b461671","stable_id":"author-1","access_policy_revision":"0000000000000000000000000000000000000000","approval_policy_revision":"0000000000000000000000000000

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
