"""Alembic environment configuration."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from session.app.core.config import settings
from session.app.models.session import Base

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
        version_table_schema=settings.KB_SESSIONS_SCHEMA,
    )

    with context.begin_transaction():
        if settings.KB_SESSIONS_SCHEMA:
            context.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.KB_SESSIONS_SCHEMA};")
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if settings.KB_SESSIONS_SCHEMA:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.KB_SESSIONS_SCHEMA}"))
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=settings.KB_SESSIONS_SCHEMA,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
