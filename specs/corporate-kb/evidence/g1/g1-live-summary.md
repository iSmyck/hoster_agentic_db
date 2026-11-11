# G1 Live Vertical Slice Acceptance Evidence

- **Generated:** 2026-11-11T20:01:40.335974+00:00
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
| flow.submit_proposal | PASS | proposal accepted and MR created | status=201, body={'id': '409ef1a3-55ec-4115-8609-52c6cff431bd', 'space_id': 'corp-kb/sales', 'proposal_sha': '764bd90d10 |
| flow.record_decision | PASS | independent human decision recorded with note+tag | status=201, body={'id': '0152e83e-cd19-58d0-aebc-6167f87cf240', 'proposal_id': '409ef1a3-55ec-4115-8609-52c6cff431bd', ' |
| flow.execute_merge | PASS | GO merge succeeds and returns merge_sha | status=200, body={'proposal_id': '409ef1a3-55ec-4115-8609-52c6cff431bd', 'status': 'merged', 'merge_sha': 'f70ee4152588b |
| flow.merge_parentage | PASS | merge commit parents equal base_sha and proposal_sha | parents=['1373dc28929ecc91a36fe130fa87b0e6dbdcc21f', '764bd90d10a15389fef8a292d7078da11bd78cfc'] |
| flow.merge_trailers | PASS | merge commit message contains Decision-ID trailer | Merge proposal 409ef1a3-55ec-4115-8609-52c6cff431bd

Decision-ID: 0152e83e-cd19-58d0-aebc-6167f87cf240
Decision-Note-ID: |
| flow.decision_tag | PASS | protected annotated tag exists on proposal_sha | found=True, target_matches=True, protected=True |
| negative.source_branch_not_found | PASS | proposal without source branch is rejected before merge | status=404 |
| negative.merge_without_decision | PASS | merge without decision rejected with INVALID_STATE | status=409, code=INVALID_STATE |
| negative.actor_spoofing_rejected | PASS | actor spoofing rejected before DecisionRecord anchors | status=403, code=ACTOR_MISMATCH |
| negative.self_approval_by_author | PASS | self-approval rejected before DecisionRecord anchors | status=403, code=SELF_APPROVAL |
| flow.merge_replay_idempotent | PASS | merge replay returns existing merge_sha without another external merge | status=200, merge_sha=f70ee4152588b2f7e4c3fbd4e59f42aef1e1a81b |
| flow.revert.submit_proposal | PASS | revert proposal accepted and MR created | status=201, body={'id': '6aae8625-bb0e-48fb-8dcb-0b156fce8783', 'space_id': 'corp-kb/sales', 'proposal_sha': 'a13a7206da |
| flow.revert.record_decision | PASS | revert decision recorded with note+tag | status=201, body={'id': '3d1967ac-d93c-5b61-89d5-61c66386f3d9', 'proposal_id': '6aae8625-bb0e-48fb-8dcb-0b156fce8783', ' |
| flow.revert.execute_merge | PASS | revert merge succeeds and returns merge_sha | status=200, body={'proposal_id': '6aae8625-bb0e-48fb-8dcb-0b156fce8783', 'status': 'merged', 'merge_sha': '1e0510b6dc706 |
| flow.revert.merge_parentage | PASS | revert merge commit parents equal revert base_sha and proposal_sha | parents=['f70ee4152588b2f7e4c3fbd4e59f42aef1e1a81b', 'a13a7206dacad9f8c6948723475abb29d94deaba'] |
| flow.revert.merge_trailers | PASS | revert merge commit message contains Decision-ID trailer | Merge proposal 6aae8625-bb0e-48fb-8dcb-0b156fce8783

Decision-ID: 3d1967ac-d93c-5b61-89d5-61c66386f3d9
Decision-Note-ID: |
| flow.revert.file_restored | PASS | merged file no longer exists after revert merge | file_path=docs/g1-proposal-275214b92f8e.md, exists=False |
| flow.revert.decision_tag | PASS | protected annotated tag exists on revert proposal_sha | found=True, target_matches=True, protected=True |

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/g1/run_g1_live_acceptance.py
```
