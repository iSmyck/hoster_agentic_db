# Local stack smoke test

Generated: 2026-11-11T21:11:44.296499+00:00

- PASS: 13
- FAIL: 0
- BLOCKED: 0
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

## health.gitlab — PASS

- Expected: GitLab API is reachable
- Actual: status=200

## session.create_author — PASS

- Expected: session service creates a token for author-1
- Actual: token issued

## session.validate_author — PASS

- Expected: session token validates and returns author-1 stable_id
- Actual: status=200, body={"session_id":"eb4d56a5-11f2-451d-9832-86464aeb20f8","stable_id":"author-1","access_policy_revision":"0000000000000000000000000000000000000000","approval_policy_revision":"0000000000000000000000000000

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
