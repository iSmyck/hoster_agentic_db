# T00 evidence index

Status: **collected for owner review**. Machine-generated raw artifacts remain in `_bmad-output/test-artifacts/t00/` and are not committed.

| Document | Result |
|---|---|
| `independent-review.md` | Final independent review: 18 checks, 15/15 hashes and 18/18 targets PASS |
| `manifest.json` | Machine-readable check IDs, commands, environments, statuses, raw SHA-256 and sanitized links |
| `environment.md` | Pinned versions, sandbox hosts and toolchain |
| `gitlab-capabilities.md` | GitLab CE capability probes: 42 completed, including nonconforming target-race evidence |
| `postgres-recovery-probe.md` | GO recovery barrier persistence/rebuild semantics: 6 PASS / 0 FAIL |
| `object-store.md` | S3 immutable versions: 5 PASS / 1 ACL FAIL — partial evidence |
| `ci-runner.md` | GitLab Runner exact-SHA pipeline: 7 PASS / 0 FAIL / 0 BLOCKED |
| `ldap-capabilities.md` | OpenLDAP/LDAPS/StartTLS stable identity and revocation: 8 PASS / 0 FAIL |
| `identity-capabilities.md` | Keycloak identity adapter: 9 PASS / 0 FAIL / 0 BLOCKED |
| `notes-chats-regression.md` | Personal Notes/chats API authorization baseline: 8 PASS / 0 FAIL |
| `postgres-schema-probe.md` | Synthetic `kb_authz`/`kb_ops`/`kb_index` roles and cross-write denials: partial PASS |
| `approval-policy-probe.md` | Path-scoped approval policy semantics: 14 PASS / 0 FAIL |
| `openwebui-oidc-runtime.md` | Stock OIDC login: 4 PASS / 2 security FAIL / 0 BLOCKED |
| `openwebui-auth-audit.md` | Static auth, execution and migration audit with required adapters |
| `openwebui-rag-editor-audit.md` | Retrieval/editor source audit and editor fidelity evidence |
| `openwebui-toolchain.md` | Backend/frontend runtime, migrations, build and test evidence |
| `retrieval-benchmark.md` | pgvector synthetic benchmark: 22/22 deterministic gates PASS |
| `openwebui-license-review.md` | License/branding evidence; not legal clearance |
| `capability-matrix.md` | Cross-cutting PASS/ADAPTER/G0-DECISION/UNKNOWN matrix |

## Current gate conclusion

- GitLab, identity adapter feasibility, migration ownership, runtime role separation and pgvector deterministic checks have evidence.
- Stock Open WebUI identity and execution boundaries require adapters.
- G0-D1–D17 are APPROVED with follow-up gates.
- **T00 DONE, G0 APPROVED.** Deferred browser/object-store/hoster checks remain mandatory follow-up work and are not claimed as PASS.
