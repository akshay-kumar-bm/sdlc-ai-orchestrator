import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

import app.db.models  # noqa: F401
from alembic import context
from app.core.config import get_settings
from app.db.base import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def _run(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async():
    engine = create_async_engine(get_settings().DATABASE_URL)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=get_settings().DATABASE_URL, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async())
