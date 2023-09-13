from __future__ import annotations

from testbed_app.database import async_engine
from testbed_app.models import Base


async def create_db():
    """
    Create database tables
    :return: None
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def destroy_db():
    """
    Drop database tables
    :return:
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
