# Deployment Handover

**Project:** corp_ai_db  
**Date:** 2026-11-12  
**Overall readiness:** 90 %  
**Target:** Minimal production launch under hoster.by white-label

## Repository layout

```
├── src/
│   ├── identity/          # Identity + AuthZ service (port 8001)
│   ├── git-orchestrator/  # Git Orchestrator service (port 8002)
│   ├── retrieval/         # Retrieval + Indexing service (port 8003)
│   ├── session/           # Session service (port 8004)
│   ├── backup/            # Backup/restore service
│   └── open-webui/        # Frontend overlay (port 3100)
├── scripts/
│   ├── local_stack.py     # Start/stop local Docker stack
│   └── smoke_local_stack.py
├── specs/corporate-kb/    # Specs, ADRs, runbooks, evidence
│   ├── runbooks/          # Operational runbooks
│   └── evidence/          # Acceptance evidence
├── _bmad-output/          # Generated test artifacts and sprint status
├── .env.example           # Local development configuration template
└── DEPLOYMENT.md          # This file
```

## Prerequisites

- Python 3.12+
- `uv` (Python package manager)
- Node.js 20+ and npm
- Docker and Docker Compose (for local stack)
- Git

## Initial setup

1. Clone the repository.
2. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

3. Fill in real values for:
   - `GITLAB_TOKEN` / `GO_GITLAB_TOKEN` (if using real GitLab)
   - `KEYCLOAK_CLIENT_SECRET`
   - `KIMI_API_KEY`
   - `MINIO_SECRET_KEY`
   - `SESSION_SECRET_KEY` (change in production)

4. Install Python dependencies:

   ```bash
   uv sync
   ```

5. Install frontend dependencies:

   ```bash
   cd src/open-webui
   npm install
   ./setup-openwebui.sh   # clones the pinned upstream Open WebUI checkout
   ```

## Local development stack

Start all services (PostgreSQL, MinIO, Keycloak, GitLab CE, Open WebUI):

```bash
python scripts/local_stack.py start
```

Run smoke tests:

```bash
python scripts/smoke_local_stack.py
```

Stop the stack:

```bash
python scripts/local_stack.py stop
```

> The local stack uses disposable fixtures. Do not use it for production data.

## Service ports

| Service | Port | Notes |
|---------|------|-------|
| Identity + AuthZ | 8001 | Keycloak-backed in local stack |
| Git Orchestrator | 8002 | GitLab adapter stub by default |
| Retrieval | 8003 | pgvector-backed in local stack |
| Session | 8004 | JWT + OIDC fallback |
| Open WebUI | 3100 | Custom `/kb` route included |
| PostgreSQL | 5432 | `corp_kb` database |
| MinIO | 9000 | Object-store staging |
| Keycloak | 8082 | `corp-kb` realm |
| GitLab CE | 8081 | Sandbox GitLab |

## Running tests

Backend:

```bash
uv run pytest src/git-orchestrator/tests -q
uv run pytest src/identity/tests -q
uv run pytest src/session/tests -q
uv run pytest src/retrieval/tests -q
uv run pytest src/backup/tests -q
```

Frontend overlay:

```bash
cd src/open-webui
npm run kb:test
```

Live acceptance (requires running local stack and `G1_ALLOW_DESTRUCTIVE_RESET=1`):

```bash
export G1_ALLOW_DESTRUCTIVE_RESET=1
uv run python _bmad-output/test-artifacts/g1/run_g1_live_acceptance.py
uv run python _bmad-output/test-artifacts/g1/run_openwebui_acceptance.py
```

## Building for deployment

Default build:

```bash
cd src/open-webui
npm run kb:build
```

White-label build (requires legal clearance and asset paths):

```bash
cd src/open-webui
cp .white-label-env.example .white-label-env
# edit .white-label-env with real asset paths
source .white-label-env
WHITE_LABEL_LEGAL_CLEARANCE=1 npm run kb:build:white-label
```

> White-label assets and final legal clearance are pending. The default build keeps standard Open WebUI branding with `WEBUI_NAME` customization only.

## Production deployment notes

- The minimal production target is owner-approved: single-node PostgreSQL, daily backups, basic hoster monitoring, repo runbooks.
- HA/DR, cross-site replication, and external penetration tests are deferred.
- KIMI remains the production inference provider; hoster.ai integration is deferred.
- External source connectors are deferred; the only canonical source is Git-managed Spaces plus manual uploads through `/kb`.

## Operational runbooks

See `specs/corporate-kb/runbooks/`:

- `incident-response.md`
- `rollback-and-recovery.md`
- `privileged-bypass-governance.md`
- `security-review-checklist.md`
- `monitoring-alerting-checklist.md`
- `backup-and-retention.md`

## Blocked gates for production launch

The following require owner/hoster/external input and cannot be resolved from the codebase alone:

- **T13/T16** — object-store ACL production engine recheck.
- **Production AD / live SLO** — production IdP integration.
- **HA / cross-site DR** — deferred to post-launch.
- **External penetration test** — not performed for the minimal target.
- **Real white-label assets** — build config ready, assets pending.

## Known approved debt

- Upstream `svelte-check` / ESLint are known-fail approved debt (G0-D9); use the direct Vite build and Vitest instead.
- Full A01–A36 live destructive acceptance and live browser IME/a11y/XSS gates are environment-gated and deferred.

## Support contacts

- Architecture / design: `specs/corporate-kb/architecture.md`, `specs/corporate-kb/adr/`
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Owner input decisions: `specs/corporate-kb/owner-input-request.md`
- Release readiness: `specs/corporate-kb/evidence/release-readiness-checklist.md`
