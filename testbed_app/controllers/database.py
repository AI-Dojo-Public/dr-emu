from __future__ import annotations

from testbed_app.lib.logger import logger
from testbed_app.database_config import async_engine
from testbed_app.models import Base


async def create_db():
    """
    Create database tables
    :return: None
    """
    logger.debug("Creating Database")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database created")


async def destroy_db():
    """
    Drop database tables
    :return:
    """
    logger.debug("Destroying Database")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database destroyed")
