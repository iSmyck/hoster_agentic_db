# T00 baseline — Corporate Agentic Knowledge Platform

Status: **DONE — G0 approved**  
Date: 2026-11-07  
Scope: T00 baseline audit for the proposed architecture in `spec.md`, `architecture-spine.md`, ADR-003–ADR-016 and the design companions. This is not production approval.

## 1. Selected baseline

| Component | Baseline | Status |
|---|---|---|
| Platform upstream | Open WebUI `v0.13.0`, commit `c38885a1a737da4968f157092f304f3b5481d0bf` | Selected for T00; **G0 owner review APPROVED 2026-11-08** |
| Git service | GitLab CE `19.5.3-ce.0`, revision `0d4c9a9a2fa` | Selected and runtime-verified |
| Relational/vector database | PostgreSQL `18.6`, pgvector `0.8.7`, image `pgvector/pgvector:0.8.7-pg18-trixie` | Selected and runtime-verified |
| Identity sandbox | Keycloak `26.8.2` | Used to prove the identity adapter approach; production IdP remains owner-selected |
| CI runner | GitLab Runner `19.5.3`, revision `33227fd4`, darwin/arm64 | Selected; exact-SHA pipeline probe is recorded separately |
| Backend runtime | Python `3.12.13`, uv `0.11.13` | Verified |
| Frontend runtime | Node `22.23.4`, npm 11 | Verified |
| Git object format | SHA-1 | Verified locally |
| Synthetic embedding model | Ollama `bge-m3:567m`, digest `sha256:7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`, 1024 dimensions | Benchmark-only, not production model selection |

Repository rule: **one GitLab repository = one Space**. Business owners have no GitLab user records; only GO has the normal Maintainer merge path.

## 2. Sandbox environment

All runtime evidence used synthetic local services and data:

- GitLab on `localhost:8080`;
- PostgreSQL/pgvector on `localhost:55432`;
- Keycloak on `localhost:8443`;
- Ollama on `localhost:11434`;
- Open WebUI backend on `localhost:3100`.

No production endpoints, customer documents, real identities or secrets were used.

Environment evidence: `evidence/t00/environment.md`.

## 3. Reproducible commands

### Checkout

```bash
git clone --branch v0.13.0 --depth 1 https://github.com/open-webui/open-webui.git
```

The verified checkout head is `c38885a1a737da4968f157092f304f3b5481d0bf`.

### Backend dependencies and checks

```bash
uv sync --frozen --group dev
uv sync --frozen --group dev --extra postgres
uv run ruff format --check . --exclude .venv --exclude venv
uv run ruff check --select=F --ignore=F401,F403,F405,F541,F811,F841 --output-format=github .
uv run pytest -q
```

Results:

- dependency install: **PASS**;
- Ruff format: **PASS**;
- upstream CI Ruff selection: **PASS**;
- pytest: **NO LOCAL TESTS** (`exit 5`, no tests collected);
- external regression workflow references a moving reusable workflow and is not a reproducible pinned test gate.

### Frontend dependencies and checks

Use Node 22, not the host Node 26:

```bash
CYPRESS_INSTALL_BINARY=0 npm ci
npm run check
./node_modules/.bin/eslint .
npm run test:frontend -- --run
npm run build
node --max-old-space-size=6144 node_modules/vite/bin/vite.js build
```

Results:

- `npm ci`: **PASS** with Cypress binary disabled;
- Vitest: **PASS** (`1` test file, `4` tests);
- direct Vite build with 6 GiB heap: **PASS** (`5706` files, `build/index.html`);
- upstream `npm run build`: **FAIL** in the 12 GiB Docker allocation because the script hardcodes a 12 GiB Node heap and was OOM-killed;
- `npm run check`: **FAIL** (`5722` errors, `191` warnings);
- non-mutating ESLint: **FAIL** because `@typescript-eslint/no-unused-vars` crashed on `ModelDefaultsPanel.svelte`;
- browser/E2E: **NOT RUN**.

Evidence: `evidence/t00/openwebui-toolchain.md`.

### External migration owner and runtime

External migrator profile:

```bash
ENABLE_DB_MIGRATIONS=False
DATABASE_SCHEMA=openwebui
uv run alembic upgrade head
uv run alembic current
```

Runtime profile:

```bash
ENABLE_DB_MIGRATIONS=False
DATABASE_SCHEMA=openwebui
VECTOR_DB=pgvector
uv run uvicorn open_webui.main:app --host 127.0.0.1 --port 3100
```

Results:

- 51 upstream tables created;
- Alembic head `e42c8f710a36`;
- `/api/config` returned version `0.13.0`;
- runtime role could read upstream tables;
- runtime role could not create tables in the upstream schema;
- `document_chunk` is owned by the runtime/index role in the dedicated vector schema;
- upstream `alembic_version` is owned by the migrator role.

