# G1 Open WebUI acceptance summary

Generated: 2026-11-11T21:30:55.291318+00:00

- PASS: 6
- FAIL: 3
- BLOCKED: 0
- TOTAL: 9

## precondition.go_health — PASS

- Expected: GO health endpoint returns 200
- Actual: status=200

## precondition.schema_reset — PASS

- Expected: kb_ops schema reset and migrations applied
- Actual: schema=kb_ops_g1_test

## openwebui.admin_token — PASS

- Expected: admin token available
- Actual: token present

## openwebui.create_users — PASS

- Expected: random per-run author and approver created
- Actual: both tokens present

## security.prepare_requires_session — PASS

- Expected: prepare-branch rejects unauthenticated writes
- Actual: status=401

## security.prepare_rejects_ci_path — FAIL

- Expected: prepare-branch rejects CI/service paths
- Actual: status=401

## security.prepare_replay_idempotent — FAIL

- Expected: prepare retry returns identical proposal/base SHA
- Actual: first=401:{"detail":{"code":"INVALID_SESSION","message":"session token rejected"}}, second=401:{"detail":{"code":"INVALID_SESSION","message":"session token rejected"}}

## openwebui.kb_page_loads — PASS

- Expected: KB editor page loads
- Actual: http://localhost:3100/kb

## openwebui.author_submit — FAIL

- Expected: author submits proposal via Open WebUI
- Actual: Submit proposal button is disabled; status=Ready. Select actor, edit content, then submit proposal.
WARN: initialization failed: GET /api/kb/v1/identity/me -> 401: INVALID_SESSION: session token rejected

