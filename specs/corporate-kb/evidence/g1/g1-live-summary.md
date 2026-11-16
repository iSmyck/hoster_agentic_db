# G1 Live Vertical Slice Acceptance Evidence

- **Generated:** 2026-11-16T22:29:51.464453+00:00
- **Environment:** live_local_gitlab_ce
- **GitLab:** http://localhost:8081 / corp-kb/sales

## Counts

- PASS: 20
- FAIL: 0
- BLOCKED: 0
- TOTAL: 20

## Checks

| ID | Status | Expected | Actual |
|---|---|---|---|
| precondition.health | PASS | GO health endpoint returns 200 | status=200, body={'status': 'ok'} |
| precondition.merge_only_rules | PASS | target branch is protected and merge-only | protected=True, merge_only=True |
| flow.submit_proposal | PASS | proposal accepted and MR created | status=201, body={'id': '0f7da12e-49f5-4ee5-b8bd-45dd47dbe716', 'space_id': 'corp-kb/sales', 'proposal_sha': 'c27c218129 |
| flow.record_decision | PASS | independent human decision recorded with note+tag | status=201, body={'id': 'a413b04c-9db6-5ad0-85c4-08a92c3c2d5e', 'proposal_id': '0f7da12e-49f5-4ee5-b8bd-45dd47dbe716', ' |
| flow.execute_merge | PASS | GO merge succeeds and returns merge_sha | status=200, body={'proposal_id': '0f7da12e-49f5-4ee5-b8bd-45dd47dbe716', 'status': 'merged', 'merge_sha': 'a258c934021e7 |
| flow.merge_parentage | PASS | merge commit parents equal base_sha and proposal_sha | parents=['255d6469ee8963d78f3ce57d5c0bfee2c8ed7bd2', 'c27c218129c62e681da4e68cb401b56b3654262e'] |
| flow.merge_trailers | PASS | merge commit message contains Decision-ID trailer | Merge proposal 0f7da12e-49f5-4ee5-b8bd-45dd47dbe716

Decision-ID: a413b04c-9db6-5ad0-85c4-08a92c3c2d5e
Decision-Note-ID: |
| flow.decision_tag | PASS | protected annotated tag exists on proposal_sha | found=True, target_matches=True, protected=True |
| negative.source_branch_not_found | PASS | proposal without source branch is rejected before merge | status=404 |
| negative.merge_without_decision | PASS | merge without decision rejected with INVALID_STATE | status=409, code=INVALID_STATE |
| negative.actor_spoofing_rejected | PASS | actor spoofing rejected before DecisionRecord anchors | status=403, code=ACTOR_MISMATCH |
| negative.self_approval_by_author | PASS | self-approval rejected before DecisionRecord anchors | status=403, code=SELF_APPROVAL |
| flow.merge_replay_idempotent | PASS | merge replay returns existing merge_sha without another external merge | status=200, merge_sha=a258c934021e7d1016f446ba56f1025b79d7c0ed |
| flow.revert.submit_proposal | PASS | revert proposal accepted and MR created | status=201, body={'id': '30d94bd4-9f9a-4a9a-aef3-9fcefc157c2d', 'space_id': 'corp-kb/sales', 'proposal_sha': 'aa40da3de2 |
| flow.revert.record_decision | PASS | revert decision recorded with note+tag | status=201, body={'id': '520e21c4-3090-5481-a417-8960adad5a6f', 'proposal_id': '30d94bd4-9f9a-4a9a-aef3-9fcefc157c2d', ' |
| flow.revert.execute_merge | PASS | revert merge succeeds and returns merge_sha | status=200, body={'proposal_id': '30d94bd4-9f9a-4a9a-aef3-9fcefc157c2d', 'status': 'merged', 'merge_sha': '79d228a3dc2dc |
| flow.revert.merge_parentage | PASS | revert merge commit parents equal revert base_sha and proposal_sha | parents=['a258c934021e7d1016f446ba56f1025b79d7c0ed', 'aa40da3de2642cfd4493ddcdda402088c2b413e3'] |
| flow.revert.merge_trailers | PASS | revert merge commit message contains Decision-ID trailer | Merge proposal 30d94bd4-9f9a-4a9a-aef3-9fcefc157c2d

Decision-ID: 520e21c4-3090-5481-a417-8960adad5a6f
Decision-Note-ID: |
| flow.revert.file_restored | PASS | merged file no longer exists after revert merge | file_path=docs/g1-proposal-41404bacb05c.md, exists=False |
| flow.revert.decision_tag | PASS | protected annotated tag exists on revert proposal_sha | found=True, target_matches=True, protected=True |

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/g1/run_g1_live_acceptance.py
```