Evidence: `evidence/t00/openwebui-toolchain.md`.

## 4. Capability summary

| Capability | Result | Evidence |
|---|---|---|
| GitLab MR/proposal, merge commit, protected branch, tags, notes, export, cutover, webhooks | **42 completed probes; nonconforming target-race observed** | `evidence/t00/gitlab-capabilities.md` |
| GitLab CE-only merge profile | **PASS with owner decision** | CE cannot assign per-user protected branch grants; use role-based Maintainer-only GO |
| GitLab target-branch CAS | **ADAPTER REQUIRED** | GitLab has no atomic target HEAD precondition; GO serialization + durable barrier are mandatory |
| GitLab privileged admin bypass | **G0 DECISION** | Instance/project Owners can bypass GO; reconciliation and admin governance are required |
| Stable identity, revocation adapter and path-scoped approval policy | **PASS adapter/policy feasibility** | Keycloak adapter checks 9/9; approval policy 14/14 |
| Stock Open WebUI LDAP/OIDC as ADR-010 implementation | **ADAPTER REQUIRED** | Email/provider-alias identity, no nested AD closure, stale empty groups |
| Stock Open WebUI OIDC as ADR-010 implementation | **FAIL / ADAPTER REQUIRED** | Login/session/group sync works; issuer namespace and missing-group revocation fail |
| Tool execution capability boundary | **ADAPTER REQUIRED** | Stock arbitrary Python and multi-channel execution are not deny-by-default |
| Stock tool approval as business approval | **NOT ACCEPTABLE** | Same-owner approval has no independent approver/evidence; platform review + GO DecisionRecord is required |
| Personal Notes and ordinary chats | **PASS 8/8** | `evidence/t00/notes-chats-regression.md` |
| PostgreSQL role/schema separation and recovery barrier semantics | **PARTIAL PASS** | Synthetic schemas/denials and six recovery checks passed; full product migration matrix/HA drills remain pending |
| External migration ownership | **PASS** | External migrator reached head `e42c8f710a36`; runtime DDL denied |
| pgvector Russian/ACL synthetic retrieval | **PASS 22/22 deterministic gates** | `evidence/t00/retrieval-benchmark.md` |
| Production retrieval quality | **UNKNOWN** | Owner thresholds and production corpus are not yet selected |
| Editor canonical fidelity | **G0 DECISION** | CodeMirror preserves bytes but has no WYSIWYG; current TipTap path normalizes/loses constructs |
| Browser editor UX, IME, accessibility, XSS, full managed preview | **DEFERRED to T04; not PASS** | TipTap adapter selected at G0-D8; browser checks were not executed. Realtime CRDT is outside MVP, not a blocked T00 requirement |
| CI exact-SHA execution | **PASS 7/7** | `evidence/t00/ci-runner.md` |
| hoster.ai endpoint/models | **UNKNOWN / deferred** | No endpoint or model ID was provided for T00 |
| License/branding | **G0 LEGAL DECISION** | Current license is BSD-3-Clause plus branding restriction; managed distribution requires owner/legal review |

Full matrix: `evidence/t00/capability-matrix.md`.

## 5. Important upstream source findings

Paths below are relative to the pinned Open WebUI checkout.

### Identity and sessions

- Empty LDAP password is rejected before bind: `backend/open_webui/routers/auths.py:412-428`.
- LDAP supports implicit LDAPS and read-only bind/search; StartTLS is absent: `backend/open_webui/routers/auths.py:436-473`.
- LDAP attributes do not include objectGUID/entryUUID: `backend/open_webui/routers/auths.py:475-487`.
- LDAP account linking uses email: `backend/open_webui/routers/auths.py:586-597`.
- OIDC persistence uses provider alias + `sub`, not issuer + `sub`: `backend/open_webui/models/users.py:450-469`.
- Empty LDAP/OIDC group sets do not revoke prior memberships: `backend/open_webui/routers/auths.py:631-639`, `backend/open_webui/utils/oauth.py:1803-1819`.
- SCIM external ID is a useful seam but not integrated with LDAP/OIDC JIT: `backend/open_webui/models/users.py:471-482`.

### Tools and approval

- Saved Tool code is executed with server-process Python `exec`: `backend/open_webui/utils/plugin.py:208-250`.
- Tool Creation is exposed as a built-in: `backend/open_webui/tools/builtin.py:3870-3908`.
- Additive group permissions use `True > False` and have no deny/veto: `backend/open_webui/utils/access_control/__init__.py:32-44`.
- AccessGrant has `read`/`write`, not action capabilities: `backend/open_webui/models/access_grants.py:23-42`.
- Automations/channels force full tool approval mode: `backend/open_webui/main.py:1240-1250`.
- Stock approval is same-chat-owner and lacks independent approver/hash/evidence: `backend/open_webui/utils/tool_approval.py:80-125`.
- Native and legacy tool execution have separate paths: `backend/open_webui/utils/middleware.py:3092-3184`, `backend/open_webui/utils/middleware.py:1102-1144`.

