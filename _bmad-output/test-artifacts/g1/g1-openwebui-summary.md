# G1 Open WebUI acceptance summary

Generated: 2026-11-12T08:37:00.215217+00:00

- PASS: 18
- FAIL: 0
- BLOCKED: 0
- TOTAL: 18

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

## openwebui.oidc_tokens — PASS

- Expected: Keycloak OIDC tokens obtained for g1-author and g1-approver
- Actual: both tokens present

## security.prepare_requires_session — PASS

- Expected: prepare-branch rejects unauthenticated writes
- Actual: status=401

## security.prepare_rejects_ci_path — PASS

- Expected: prepare-branch rejects CI/service paths
- Actual: status=400

## security.prepare_replay_idempotent — PASS

- Expected: prepare retry returns identical proposal/base SHA
- Actual: first=200:{"space_id":"corp-kb/sales","proposal_sha":"18bd8f5fffaf85e346666ac490fed1dacc114910","base_sha":"7958c41697b23af49586d0bd23439973f525abda","proposal_branch":"proposal/18bd8f5f","file_path":"docs/g1-p, second=200:{"space_id":"corp-kb/sales","proposal_sha":"18bd8f5fffaf85e346666ac490fed1dacc114910","base_sha":"7958c41697b23af49586d0bd23439973f525abda","proposal_branch":"proposal/18bd8f5f","file_path":"docs/g1-p

## openwebui.kb_page_loads — PASS

- Expected: KB editor page loads
- Actual: http://localhost:3100/kb

## openwebui.author_submit — PASS

- Expected: author submits proposal via Open WebUI
- Actual: proposal_id=5cb4f999-f0b9-4e98-9fea-4997b1d00c20

## openwebui.author_cannot_approve — PASS

- Expected: author session cannot record an approval
- Actual: role":"user"}
Creating branch and commit in GitLab...
{"merge_only":true,"protected":true}
WARN: initialization failed: POST /api/kb/v1/drafts/get -> 404: NOT_FOUND: draft not found
Submitting proposal to GO...
{"proposal_id":"5cb4f999-f0b9-4e98-9fea-4997b1d00c20","proposal_sha":"be0cef00e67bc3a3fd78c47cb70e95babdb87768","base_sha":"7958c41697b23af49586d0bd23439973f525abda"}
Recording decision...
ERROR: POST /api/kb/v1/decisions -> 403: APPROVER_REQUIRED: independent approver capability required

## openwebui.approver_decision — PASS

- Expected: approver records decision in independent session
- Actual: decision_id=b6947da4-68ca-561d-b60f-4a2818faca65

## openwebui.approver_merge — PASS

- Expected: approver executes merge in independent session
- Actual: merge_sha=9ed8082f1d748968a165c2cc2ec2820bc84c110e

## openwebui.independent_sessions — PASS

- Expected: author and approver use independent browser sessions
- Actual: two isolated browser contexts

## openwebui.merge_parentage — PASS

- Expected: merge commit parents equal base_sha and proposal_sha
- Actual: parents=['7958c41697b23af49586d0bd23439973f525abda', 'be0cef00e67bc3a3fd78c47cb70e95babdb87768']

## openwebui.merge_trailers — PASS

- Expected: merge commit contains Decision-ID trailer
- Actual: Merge proposal 5cb4f999-f0b9-4e98-9fea-4997b1d00c20

Decision-ID: b6947da4-68ca-561d-b60f-4a2818faca65
Decision-Note-ID: 156
Decision-Hash: 7441abb59baa9df0d49067f1751ab209a0db807f8d2ed3ff7fa143b9d5d30511
Approved-by: http://localhost:8082/realms/corp-kb:a51015d8-8ba1-47a3-bc52-7bfdac96ac15

## openwebui.decision_tag — PASS

- Expected: protected annotated tag exists on proposal_sha
- Actual: found=True, target_matches=True, protected=True

## openwebui.merged_file_visible — PASS

- Expected: merged page is readable on target branch
- Actual: status=200, len=61

