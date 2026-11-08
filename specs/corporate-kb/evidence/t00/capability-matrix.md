# T00 capability matrix

Status legend: **PASS** means the synthetic baseline evidence supports the capability; **ADAPTER** means an upstream seam exists but a product adapter is required; **G0-DECISION** means the owner must accept a risk or choose an option; **UNKNOWN** means no valid evidence exists.

| Capability / ADR | Status | Evidence | Consequence |
|---|---|---|---|
| Git-native canonical storage, MR proposals, merge commits, DecisionRecord tags/notes, export, cutover | **PASS WITH NONCONFORMING RACE EVIDENCE** | `gitlab-capabilities.md`, 42 completed probes | Viable only with mandatory GO target serialization; GitLab race merged against advanced target |
| GitLab CE protected main without per-user grants | **PASS** | `gitlab-capabilities.md` | Use role-based profile: no push, merge only Maintainers, only GO is Maintainer |
| GitLab target-branch CAS | **ADAPTER** | `gitlab-capabilities.md` | GO per-target lock and durable recovery barrier are mandatory |
| GitLab instance/project Owner bypass | **APPROVED WITH GOVERNANCE** | `gitlab-capabilities.md` | Restricted accounts, audit and out-of-band reconciliation approved; absolute merge-only-GO for admins is not claimed |
| Stable LDAP/OIDC identity in stock Open WebUI | **ADAPTER** | `openwebui-auth-audit.md`, `identity-capabilities.md` | External identity/AuthZ adapter is mandatory |
| Nested groups, empty-group revocation, issuer+sub/entryUUID, LDAPS/StartTLS and path-scoped approval | **PASS adapter/policy/runtime feasibility** | `identity-capabilities.md`, Keycloak 9/9; `approval-policy-probe.md`, 14/14; `ldap-capabilities.md`, OpenLDAP 8/8 | Mandatory identity adapter and fresh group snapshots remain required |
| Open WebUI stock OIDC as ADR-010 implementation | **FAIL / ADAPTER REQUIRED** | `openwebui-oidc-runtime.md` | Login/session/persistence and initial groups sync work, but issuer+sub and missing-group revocation fail |
| Arbitrary Python/tool execution boundary | **ADAPTER** | `openwebui-auth-audit.md` | Disable unmanaged tools and enforce capabilities in both native and legacy paths |
| Stock tool approval as business approval | **ADAPTER** | `openwebui-auth-audit.md` | Use platform review + GO DecisionRecord, not stock same-owner approval |
| Personal Notes and ordinary chats baseline | **PASS** | `notes-chats-regression.md`, 8/8 | Private content is not readable or enumerable by another non-admin user; browser E2E remains separate |
| PostgreSQL schema ownership, runtime DDL denial and recovery semantics | **PARTIAL PASS** | `openwebui-toolchain.md`, `postgres-schema-probe.md`, `postgres-recovery-probe.md` | Synthetic roles/denials and 6 recovery checks passed; full product migrations/HA remain pending |
| Open WebUI Alembic migrations | **PASS with controls** | `openwebui-toolchain.md` | Single migrator, head `e42c8f710a36`, runtime migrations disabled |
| pgvector retrieval and ACL-aware synthetic benchmark | **PASS** | `retrieval-benchmark.md`, 22/22 | pgvector remains the baseline candidate; production quality thresholds still TBD |
| Frontend dependency install, Vitest, direct Vite build | **PASS** | `openwebui-toolchain.md` | Node 22, npm ci, 4/4 tests, direct 6 GiB build |
| Upstream `npm run build` script | **FAIL / APPROVED RISK** | `openwebui-toolchain.md` | Direct 6 GiB Vite build works; hardcoded 12 GiB script heap is tracked as build-profile debt |
| Upstream svelte-check and ESLint | **FAIL / APPROVED DEBT** | `openwebui-toolchain.md` | 5722 typecheck errors and ESLint parser crash; not healthy gates; debt is tracked explicitly |
| Markdown editor fidelity | **APPROVED: TipTap adapter; browser DEFERRED** | `openwebui-rag-editor-audit.md`, editor summary | TipTap requires canonical adapter and T04 browser gates; CodeMirror/hybrid rejected for this baseline |
| Object-store immutable versions and ACL | **PARTIAL / APPROVED DEFERRAL** | `object-store.md`, 5/6 | Immutable version/hash semantics passed; cross-bucket denial failed in LocalStack and needs production-engine recheck |
| CI exact-SHA execution | **PASS** | `ci-runner.md`, 7/7 | Real runner job, exact SHA/object read, protected ref, artifact match and no write-back |
| OpenAI-compatible hoster.ai endpoint/models | **UNKNOWN** | no endpoint provided | Deferred after T00; blocks later hoster checks, not this baseline |
| License/branding for managed distribution | **APPROVED WITH LEGAL FOLLOW-UP** | `openwebui-license-review.md` | Preserve branding; no white-label/commercial distribution before legal clearance |
