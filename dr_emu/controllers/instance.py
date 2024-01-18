from dr_emu.models import Instance
from dr_emu.controllers.infrastructure import InfrastructureController
from dr_emu.lib.logger import logger
from sqlalchemy.ext.asyncio import AsyncSession


async def delete_instance(instance: Instance, db_session: AsyncSession) -> None:
    await InfrastructureController.stop_infra(instance.infrastructure)
    logger.debug("Deleting Instance", id=instance.id)
    await db_session.delete(instance)
    await db_session.commit()
    logger.info("Instance deleted", id=instance.id)
