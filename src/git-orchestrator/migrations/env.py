"""Alembic environment configuration."""

from __future__ import annotations

import importlib
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Make the git-orchestrator package importable under a valid Python identifier
# so that Alembic can reference its models and settings.
_SRC = Path(__file__).resolve().parents[2]  # src/git-orchestrator/migrations -> src
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

importlib.import_module("git-orchestrator.app.models.ops")
for _name in list(sys.modules):
    if _name.startswith("git-orchestrator"):
        sys.modules[_name.replace("git-orchestrator", "git_orchestrator")] = sys.modules[_name]

from git_orchestrator.app.core.config import settings
from git_orchestrator.app.models.ops import Base

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Allow DATABASE_URL to override alembic.ini.
url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
config.set_main_option("sqlalchemy.url", url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=settings.KB_OPS_SCHEMA,
    )

    with context.begin_transaction():
        if settings.KB_OPS_SCHEMA:
            context.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.KB_OPS_SCHEMA};")
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if settings.KB_OPS_SCHEMA:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.KB_OPS_SCHEMA}"))
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=settings.KB_OPS_SCHEMA,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
