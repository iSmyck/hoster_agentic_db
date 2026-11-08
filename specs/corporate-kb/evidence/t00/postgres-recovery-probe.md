# T00 evidence — GO recovery barrier persistence semantics

## Scope

Synthetic PostgreSQL probe for `kb_ops` projection and recovery semantics. It is not the full product schema/migration test.

Raw artifacts:

- `_bmad-output/test-artifacts/t00/postgres/recovery-probe.sql`
- `_bmad-output/test-artifacts/t00/postgres/recovery-results.txt`

SHA-256 raw result: `d34f62a50f4169d708f3f5a3c1bbe3461c19046911dec5491c443f4bde489220`

## Result

**6 PASS / 0 FAIL**

| Check | Result |
|---|---|
| Unknown `merge_attempted` preserves `recovery_required` | PASS |
| Verified merge plus completed reconciliation clears the target barrier | PASS |
| Conflicted/unproven outcome preserves the target barrier | PASS |
| Guarded `failed` retry requires completed request and proven no-merge | PASS |
| Retry is denied while request completion is unproven | PASS |
| `unique(decision_id)` rejects duplicate merge decisions | PASS |

## Semantics demonstrated

- Projection state can be rebuilt from canonical decision inputs.
- A target barrier is not cleared by a generic `invalid/conflicted` state or by timeout alone.
- Only verified merge proof plus a completed target-wide reconciliation clears it.
- `failed` is retryable only with both completion and no-merge proof.
- Duplicate decision IDs cannot create a second merge operation.

## Remaining work

This is a semantic SQL probe, not the final 39-table migration, HA/fencing test, owner rollback/rebuild drill or A33 acceptance. Those remain implementation tasks after G0.
