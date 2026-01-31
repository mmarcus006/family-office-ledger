"""Alembic environment configuration.

This file connects Alembic migrations to our application's
configuration and database settings.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from family_office_ledger.config import get_settings  # noqa: E402

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from application settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.effective_database_url)

# Add your model's MetaData object here for 'autogenerate' support.
# For now, we don't have SQLAlchemy models (using raw SQL in repositories),
# so target_metadata is None. When/if we add SQLAlchemy ORM models,
# import their Base.metadata here.
# from family_office_ledger.models import Base
# target_metadata = Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schema names in migration
        include_schemas=True,
        # Render item names as quoted when necessary
        render_as_batch=True,  # Better SQLite support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate
    a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Include schema names in migration
            include_schemas=True,
            # Use batch mode for SQLite ALTER TABLE support
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
