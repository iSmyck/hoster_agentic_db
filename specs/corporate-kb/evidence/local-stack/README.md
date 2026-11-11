# Local development stack evidence

**Status:** VERIFIED — local stack starts successfully and smoke tests pass against it.

## Latest run

- **Date:** 2026-11-10
- **Command:** `bash -c 'set -a && source .env.example && set +a && uv run python scripts/smoke_local_stack.py'`
- **Result:** 12 PASS, 0 FAIL, 1 BLOCKED (GitLab API health requires a token; stack uses `GO_GITLAB_ADAPTER=stub` by default)
- **Artifacts:** `_bmad-output/test-artifacts/local-stack/smoke-results.json`, `smoke-summary.md`
- **Open WebUI:** http://127.0.0.1:3100 returns 200. KIMI models are available. A test knowledge collection `corp-ai-db project docs` was seeded with 44 project markdown files via `scripts/seed_openwebui_kb.py`. A default knowledge-backed model `hoster-assistant` (KIMI base + attached project docs) was created and set as the default chat model. T04b WYSIWYG markdown editor is implemented in Knowledge file viewer (`Source` / `Visual` toggle); it preserves front matter and links, but list markers and paragraph spacing may be normalized on save. Document creation helper `scripts/create_kb_document.py` exercises the canonical GO draft/proposal path.

## Artifacts

- `.env.example` — unified local environment variables (stub adapters by default).
- `docker-compose.yml` — PostgreSQL, GitLab CE, S3Mock (replaces MinIO for local dev), Keycloak infrastructure.
- `scripts/local_stack.py` — starts infra, runs migrations, seeds data, launches app services and Open WebUI.
- `scripts/smoke_local_stack.py` — health checks and GO draft/history/session smoke tests.
- `scripts/seed_openwebui_kb.py` — seeds Open WebUI Knowledge and the default knowledge-backed model.
- `scripts/create_kb_document.py` — creates a KB document draft (and optionally proposal) through the Git Orchestrator API.
- `scripts/README.md` — runbook.
- `_bmad-output/test-artifacts/t00/upstream/open-webui/src/lib/components/workspace/Knowledge/KnowledgeBase/FileViewer.svelte` — WYSIWYG visual editor integration for Markdown files.

## How to run

```bash
cp .env.example .env
# Start the stack
uv run python scripts/local_stack.py
# In another terminal
uv run python scripts/smoke_local_stack.py
```

## Smoke test coverage

- Health checks for identity, session, GO, retrieval, backup, Open WebUI, GitLab.
- Session service create/validate for `author-1`.
- GO draft save/get and history endpoints using the session token.
- Open WebUI `/kb` page reachability.

## Notes

- Identity service starts in `stub` mode by default to avoid Keycloak realm setup.
- Git Orchestrator uses `GO_GITLAB_ADAPTER=stub` by default for local dev; live GitLab integration requires a token and `GO_GITLAB_ADAPTER=http`.
- Retrieval service starts with `GO_CLIENT_MODE=stub` to avoid requiring a live GitLab project.
- S3Mock (`adobe/s3mock:3.12.0`) replaces MinIO in `docker-compose.yml` because MinIO images require authenticated pull; S3Mock provides S3-compatible APIs sufficient for local development.
- Open WebUI authentication is disabled (`WEBUI_AUTH=false`) only for fresh local dev starts with no existing users. If users already exist, auth stays enabled and the first signed-up user becomes admin. GO uses session-service tokens. A shared OIDC/Keycloak configuration is a future integration step.
