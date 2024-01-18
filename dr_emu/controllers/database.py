from __future__ import annotations

from dr_emu.lib.logger import logger
from dr_emu.database_config import sessionmanager
from dr_emu.models import Base


async def create_db():
    """
    Create database tables
    :return: None
    """
    logger.debug("Creating Database")
    await sessionmanager.engine.connect().run_sync(Base.metadata.create_all)
    logger.info("Database created")


async def destroy_db():
    """
    Drop database tables
    :return:
    """
    logger.debug("Destroying Database")
    await sessionmanager.engine.connect().run_sync(Base.metadata.drop_all)
    logger.info("Database destroyed")
