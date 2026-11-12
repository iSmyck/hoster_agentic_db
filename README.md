# Corporate Agentic Knowledge Base

A Git-native, policy-enforced corporate knowledge platform built around Open WebUI, GitLab, Keycloak, and PostgreSQL/pgvector. Documents live as Markdown in GitLab; identity and approval workflows are enforced by a dedicated Git Orchestrator; semantic search is provided by a Retrieval service backed by pgvector and KIMI embeddings.

This repository contains the source code, deployment overlays, operational runbooks, and acceptance evidence for the **G1 vertical slice** and **Phase B / Phase E minimal-production readiness** work.

---

## Project status

- **Overall readiness:** 90 %
- **G1 vertical slice:** DONE
- **Phase B Identity/Retrieval live integration:** DONE
- **Phase D Backup/restore:** VERIFIED
- **Phase C Ingestion/source connectors:** backlog (Git-only source approved)
- **Phase E Production hardening:** minimal target complete; HA/AD/SLO/deep pen-test deferred

For the authoritative task and gate status, see [`_bmad-output/implementation-artifacts/sprint-status.yaml`](_bmad-output/implementation-artifacts/sprint-status.yaml).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Open WebUI (overlay)                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  /kb editor     │  │  TipTap editor  │  │  White-label build step     │  │
│  │  (SvelteKit)    │  │  + Markdown     │  │  (env-driven assets)        │  │
│  └────────┬────────┘  └─────────────────┘  └─────────────────────────────┘  │
│           │ OIDC token                                                       │
└───────────┼──────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service layer (Python/FastAPI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Identity     │  │ Git          │  │ Retrieval    │  │ Session      │    │
│  │ + AuthZ      │  │ Orchestrator │  │ + Indexing   │  │ Service      │    │
│  │ :8001        │  │ :8002        │  │ :8003        │  │ :8004        │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Data / infrastructure layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Keycloak     │  │ GitLab CE    │  │ PostgreSQL   │  │ MinIO        │    │
│  │ OIDC / realm │  │ Repo=Space   │  │ + pgvector   │  │ object store │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core components

| Component | Directory | Purpose |
|-----------|-----------|---------|
| **Identity + AuthZ** | `src/identity/` | Resolves stable identities, groups, and per-Space access policies from Keycloak/OIDC tokens. |
| **Git Orchestrator (GO)** | `src/git-orchestrator/` | Owns canonical writes: proposals, decisions, merge-only enforcement, decision tags, idempotency, and merge recovery. |
| **Retrieval + Indexing** | `src/retrieval/` | Builds searchable indexes from Git snapshots; performs ACL-aware semantic/exact/hybrid search via pgvector. |
| **Session Service** | `src/session/` | Issues and validates session JWTs; falls back to OIDC introspection for Keycloak-issued tokens. |
| **Backup/Restore** | `src/backup/` | Git mirror, metadata backup, PostgreSQL dump, object-store backup, and point-in-time restore. |
| **Open WebUI Overlay** | `src/open-webui/` | SvelteKit overlay adding the `/kb` route, TipTap editor, white-label build step, and typed KB API client. |

---

## Key features

- **Git-native canonical storage.** Every Space is a GitLab repository; every document is Markdown with YAML front matter. Full commit SHAs are revisions.
- **Merge-only governance.** No direct writes to `main`. Changes go through proposal → review → DecisionRecord → merge, with exact parent/trailer verification and protected decision tags.
- **OIDC/Keycloak unified token seam.** Open WebUI sends Keycloak access tokens to GO, Session, and Identity endpoints; the session service introspects them via the identity adapter.
- **ACL-aware retrieval.** Search results are filtered per-path by the identity service before delivery. Unauthorized documents are never returned.
- **pgvector + KIMI embeddings.** The retrieval service uses `text-embedding-v2` (1024d) for semantic search. A live benchmark against PostgreSQL/pgvector passed (ACT-006).
- **Lossless TipTap editor.** The `/kb` editor uses TipTap + a custom Markdown serializer (no `marked`/`turndown` round-trip). DOMPurify sanitizes preview HTML; a11y attributes and IME composition handling are included.
- **White-label build step.** An opt-in `kb:build:white-label` script accepts logo/favicon/splash paths via env vars and injects CSS overrides at build time while preserving Open WebUI attribution.
- **Operational runbooks.** Incident response, rollback/recovery, privileged-bypass governance, security review, monitoring, and backup/retention are documented and versioned.

---

## Quick start

### Prerequisites

- Python 3.12+
- `uv` (Python package manager)
- Node.js 20+ and npm
- Docker and Docker Compose
- Git

### 1. Clone and configure

```bash
git clone <repository-url>
cd corp_ai_db
cp .env.example .env
# Edit .env and set GITLAB_TOKEN, KEYCLOAK_CLIENT_SECRET, KIMI_API_KEY, etc.
```

### 2. Install dependencies

```bash
uv sync
```

```bash
cd src/open-webui
npm install
./setup-openwebui.sh   # clones the pinned upstream Open WebUI checkout
```

### 3. Start the local development stack

```bash
cd <project-root>
python scripts/local_stack.py start
```

This starts PostgreSQL, MinIO, Keycloak, GitLab CE, the backend services, and Open WebUI on port 3100.

### 4. Verify the stack

```bash
python scripts/smoke_local_stack.py
```

### 5. Stop the stack

```bash
python scripts/local_stack.py stop
```

---

## Service ports (local stack)

| Service | Port | Description |
|---------|------|-------------|
| Identity + AuthZ | 8001 | Identity resolution and path-level authorization |
| Git Orchestrator | 8002 | Proposal/decision/merge lifecycle |
| Retrieval | 8003 | Index build and semantic search |
| Session | 8004 | Session JWT issuance/validation |
| Open WebUI | 3100 | Custom `/kb` route included |
| PostgreSQL | 5432 | `corp_kb` database |
| MinIO | 9000 | Object-store staging |
| Keycloak | 8082 | `corp-kb` realm |
| GitLab CE | 8081 | Sandbox GitLab |

---

## Running tests

### Backend

```bash
uv run pytest src/git-orchestrator/tests -q
uv run pytest src/identity/tests -q
uv run pytest src/session/tests -q
uv run pytest src/retrieval/tests -q
uv run pytest src/backup/tests -q
```

### Frontend overlay

```bash
cd src/open-webui
npm run kb:test
```

### Live acceptance (optional)

Requires the local stack and an explicit destructive-reset guard:

```bash
export G1_ALLOW_DESTRUCTIVE_RESET=1
uv run python _bmad-output/test-artifacts/g1/run_g1_live_acceptance.py
uv run python _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py
```

---

## Building the frontend

### Default build

```bash
cd src/open-webui
npm run kb:build
```

### White-label build

White-label assets and final legal clearance are pending, but the build step is ready:

```bash
cd src/open-webui
cp .white-label-env.example .white-label-env
# Edit .white-label-env with real asset paths
source .white-label-env
WHITE_LABEL_LEGAL_CLEARANCE=1 npm run kb:build:white-label
```

The default build keeps standard Open WebUI branding with `WEBUI_NAME` customization only.

---

## Deployment

### Minimal production target (owner-approved)

- Single-node PostgreSQL with daily backups.
- Basic hoster-provided monitoring.
- Markdown runbooks versioned in this repository.
- KIMI as the inference provider; hoster.ai integration deferred.
- Git-managed Spaces plus manual uploads as the only content source.

For step-by-step handover instructions, see [`DEPLOYMENT.md`](DEPLOYMENT.md).

### Operational runbooks

| Runbook | Purpose |
|---------|---------|
| `specs/corporate-kb/runbooks/incident-response.md` | Outage triage, escalation, rollback, communication |
| `specs/corporate-kb/runbooks/rollback-and-recovery.md` | Git/PostgreSQL/object-store recovery |
| `specs/corporate-kb/runbooks/privileged-bypass-governance.md` | Emergency approval overrides and audit |
| `specs/corporate-kb/runbooks/security-review-checklist.md` | Per-release security gate |
| `specs/corporate-kb/runbooks/monitoring-alerting-checklist.md` | Metrics, thresholds, on-call references |
| `specs/corporate-kb/runbooks/backup-and-retention.md` | Schedule, retention, encryption, restore drills |

---

## Blocked gates before full production launch

The remaining 10 % requires external owner/hoster input:

- **T13/T16** — object-store ACL production engine recheck.
- **Production AD / live SLO** — production IdP integration.
- **HA / cross-site DR** — deferred to post-launch.
- **External penetration test** — not performed for the minimal target.
- **Real white-label assets** — build config ready, assets pending.

See [`specs/corporate-kb/evidence/release-readiness-checklist.md`](specs/corporate-kb/evidence/release-readiness-checklist.md) for go/no-go criteria.

---

## Repository structure

```
├── src/
│   ├── identity/              # Identity + AuthZ service
│   ├── git-orchestrator/      # Git Orchestrator service
│   ├── retrieval/             # Retrieval + Indexing service
│   ├── session/               # Session service
│   ├── backup/                # Backup/restore service
│   └── open-webui/            # Frontend overlay
├── scripts/
│   ├── local_stack.py         # Local Docker stack orchestration
│   └── smoke_local_stack.py   # Local stack smoke tests
├── specs/corporate-kb/
│   ├── architecture.md        # System architecture
│   ├── adr/                   # Architecture Decision Records
│   ├── runbooks/              # Operational runbooks
│   ├── evidence/              # Acceptance evidence
│   └── owner-input-request.md # Recorded owner decisions
├── _bmad-output/
│   ├── implementation-artifacts/sprint-status.yaml
│   └── test-artifacts/        # Machine-generated test output
├── .env.example               # Local configuration template
├── DEPLOYMENT.md              # Detailed handover instructions
└── README.md                  # This file
```

---

## Documentation map

- **Architecture:** `specs/corporate-kb/architecture.md`
- **ADRs:** `specs/corporate-kb/adr/`
- **Runbooks:** `specs/corporate-kb/runbooks/`
- **Release readiness:** `specs/corporate-kb/evidence/release-readiness-checklist.md`
- **Owner decisions:** `specs/corporate-kb/owner-input-request.md`
- **Sprint retrospective:** `specs/corporate-kb/evidence/sprint-retrospective-2026-11-12.md`
- **Deployment handover:** `DEPLOYMENT.md`

---

## Known approved debt

- Upstream `svelte-check` and ESLint are known-fail approved debt (G0-D9); use the direct Vite build and Vitest as gates.
- Full A01–A36 live destructive acceptance and live browser IME/a11y/XSS gates are environment-gated and deferred to Phase E.

---

## License

This project is an overlay/integration layer around Open WebUI v0.13.0. Refer to the upstream Open WebUI LICENSE for branding restrictions. The white-label build step preserves attribution and requires explicit legal clearance.
