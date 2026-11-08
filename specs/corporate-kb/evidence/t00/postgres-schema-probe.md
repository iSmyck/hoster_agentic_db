# T00 evidence — PostgreSQL schema/role probe

## Scope

Synthetic PostgreSQL 18.6 + pgvector 0.8.7 probe. The check created three schemas and four roles, then verified writer boundaries.

Raw artifacts:

- `_bmad-output/test-artifacts/t00/postgres/schema-checks-v3.sql`
- `_bmad-output/test-artifacts/t00/postgres/schema-results-v3.txt`

SHA-256 raw result: `02ea0791b535972fd93c7471f61fca5de903104ef4d429adf0c5cd0e1eb3c088`

## Result

**PARTIAL PASS — synthetic role/schema isolation, not a product migration or A33 PASS.**

| Probe | Result |
|---|---|
| `kb_authz_rw` can write `kb_authz` | PASS |
| `kb_ops_rw` can write `kb_ops` | PASS |
| `kb_index_rw` can write `kb_index` | PASS |
| `kb_retrieval_ro` can select `kb_index` and receives one row with distance `0` | PASS |
| RLS read policy is explicit; an RLS-only probe without policy returned no rows and was not used as positive evidence | PASS as a required negative control |
| `kb_authz_rw` cannot write `kb_ops` | DENIED as required |
| `kb_ops_rw` cannot write `kb_index` | DENIED as required |
| `kb_index_rw` cannot write `kb_authz` | DENIED as required |
| `kb_retrieval_ro` cannot write `kb_index` | DENIED as required |
| pgvector extension and vector distance query | PASS |

## What this proves

Separate database roles and schemas can enforce the ownership model without relying only on application conventions. A dedicated PostgreSQL instance can host the three managed schemas and an independent upstream schema.

## What remains unproven

- The 39-table product schema/migrations were not created.
- No full component × schema × INSERT/UPDATE/DELETE/DDL matrix was executed.
- No owner migration repeat/rollback/upgrade rehearsal was performed for `kb_authz`, `kb_ops`, `kb_index`.
- Durable recovery-barrier persistence/rebuild semantics are covered separately by [postgres-recovery-probe.md](postgres-recovery-probe.md), 6/6 checks; Git-derived HA/crash/fencing and managed upstream grant write matrix remain unproven.
- The first probe setup failed because of table ownership and an RLS read policy; the corrected v3 probe made each table owner explicit and proved one retrieval row with distance `0`.

## Baseline consequence

T00 can claim **synthetic schema/role feasibility**. Full migrations and A33 evidence remain implementation tasks after G0.