### Migrations and data ownership

- Import-time startup migration is enabled by default and is not safe as a multi-worker migration owner: `backend/open_webui/config.py:63-81`, `backend/start.sh:94-110`.
- Online migration supports schema guards: `backend/open_webui/migrations/env.py:75-106`.
- ACL migration can log/skip malformed inserts before dropping source columns: `backend/open_webui/migrations/versions/f1e2d3c4b5a6_add_access_grant_table.py:132-143`, `backend/open_webui/migrations/versions/f1e2d3c4b5a6_add_access_grant_table.py:188-223`.
- Duplicate normalized emails fail a migration and include emails in an error; evidence must be sanitized: `backend/open_webui/migrations/versions/f0bd01a18a3d_add_unique_normalized_user_email_index.py:59-75`.

### Editor and retrieval

- Notes serializes TipTap JSON to HTML and Turndown Markdown, not canonical raw Markdown: `src/lib/components/common/RichTextInput.svelte:433-460`.
- Notes page revisions are mutable projections, not Git SHAs: `backend/open_webui/models/notes.py:349-374`.
- Existing CodeMirror editor, preview and diff components are reusable: `src/lib/components/chat/FileNav/FileCodeEditor.svelte:136-211`, `src/lib/components/workspace/Skills/SkillFiles.svelte:217-249`, `src/lib/components/common/DiffEditorModal.svelte:51-81`.
- Existing front-matter parser is in the Skills path, not Notes: `src/lib/utils/index.ts:2469-2478`, `backend/open_webui/utils/skill_files.py:60-82`.
- pgvector supports PostgreSQL DSN, ANN, FTS and hybrid search: `backend/open_webui/retrieval/vector/dbs/pgvector.py:151-225`, `backend/open_webui/retrieval/vector/dbs/pgvector.py:598-638`.
- Native hybrid falls back to generic full-collection BM25 when metadata filters are used: `backend/open_webui/retrieval/vector/dbs/pgvector.py:579-589`, `backend/open_webui/retrieval/utils.py:504-563`.
- Embedding dimensions are padded/truncated by storage config; model/profile changes require a new index profile: `backend/open_webui/retrieval/vector/dbs/pgvector.py:315-333`.

## 6. Design deltas required by baseline

### Identity adapter is mandatory

Stock LDAP/OIDC JIT must not be treated as the ADR-010 implementation. The identity/AuthZ adapter must own:

- stable `(issuer, sub)` or `(directory, objectGUID/entryUUID)` mapping;
- duplicate/ambiguous identity rejection;
- nested group closure;
- managed-vs-personal membership ownership;
- empty group revocation;
- epoch-matched policy/group snapshots;
- fail-closed AuthzContext.

Synthetic Keycloak adapter evidence passed 9/9. Stock Open WebUI OIDC login works and persists sessions/users, but it confirms two security gaps: provider alias is stored instead of issuer+sub, and a missing groups claim leaves stale membership. The external identity/AuthZ adapter is therefore mandatory; production AD/LDAP interoperability remains a later integration check.

### Tool execution boundary is mandatory

Corporate deployment must not expose arbitrary Python Tools or Tool Creation. Capability enforcement must be deny-by-default and must cover both native and legacy execution paths, deferred `call_tool`, browser/direct tools, OpenAPI, MCP, automations, channels and subagents. The first slice exposes only read/search/propose.

### External migration ownership is mandatory

Runtime workers run with `ENABLE_DB_MIGRATIONS=False` and non-DDL roles. A single migrator performs upgrades, verifies head `e42c8f710a36`, runs pre/post data-copy checks and proves rollback before enabling traffic.

### GitLab CE profile is viable with explicit constraints

The verified CE profile is:

- `push_access_level=0`;
- `merge_access_level=40`;
- only GO is Maintainer;
- unprotect access is Administrator-level;
- protected decision tags `kb-decisions/*` are created only by GO;
- no per-user protected branch grants from CE are used.

Privileged GitLab admins/Owners remain a break-glass risk. Owner approved this only with restricted privileged accounts, audit and out-of-band reconciliation (G0-D3); absolute merge-only-GO for admins is not claimed.

### Retrieval baseline is viable as a candidate

pgvector passed synthetic deterministic ACL/revision/ANN gates. Final production model, chunking, Russian quality thresholds, latency, reranking and hoster embeddings remain open.

