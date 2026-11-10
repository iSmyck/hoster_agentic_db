# G1 Live Vertical Slice Acceptance Evidence

- **Generated:** 2026-11-10T10:19:38.830806+00:00
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
| flow.submit_proposal | PASS | proposal accepted and MR created | status=201, body={'id': '4cb66886-e2db-4ea3-9263-6d5bc850373f', 'space_id': 'corp-kb/sales', 'proposal_sha': 'fbbd3f68c5 |
| flow.record_decision | PASS | independent human decision recorded with note+tag | status=201, body={'id': 'd93627af-4702-5a7f-939f-9d5616cba658', 'proposal_id': '4cb66886-e2db-4ea3-9263-6d5bc850373f', ' |
| flow.execute_merge | PASS | GO merge succeeds and returns merge_sha | status=200, body={'proposal_id': '4cb66886-e2db-4ea3-9263-6d5bc850373f', 'status': 'merged', 'merge_sha': '666dc259d6e5e |
| flow.merge_parentage | PASS | merge commit parents equal base_sha and proposal_sha | parents=['76772cc3a475a93f1608dc01012a8b7d9a13f0d4', 'fbbd3f68c52fdac053e0d31f9d0767adc16143f9'] |
| flow.merge_trailers | PASS | merge commit message contains Decision-ID trailer | Merge proposal 4cb66886-e2db-4ea3-9263-6d5bc850373f

Decision-ID: d93627af-4702-5a7f-939f-9d5616cba658
Decision-Note-ID: |
| flow.decision_tag | PASS | protected annotated tag exists on proposal_sha | found=True, target_matches=True, protected=True |
| negative.source_branch_not_found | PASS | proposal without source branch is rejected before merge | status=404 |
| negative.merge_without_decision | PASS | merge without decision rejected with INVALID_STATE | status=409, code=INVALID_STATE |
| negative.actor_spoofing_rejected | PASS | actor spoofing rejected before DecisionRecord anchors | status=403, code=ACTOR_MISMATCH |
| negative.self_approval_by_author | PASS | self-approval rejected before DecisionRecord anchors | status=403, code=SELF_APPROVAL |
| flow.merge_replay_idempotent | PASS | merge replay returns existing merge_sha without another external merge | status=200, merge_sha=666dc259d6e5edea93a1b0fe0cf04f9d3c8c8f22 |
| flow.revert.submit_proposal | PASS | revert proposal accepted and MR created | status=201, body={'id': '032063f3-25a3-488b-a184-34f5ba7372b2', 'space_id': 'corp-kb/sales', 'proposal_sha': 'e33305ddaf |
| flow.revert.record_decision | PASS | revert decision recorded with note+tag | status=201, body={'id': '8a860871-65ac-51fd-9fe7-39f8f3128a00', 'proposal_id': '032063f3-25a3-488b-a184-34f5ba7372b2', ' |
| flow.revert.execute_merge | PASS | revert merge succeeds and returns merge_sha | status=200, body={'proposal_id': '032063f3-25a3-488b-a184-34f5ba7372b2', 'status': 'merged', 'merge_sha': 'ed79b829a7063 |
| flow.revert.merge_parentage | PASS | revert merge commit parents equal revert base_sha and proposal_sha | parents=['666dc259d6e5edea93a1b0fe0cf04f9d3c8c8f22', 'e33305ddaf6927e6590ee01ab87309998742d54d'] |
| flow.revert.merge_trailers | PASS | revert merge commit message contains Decision-ID trailer | Merge proposal 032063f3-25a3-488b-a184-34f5ba7372b2

Decision-ID: 8a860871-65ac-51fd-9fe7-39f8f3128a00
Decision-Note-ID: |
| flow.revert.file_restored | PASS | merged file no longer exists after revert merge | file_path=docs/g1-proposal-8fe727fde0b4.md, exists=False |
| flow.revert.decision_tag | PASS | protected annotated tag exists on revert proposal_sha | found=True, target_matches=True, protected=True |

## Rerun instructions

```bash
uv run python _bmad-output/test-artifacts/g1/run_g1_live_acceptance.py
```
