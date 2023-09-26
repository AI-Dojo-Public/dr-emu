from testbed_app.models import Instance
from testbed_app.database_config import session_factory
from testbed_app.controllers.infrastructure import InfrastructureController
from testbed_app.lib.logger import logger


async def delete_instance(instance: Instance):
    async with session_factory() as session:
        await InfrastructureController.stop_infra(instance.infrastructure)
        logger.debug("Deleting Instance", id=instance.id)
        await session.delete(instance)
        await session.commit()
        logger.info("Instance deleted", id=instance.id)
