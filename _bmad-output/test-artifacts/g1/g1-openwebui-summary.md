# G1 Open WebUI acceptance summary

Generated: 2026-11-10T10:20:48.766573+00:00

- PASS: 17
- FAIL: 0
- BLOCKED: 0
- TOTAL: 17

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

## security.prepare_rejects_ci_path — PASS

- Expected: prepare-branch rejects CI/service paths
- Actual: status=400

## security.prepare_replay_idempotent — PASS

- Expected: prepare retry returns identical proposal/base SHA
- Actual: first=200:{"space_id":"corp-kb/sales","proposal_sha":"4d3504ce82f06a851ebe707304be2a1ba290d52c","base_sha":"ed79b829a7063f637c6757afb1a4665ecc052ff8","proposal_branch":"proposal/4d3504ce","file_path":"docs/g1-p, second=200:{"space_id":"corp-kb/sales","proposal_sha":"4d3504ce82f06a851ebe707304be2a1ba290d52c","base_sha":"ed79b829a7063f637c6757afb1a4665ecc052ff8","proposal_branch":"proposal/4d3504ce","file_path":"docs/g1-p

## openwebui.kb_page_loads — PASS

- Expected: KB editor page loads
- Actual: http://localhost:5050/kb

## openwebui.author_submit — PASS

- Expected: author submits proposal via Open WebUI
- Actual: proposal_id=101532d5-0080-4ecd-b5a6-a17f1d7cad66

## openwebui.author_cannot_approve — PASS

- Expected: author session cannot record an approval
- Actual: or, edit content, then submit proposal.
{"stable_id":"g1-author-aa0a26bc36d3@hoster.test","role":"user"}
Creating branch and commit in GitLab...
{"merge_only":true,"protected":true}
Submitting proposal to GO...
{"proposal_id":"101532d5-0080-4ecd-b5a6-a17f1d7cad66","proposal_sha":"1984fe66f399c73fa15c14dda7ea0822f8964c0c","base_sha":"ed79b829a7063f637c6757afb1a4665ecc052ff8"}
Recording decision...
ERROR: POST /api/kb/v1/decisions -> 403: APPROVER_REQUIRED: independent approver capability required

## openwebui.approver_decision — PASS

- Expected: approver records decision in independent session
- Actual: decision_id=cf595329-dd49-58e3-8fed-67cbe5b0e0e5

## openwebui.approver_merge — PASS

- Expected: approver executes merge in independent session
- Actual: merge_sha=1373dc28929ecc91a36fe130fa87b0e6dbdcc21f

## openwebui.independent_sessions — PASS

- Expected: author and approver use independent browser sessions
- Actual: two isolated browser contexts

## openwebui.merge_parentage — PASS

- Expected: merge commit parents equal base_sha and proposal_sha
- Actual: parents=['ed79b829a7063f637c6757afb1a4665ecc052ff8', '1984fe66f399c73fa15c14dda7ea0822f8964c0c']

## openwebui.merge_trailers — PASS

- Expected: merge commit contains Decision-ID trailer
- Actual: Merge proposal 101532d5-0080-4ecd-b5a6-a17f1d7cad66

Decision-ID: cf595329-dd49-58e3-8fed-67cbe5b0e0e5
Decision-Note-ID: 145
Decision-Hash: 3058ff2fde3de6d4f256f2316065e39998a0a024aa651825626023c099fa43dc
Approved-by: g1-approver-aa0a26bc36d3@hoster.test

## openwebui.decision_tag — PASS

- Expected: protected annotated tag exists on proposal_sha
- Actual: found=True, target_matches=True, protected=True

## openwebui.merged_file_visible — PASS

- Expected: merged page is readable on target branch
- Actual: status=200, len=61

