from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database.session import Base, get_async_database_url
from app.core.config import settings
import app.models.models  # Registers all 6 models with Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    # Support CLI -x db_url=... override
    x_args = context.get_x_argument(as_dictionary=True)
    override_url = x_args.get("db_url")
    if not override_url:
        main_opt = config.get_main_option("sqlalchemy.url")
        if main_opt and main_opt.strip() and "%(DATABASE_URL)s" not in main_opt:
            override_url = main_opt
    raw_url = override_url if override_url else settings.DATABASE_URL
    return get_async_database_url(raw_url)


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url = get_url()
    connect_args = {}
    if url.startswith("postgresql"):
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0
    elif url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=url,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_async_migrations())
