# T00 evidence — path-scoped approval policy semantics

## Scope

Policy-level probe against the actual `contracts/approval-policy.schema.json` and a synthetic versioned `approval-policy.yaml`. This is not a product implementation or browser review test.

Raw result: `_bmad-output/test-artifacts/t00/identity/approval-policy-results.json`

SHA-256 raw result: `f219fae250c0c29a8ac7dcea5805721120f009e42e4b9927dafcfefc2f00967b`

## Result

**14 PASS / 0 FAIL**, including JSON Schema validation.

| Capability | Result |
|---|---|
| Longest normalized path prefix selects the eligible group | PASS |
| Less-specific sales/root rules cannot widen pricing scope | PASS |
| Root fallback applies only where no more-specific rule exists | PASS |
| Contractor and unmatched groups denied | PASS |
| Author self-approval denied | PASS |
| Requester self-approval denied | PASS |
| Version-author self-approval denied | PASS |
| Group removal revokes approval | PASS |
| Duplicate normalized prefix rejected | PASS |
| Access/approval policy revisions are independently bound and mismatch is rejected | PASS |

## Consequence

The selected business approval model is implementable with external groups and path scopes, without GitLab user records or CODEOWNERS business grants. Product enforcement and actual group/path snapshots remain implementation tasks.

## Limitations

- This is a policy semantics probe, not a complete approval-policy engine or end-to-end merge.
- Production AD groups, approver scopes and actual policy files are not selected.
- Browser review UX and measured revocation SLO remain separate checks.
