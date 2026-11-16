"""kb-ingestion does not own a PostgreSQL product schema (ADR-015).

Durable source-sync jobs and cursors belong in Git Orchestrator ``kb_ops``.
This package exists so KBI-902 can point at a migrations root without
shipping Alembic revisions or expanding tables.
"""

PRODUCT_SCHEMA_OWNED_BY = "kb_ops"
ALEMBIC_VERSIONS: tuple[str, ...] = ()
