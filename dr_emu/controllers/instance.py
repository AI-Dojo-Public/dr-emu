from dr_emu.models import Instance
from dr_emu.database_config import session_factory
from dr_emu.controllers.infrastructure import InfrastructureController
from dr_emu.lib.logger import logger


async def delete_instance(instance: Instance):
    async with session_factory() as session:
        await InfrastructureController.stop_infra(instance.infrastructure)
        logger.debug("Deleting Instance", id=instance.id)
        await session.delete(instance)
        await session.commit()
        logger.info("Instance deleted", id=instance.id)
