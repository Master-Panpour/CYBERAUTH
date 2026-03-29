"""Alembic environment configuration."""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from config import settings
import models

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Create Alembic config
config = context.config

# Set the sqlalchemy.url - convert async URL to sync for Alembic
db_url = settings.DATABASE_URL.replace("asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", db_url)

# Add models for autogenerate support
target_metadata = models.Base.metadata


def run_migrations_offline() -> None:
    """Run migrations 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations 'online'."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.StaticPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
