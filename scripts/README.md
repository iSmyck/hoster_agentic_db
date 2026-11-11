# Local development stack

This directory contains scripts to run the full corp-ai-db G1 vertical slice on a local machine for development and integration testing.

## What runs

**Infrastructure (Docker Compose):**
- PostgreSQL 18 + pgvector (`localhost:5432`)
- GitLab CE 19.5.3 (`localhost:8081`) — present but not required; GO runs with stub GitLab adapter by default.
- S3Mock (`localhost:9000`) — S3-compatible mock; replaces MinIO because MinIO images now require authenticated pull.
- Keycloak (`localhost:8082`) — present but not required; Identity service runs in stub mode by default.

**App services (host, via `uv`):**
- Identity + AuthZ service (`http://127.0.0.1:8001`) — `IDENTITY_ADAPTER=stub`
- Session service (`http://127.0.0.1:8004`)
- Git Orchestrator (`http://127.0.0.1:8002`) — `GO_GITLAB_ADAPTER=stub` by default
- Retrieval service (`http://127.0.0.1:8003`) — `GO_CLIENT_MODE=stub`
- Backup service (`http://127.0.0.1:8005`) — optional
- Open WebUI (`http://127.0.0.1:3100`) — from the pinned upstream checkout; auth disabled only on fresh starts with no existing users

## Quick start

1. Copy environment defaults:
   ```bash
   cp .env.example .env
   # Edit GITLAB_TOKEN and other values if needed.
   ```

2. Apply Open WebUI integration patches (needed for WYSIWYG Knowledge editor):
   ```bash
   cd _bmad-output/test-artifacts/t00/upstream/open-webui
   git apply ../../../../patches/open-webui-t04b-wysiwyg.patch
   npm run build
   cd -
   ```

3. Start the stack:
   ```bash
   uv run python scripts/local_stack.py
   ```

4. In another terminal, run the smoke test:
   ```bash
   uv run python scripts/smoke_local_stack.py
   ```

5. Seed the knowledge collection and default assistant:
   ```bash
   uv run python scripts/seed_openwebui_kb.py
   ```
   This creates/updates the `corp-ai-db project docs` knowledge collection, builds a `hoster-assistant` custom model backed by KIMI, and sets it as the default model for new chats.

6. Create a new KB document draft (canonical path through GO):
   ```bash
   uv run python scripts/create_kb_document.py docs/runbook.md \
     --title "Runbook" --file runbook.md
   ```
   This issues a session token, saves a durable draft in GO, and (with `--propose`) attempts the proposal/MR path. In local dev with `GO_GITLAB_ADAPTER=stub` the proposal step needs a live GitLab project; the draft is saved regardless.

7. Open the editor:
   ```bash
   open http://127.0.0.1:3100
   ```

8. Stop the stack:
   ```bash
   uv run python scripts/local_stack.py --stop
   ```

## Skip Open WebUI

To start only the backend services (useful for headless API testing):

```bash
uv run python scripts/local_stack.py --no-openwebui
```

## What gets seeded

- `kb_ops.drafts` — sample drafts for `author-1` in `corp-kb/sales`.
- `StubGitLabAdapter` history — synthetic commits for `docs/g1-proposal.md`.
- Session service tokens — sessions for `author-1` and `approver-1`.
- Open WebUI Knowledge — `corp-ai-db project docs` collection from `specs/corporate-kb/**/*.md`.
- Open WebUI default model — `hoster-assistant` (KIMI base + attached project docs), pinned as the default chat model.

## Notes and limitations

- Identity service uses the stub adapter so the stack can start without Keycloak realm setup. Switch to `IDENTITY_ADAPTER=keycloak` after running `src/identity/scripts/setup_keycloak.py`.
- Git Orchestrator uses `GO_GITLAB_ADAPTER=stub` by default. Set `GO_GITLAB_ADAPTER=http` and provide `GO_GITLAB_TOKEN` for real GitLab integration.
- Retrieval service uses `GO_CLIENT_MODE=stub` to avoid requiring a live GitLab project. Set to `http` for real GitLab integration.
- Open WebUI authentication is disabled only when the `openwebui.user` table is empty. If users already exist, auth stays enabled. The GO service validates session-service tokens. For a fully seamless browser flow, configure a shared identity source (Keycloak/OIDC) or use the seeded session tokens in API tests.
- KIMI is configured via `KIMI_API_BASE_URL`/`KIMI_API_KEY`, which the orchestrator maps to Open WebUI's `OPENAI_API_*` vars with `ENABLE_DIRECT_CONNECTIONS=true`. Set `KB_BASE_MODEL_ID` to choose a different base model for the seeded default assistant.
- WYSIWYG editing of Markdown files in Open WebUI Knowledge is available via the `Source` / `Visual` toggle. It preserves front matter and links; list markers and paragraph spacing may be normalized because the first iteration uses a marked/turndown round-trip. A fully lossless serializer is tracked under T04b.
- The orchestrator sets `FRONTEND_BUILD_DIR` to the upstream checkout's `build` directory so the backend serves the result of `npm run build`.
- Open WebUI Knowledge is a read/test projection. New documents must enter the canonical Git-native lifecycle via the Git Orchestrator API (see `scripts/create_kb_document.py`).
- White-label logo/favicon replacement in Open WebUI is restricted by the upstream LICENSE and remains deferred (T18).
- Do not use these defaults or the hard-coded secrets in production.
