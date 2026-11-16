# kb-ingestion pytest (sanitized)

Command: `uv run pytest -q src/kb-ingestion/tests`

Result: **211 passed**, 1 warning (Starlette TestClient deprecation).

Backup after shared hash helper: `uv run pytest -q src/backup/tests` → **60 passed**, 1 skipped.

Ruff: `uv run ruff check src/kb-ingestion src/shared/object_store src/backup/app/adapters/object_store.py src/run_service.py scripts/local_stack.py scripts/smoke_local_stack.py` → clean.

Environment: local workspace, synthetic fixtures, no production secrets.

Live MinIO/Identity/GO/GitLab/local_stack HTTP: **BLOCKED**, not PASS.

Status: **VERIFIED(synthetic)**.
