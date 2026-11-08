# T00 evidence — retrieval and pgvector benchmark

## Scope

Synthetic benchmark used PostgreSQL 18.6 + pgvector 0.8.7 and Ollama `bge-m3:567m` (digest `sha256:7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`, 1024 dimensions). No production corpus or real user data was used.

Raw result: `_bmad-output/test-artifacts/t00/retrieval/results/benchmark.json`

SHA-256 raw result: `7efa8df13e17f54bdc84baef597328f0a65e3eeb394b2b7041194fe9ebe4231e`

## Result

**22/22 deterministic gates PASS** across `source_sanity`, `ids`, `exact`, `russian`, `semantic`, `structured`, `late_stale`, `ops`.

Key measured values:

- scale corpus: 6115 rows;
- 12 configured principals, 29 ACL groups and 51 query modes;
- 102 executed query runs and 218 evaluated rows;
- `hybrid_k=60`;
- 0 cross-Space leaks;
- 0 unauthorized disclosures;
- 0 stale/pending/rejected/preflight results;
- 0 late index writes after publication;
- 100% revision/provenance/citation binding;
- 100% full/incremental closure equivalence.

## Capability findings

| Area | Result | Note |
|---|---|---|
| Exact identifiers, paths and hashes | PASS | Deterministic gates passed |
| Russian FTS `simple` vs `russian` | PASS | `russian` profile measured better morphology; owner thresholds still absent |
| BGE-M3 semantic retrieval | PASS for functional synthetic corpus | MRR `0.8357`, nDCG `0.8793`, recall@10 `0.82`; not production quality approval |
| pgvector HNSW filtered search | PASS | 47/47 rows, 64/64 filter groups, 12/12 access groups; zero wrong-space/unauthorized/stale results |
| IVFFlat threshold | PASS | Index was not silently used below the 5000-row threshold; no rollback/false-positive index creation |
| AccessPolicyChanged / revocation | PASS | Fresh context revoked access without waiting for reindex |
| Late jobs and pointer fencing | PASS | Old jobs did not roll back the active pointer |
| Failed partial run | PASS | Active snapshot remained unchanged |
| Full/incremental dependency closure | PASS | Independent closure equality was required |

## Design consequence

pgvector remains the validated candidate for the existing retrieval path, but this does **not** select final chunking, index profile, embedding provider, quality thresholds, latency SLO or production model. Those remain owner/configuration decisions for later gates. The managed `kb_index` adapter still must use Git revision/snapshot/profile/dependency metadata instead of upstream mutable Knowledge/Notes projections.

## Limitations

- Synthetic corpus is not a proxy for the real sales corpus.
- No hoster.ai embeddings or chat model was used.
- Browser/UI answer quality and LLM grounding were not evaluated.
- Production quality and p95/p99 thresholds are intentionally `owner_TBD`.
