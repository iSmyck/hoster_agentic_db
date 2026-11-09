# Epic 12 Retrospective: Retrieval + indexing implementation

Date: 2026-11-09
Epic status: done
Story: 12-1 I08

## What went well

- `src/retrieval/` FastAPI service bootstrapped with SQLAlchemy 2.0, Alembic, Pydantic v2.
- `kb_index` schema and migrations for IndexGeneration, IndexPointer, Chunk, SearchLog with pgvector `Vector(384)`.
- Index worker builds from GO canonical snapshots via stub adapter.
- Semantic/exact/hybrid search with per-payload re-authorization via identity service.
- Fence/CAS pointer activation with row-level locking.
- Code review fixed cosine similarity normalization, embedding adapter error handling, chunk count mismatch, identity client error handling, query limits.
- 160 passed, 1 skipped.

## What needs improvement

- Real embedding model integration blocked; using deterministic stub.
- Semantic search on SQLite falls back to Python ranking; real performance unknown.

## Action items

- Integrate real embedding model (Ollama/hoster.ai) once endpoint available.
- Add vector-index performance tests on PostgreSQL/pgvector.