### Editor direction approved: TipTap adapter

Owner selected the **TipTap adapter** at G0-D8. It preserves WYSIWYG editing and must provide canonical serializer, front-matter boundary, immutable attachment metadata, full source diff and browser/IME/accessibility/XSS gates in T04. Browser validation is an approved deferral (G0-D15), not a PASS. Realtime collaboration/CRDT is outside MVP; concurrent authors require conflict detection, exact/fresh revisions, full diff and a new ProposalVersion.

Measured baseline:

- CodeMirror-first preserves canonical bytes, front matter, Cyrillic and attachment metadata in headless round-trip/diff checks, but headless preview failed for Cyrillic links; it is not WYSIWYG and has no collaboration.
- Current TipTap Notes path preserves UTF-8 but normalizes/loses canonical constructs; table alignment and immutable attachment references were lost without an adapter.
- Browser rendering, IME, accessibility, XSS-safe preview and full managed preview were not executed; realtime multi-client collaboration/CRDT is outside MVP and is not a pending T00/T04 requirement.

Owner selected **TipTap adapter** at G0-D8; CodeMirror and hybrid remain rejected alternatives for this baseline. The adapter still requires browser evidence in T04, and no editor/UI PASS is claimed.

## 7. Evidence index

| Evidence | Result |
|---|---|
| `evidence/t00/environment.md` | Pinned host/tool/component versions |
| `evidence/t00/gitlab-capabilities.md` | GitLab 42 completed probes with explicit CE/admin constraints |
| `evidence/t00/identity-capabilities.md` | Keycloak adapter 9/9 PASS; upstream gaps remain |
| `evidence/t00/retrieval-benchmark.md` | pgvector deterministic gates 22/22 PASS |
| `evidence/t00/openwebui-auth-audit.md` | Static auth/tool/migration seam and STOP findings |
| `evidence/t00/openwebui-rag-editor-audit.md` | Retrieval/editor source seams and measured fidelity |
| `evidence/t00/openwebui-toolchain.md` | Runtime install/build/test/migration evidence |
| `evidence/t00/openwebui-oidc-runtime.md` | Stock OIDC login PASS; issuer+sub and stale group revocation FAIL as expected gaps |
| `evidence/t00/openwebui-license-review.md` | License/branding obligations and legal questions |
| `evidence/t00/independent-review.md` | Final independent review: 18 checks and 15/15 raw hashes verified |
| `evidence/t00/manifest.json` | Uniform check IDs, commands, statuses, raw hashes and sanitized links |
| `evidence/t00/capability-matrix.md` | Cross-cutting status matrix |
| `repository-provisioning.md` | Repository-per-Space namespace and creation-order proposal |
| `delivery-estimates.md` | LOW/VERY LOW confidence capacity scenarios for the first two delivery sprints |

Raw machine-generated artifacts remain under `_bmad-output/test-artifacts/t00/` and are intentionally not committed.

## 8. Deferred follow-up after T00 closure and G0 approval

T00 is DONE and G0 is APPROVED. The following remain mandatory follow-up work and are not PASS:

1. Apply the approved GitLab admin/Owner governance controls in deployment and prove out-of-band reconciliation (G0-D3 follow-up).
2. Preserve Open WebUI branding and complete owner/legal clearance before commercial distribution or white-label (G0-D10 follow-up).
3. Implement the approved TipTap adapter and execute browser/IME/accessibility/XSS gates in T04 (G0-D8/D15).
4. Re-run object-store ACL against the production engine in T13/T16; LocalStack ACL remains FAIL (G0-D16).
5. Provide real hoster.ai endpoints/model IDs and production quality thresholds in T11 (G0-D11).
6. **Completed 2026-11-08:** explicit owner approval of the complete baseline and ADR package was recorded in `g0-review.md` (G0-D12 APPROVED); downstream implementation/integration gates remain open.

## 9. Baseline conclusion

The local baseline demonstrates that the proposed Git-native platform is technically feasible with the selected versions, provided that the documented adapters and operational controls are mandatory rather than optional. The most significant changes from the original optimistic assumptions are:

- stock Open WebUI identity/tool approval is not sufficient;
- migrations must be externally owned;
- GitLab CE uses role-based merge isolation and still has privileged admin bypass;
- GitLab does not provide target-branch CAS;
- TipTap editor direction is owner-approved, while its canonical adapter/browser evidence and license legal clearance remain follow-up;
- upstream frontend typecheck/lint debt is material and must not be hidden.

CI/OIDC runtime checks and sanitized evidence collection are complete, and the independent review passed all 18 manifest checks with 15/15 raw hashes. **T00 is DONE and G0 is APPROVED.** Deferred gates remain mandatory follow-up work and are not claimed as PASS.
