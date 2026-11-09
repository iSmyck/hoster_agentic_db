"""Alembic migration smoke test against a real PostgreSQL server.

Falls back to ``pytest.skip`` when no PostgreSQL test server is available so
SQLite-only runs still pass.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from typing import Any

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

DEFAULT_PG_ADMIN_URL = "postgresql://corp_kb:corp_kb_dev@localhost:5432/postgres"


def _pg_admin_url() -> str:
    return os.environ.get("IDENTITY_PG_ADMIN_URL", DEFAULT_PG_ADMIN_URL)


def _test_db_url(admin_url: str, db_name: str) -> str:
    # Replace the last path component (database name) while preserving driver.
    base = admin_url.rsplit("/", 1)[0]
    return f"{base}/{db_name}"


def _can_connect(url: str) -> bool:
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except OperationalError:
        return False


@pytest.fixture(scope="module")
def pg_test_db() -> Any:
    admin_url = _pg_admin_url()
    if not _can_connect(admin_url):
        pytest.skip("PostgreSQL test server not available")

    db_name = f"identity_migration_test_{uuid.uuid4().hex[:12]}"
    engine = create_engine(admin_url).execution_options(isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {db_name}"))
    engine.dispose()

    test_url = _test_db_url(admin_url, db_name)
    yield test_url

    engine = create_engine(admin_url).execution_options(isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE)"))
    engine.dispose()


class TestAlembicMigrations:
    def test_upgrade_head_creates_expected_schema(self, pg_test_db: str) -> None:
        env = os.environ.copy()
        env["DATABASE_URL"] = pg_test_db
        env["KB_AUTHZ_SCHEMA"] = "kb_authz"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "src/identity/migrations/alembic.ini",
                "upgrade",
                "head",
            ],
            env=env,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.returncode == 0

        engine = create_engine(pg_test_db)
        try:
            inspector = inspect(engine)
            schemas = inspector.get_schema_names()
            assert "kb_authz" in schemas

            tables = inspector.get_table_names(schema="kb_authz")
            expected_tables = {
                "identities",
                "identity_external_refs",
                "group_snapshots",
                "policy_bundles",
                "authz_contexts",
                "revocations",
                "alembic_version",
            }
            assert expected_tables.issubset(set(tables))

            id_ref_cols = {c["name"] for c in inspector.get_columns("identity_external_refs", schema="kb_authz")}
            assert {"issuer", "sub", "identity_id", "created_at"}.issubset(id_ref_cols)

            id_ref_pks = inspector.get_pk_constraint("identity_external_refs", schema="kb_authz")["constrained_columns"]
            assert set(id_ref_pks) == {"issuer", "sub"}

            id_ref_indexes = {idx["name"] for idx in inspector.get_indexes("identity_external_refs", schema="kb_authz")}
            assert "ix_identity_external_refs_identity_id" in id_ref_indexes

            identity_indexes = {idx["name"] for idx in inspector.get_indexes("identities", schema="kb_authz")}
            assert "ix_identities_external_refs_gin" in identity_indexes
        finally:
            engine.dispose()

        downgrade = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "src/identity/migrations/alembic.ini",
                "downgrade",
                "base",
            ],
            env=env,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        assert downgrade.returncode == 0
