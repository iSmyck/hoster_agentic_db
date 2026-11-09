# Implementation Phase Plan

## Goal

Move from contract/test harnesses to real application code for the Corporate Agentic Knowledge Platform.

## Decisions (owner-confirmed)

1. **Repository layout:** `src/` with subfolders per service.
2. **First component:** Identity + AuthZ adapter (`src/identity/`).
3. **Local infrastructure:** Docker Compose with PostgreSQL/pgvector, GitLab CE, Keycloak, MinIO.
4. **Sprint 0 goal:** Identity MVP — stable identity, group snapshots, policy activation, AuthzContext.
5. **Open WebUI fork:** embedded into `src/open-webui/` later, after backend services are bootstrapped.

## Proposed `src/` layout

```
src/
  identity/          # Identity + AuthZ adapter (Python/FastAPI)
  git-orchestrator/  # Git Orchestrator (Python/FastAPI)
  retrieval/         # Retrieval + indexing adapter
  ingestion/         # Ingestion + source connectors
  open-webui/        # Open WebUI fork v0.13.0 (future)
  contracts/         # Shared Pydantic models, JSON schemas, events
  docker/            # Dockerfiles and local dev scripts
```

## Sprint 0: Identity + AuthZ MVP

### Scope

- PostgreSQL `kb_authz` schema with tables:
  - `identities` (stable identity keys)
  - `group_snapshots` (nested groups, epochs)
  - `policy_bundles` (per-Space policies, valid_until, activation epoch)
  - `authz_contexts` (computed per-Space context, cached)
  - `revocations` (revocation barrier)
- FastAPI service exposing:
  - `POST /api/kb/v1/identity/resolve` — resolve actor to stable identity
  - `POST /api/kb/v1/authz/context` — compute AuthzContext for Space
  - `POST /api/kb/v1/authz/check` — check path approval
  - `POST /api/kb/v1/groups/snapshot` — ingest group snapshot
  - `POST /api/kb/v1/policies/activate` — activate policy bundle
- Pydantic models matching `specs/corporate-kb/contracts/authz-v2.schema.json`.
- Alembic migrations under `src/identity/migrations/`.
- Unit tests + contract tests against existing T03a/T03b harness fixtures.
- Docker Compose service `identity`.

### Out of scope

- Live Keycloak/LDAP integration (adapter interface only; concrete adapters BLOCKED).
- GO integration.
- Open WebUI fork.
- Retrieval/ingestion.

## Acceptance criteria for Sprint 0

1. `docker compose up -d postgres` brings up `kb_authz` database.
2. `uv run alembic upgrade head` applies identity migrations.
3. `uv run pytest -q src/identity/tests` passes.
4. Existing T03a/T03b harness fixtures are reused as contract test inputs.
5. Service health check responds at `/health`.

## Next sprints (draft)

- Sprint 1: Git Orchestrator skeleton + GitLab client + canonical read.
- Sprint 2: Open WebUI fork setup + `/api/kb/v1` client seams.
- Sprint 3: Retrieval + indexing adapter MVP.
- Sprint 4: Ingestion + source connector MVP.
