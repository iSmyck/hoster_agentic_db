"""Idempotent helper to create the kb_sessions schema and tables.

Useful in tests and local dev before running the service. Production
migrations should use Alembic.
"""

from __future__ import annotations

from session.app.repositories.db import init_db


def main() -> None:
    init_db()
    print("kb_sessions schema/tables created or already present")


if __name__ == "__main__":
    main()
