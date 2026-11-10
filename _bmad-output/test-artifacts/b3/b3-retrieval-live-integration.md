# B.3 Retrieval service live integration with identity ACL

**Status:** DONE  
**Date:** 2026-11-10  
**Baseline commit:** bc96a60  
**Spec:** `_bmad-output/implementation-artifacts/spec-b3-retrieval-live-integration.md`

## Summary

Connected the Retrieval service (port 8003) to the Identity service (port 8001)
on the local PostgreSQL/pgvector instance started by `docker-compose.yml`.
Verified end-to-end search with the real `HttpIdentityClient`, stub
deterministic embeddings, and a synthetic Git snapshot delivered by an in-memory
stub GO client.

## Changes made

- `src/retrieval/app/schemas/retrieval.py`
  - Added optional `cursor` field to `SearchRequest`.
- `src/retrieval/app/services/search.py`
  - Validate `cursor` against the active generation id/snapshot; return
    `STALE_SNAPSHOT` on mismatch.
- `src/retrieval/app/api/router.py`
  - Mapped `STALE_SNAPSHOT` to HTTP 409 and threaded `cursor` into the service.
- `src/retrieval/app/core/config.py`
  - Added `GO_CLIENT_MODE` (`http` | `stub`).
- `src/retrieval/app/adapters/go_client.py`
  - Added `SyntheticStubGOClient` and `build_synthetic_stub_go_client` that serve
    the same synthetic snapshot for any space id, keeping concurrent smoke and
    live-test runs isolated.
- `src/retrieval/app/main.py`
  - When `GO_CLIENT_MODE=stub`, wire the synthetic stub.
- `.env.example`
  - Added `RETRIEVAL_GO_CLIENT_MODE` and removed duplicate embedding-dimension
    line.
- `src/retrieval/scripts/smoke_retrieval.py` (new)
  - Live smoke: health checks, identity seeding, index build/activate,
    authorized/unauthorized search, stale cursor.
- `src/retrieval/tests/test_retrieval_live.py` (new)
  - Pytest live integration suite; skipped unless services are healthy or
    `RUN_LIVE_RETRIEVAL_TESTS=1` is set.

## Verification commands

```text
# Infrastructure (already running)
docker compose up -d postgres keycloak

# Identity service
PYTHONPATH=src uv run uvicorn identity.app.main:app --host 127.0.0.1 --port 8001

# Retrieval service with stub GO/embeddings for local smoke
PYTHONPATH=src \
  RETRIEVAL_GO_CLIENT_MODE=stub \
  RETRIEVAL_EMBEDDING_MODEL=stub-deterministic \
  RETRIEVAL_EMBEDDING_DIMENSIONS=384 \
  uv run uvicorn retrieval.app.main:app --host 127.0.0.1 --port 8003

# Smoke test
PYTHONPATH=src \
  RETRIEVAL_GO_CLIENT_MODE=stub \
  RETRIEVAL_EMBEDDING_MODEL=stub-deterministic \
  RETRIEVAL_EMBEDDING_DIMENSIONS=384 \
  uv run python src/retrieval/scripts/smoke_retrieval.py

# Live integration tests
PYTHONPATH=src RUN_LIVE_RETRIEVAL_TESTS=1 uv run pytest -q src/retrieval/tests/test_retrieval_live.py

# Full retrieval suite
PYTHONPATH=src uv run pytest -q src/retrieval/tests

# Lint
PYTHONPATH=src uv run ruff check src/retrieval
```

## Results

### Smoke test

```text
B.3 Retrieval live integration smoke test
  identity: http://localhost:8001
  retrieval: http://localhost:8003

1. Health checks
  identity: ok
  retrieval: ok

2. Seed Identity service
  group snapshot: ok
  policy bundle: ok

3. Build and activate index
  index build: 3 chunk(s) indexed
  pointer activated: fence_token=<incremented>

4. Authorized search (reader)
  results: {'docs/restricted.md', 'docs/public.md'}
  PASS

5. Unauthorized search (outsider)
  PASS

6. Stale cursor search
  PASS

All smoke checks passed.
```

### Live pytest

```text
....
4 passed
```

### Full retrieval suite

```text
............................................ssss
40 passed, 4 skipped
```

### Lint

```text
All checks passed!
```

## Evidence files

- `_bmad-output/test-artifacts/b3/smoke_retrieval.log`
- `_bmad-output/test-artifacts/b3/pytest_live.log`
- `_bmad-output/test-artifacts/b3/pytest_retrieval.log`

## Risks / incomplete

- The live integration uses the Identity service's `/api/kb/v1/authz/check`
  endpoint, which currently implements a path-approver check rather than a
  dedicated read/search ACL check. This matches the existing retrieval code but
  may need refinement when the AuthZ contract is hardened for search.
- GO client stub mode is intended for smoke/integration tests only; production
  deployments must use `GO_CLIENT_MODE=http` and a real Git Orchestrator.
- The cursor field accepts either the active generation id or the active
  snapshot SHA; cursor serialization/versioning is minimal and should evolve
  with the published-search contract.
- Live Identity service is running with `IDENTITY_ADAPTER=keycloak` from the
  local `.env`; the authz-check path exercised here does not call Keycloak, so
  full IdP integration remains a separate verification.
- Live tests now use a unique space id per import to avoid cross-run fence
  races; the stub GO client returns the synthetic fixture for any space.
