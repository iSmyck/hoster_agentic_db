# B.2 Session service — acceptance evidence

**Task:** B.2 Session service — identity-bound tokens for GO/Retrieval  
**Date:** 2026-11-10  
**Environment:** macOS, Python 3.12, PostgreSQL 18.6 (Docker), local `kb_sessions` schema

## Verification summary

| Criterion | Evidence | Result |
|-----------|----------|--------|
| Create session returns tokens + persists row | `test_session_live.py::TestCreateAndValidate` + smoke script | PASS |
| Validate access token returns stable_id + policy revisions | `test_session_service.py::TestValidateAccessToken` + smoke | PASS |
| Expired/revoked token returns 401 | `test_session_service.py` + `test_session_live.py` | PASS |
| Refresh issues new access token and invalidates old | `test_session_service.py::TestRefreshAccessToken` + smoke | PASS |
| GO protected route works with valid session Bearer | `src/git-orchestrator/tests` still pass | PASS |
| GO route with revoked token returns 401 | covered by Session service contract; GO integration live test BLOCKED by no running GO+Session stack in this run | PARTIAL |

## Commands

```bash
# Migrations
PYTHONPATH=src uv run alembic -c src/session/migrations/alembic.ini upgrade head

# Tests
PYTHONPATH=src uv run pytest -q src/session/tests
PYTHONPATH=src uv run pytest -q src/git-orchestrator/tests
PYTHONPATH=src uv run pytest -q

# Lint
PYTHONPATH=src uv run ruff check src/session src/git-orchestrator

# Live smoke
PYTHONPATH=src uv run uvicorn session.app.main:app --host 127.0.0.1 --port 8004
PYTHONPATH=src uv run python src/session/scripts/smoke_session.py
```

## Results

- Full suite: **250 passed**.
- Session tests: **18 passed**.
- GO tests: **44 passed**.
- Ruff: **clean**.
- Live smoke: **exit 0**.

## Incomplete / risky

- Live end-to-end GO → Session service → protected route was not exercised with
  both services running simultaneously; existing GO tests mock identity.
- Default `SESSION_SECRET_KEY` in code is a placeholder; production deployments
  must override it via `.env`.
- Role claim is not propagated from Session service to GO; approver authorization
  currently relies on `stable_id` allow-list.
