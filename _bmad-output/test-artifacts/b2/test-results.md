# B.2 Session service — test evidence

Generated: 2026-11-10

## Unit + integration tests

```text
PYTHONPATH=src uv run pytest -q
250 passed, 28 warnings in 8.00s
```

Session-only subset:

```text
PYTHONPATH=src uv run pytest -q src/session/tests
18 passed, 28 warnings in 0.23s
```

## Lint

```text
PYTHONPATH=src uv run ruff check src/session src/git-orchestrator
All checks passed!
```

## Live smoke test

Session service running on `127.0.0.1:8004` against the local PostgreSQL
instance (`corp_kb` database, `kb_sessions` schema).

```text
PYTHONPATH=src uv run python src/session/scripts/smoke_session.py
health ok
create ok
validate ok
refresh ok
logout ok
revoked token rejected ok
smoke session passed
```

## Migration

```text
PYTHONPATH=src uv run alembic -c src/session/migrations/alembic.ini upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, Initial kb_sessions tables.
```

## Notes

- All acceptance criteria in `spec-b2-session-service.md` are exercised by the
  unit/integration tests and the live smoke script.
- Git Orchestrator tests continue to pass because `get_current_identity` is
  mocked in the existing test fixtures; the production code now calls the
  Session service `/api/kb/v1/session/validate` endpoint.
