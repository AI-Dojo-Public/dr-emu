from enum import Enum
from docker import DockerClient
import asyncio
from dr_emu.lib.logger import logger
from docker.errors import NotFound
from parser.util import constants


class AgentRole(Enum):
    attacker = "attacker"
    defender = "defender"


class InstallChoice(Enum):
    git = "git"
    pypi = "pypi"
    local = "local"


# TODO: Needs testing, also, never used
async def depends_on(client: DockerClient, dependencies: dict, timeout=15) -> bool:
    async def check_dependency(container, dependency):
        count = 0
        while count < timeout:
            try:
                # TODO: this is HOTFIX, rework dependency to feature in models
                container_info = client.api.inspect_container(container)
            except NotFound:
                logger.debug(f"Waiting for dependency container: {container}")
                await asyncio.sleep(1)
                count += 1
                continue

            if dependency == constants.SERVICE_HEALTHY:
                try:
                    container_health = (
                        client.api.inspect_container(container_info).get("State").get("Health").get("Status")
                    )
                    if container_health == "healthy":
                        return True
                    else:
                        logger.debug(f"Waiting for healthy container: {container}")
                        await asyncio.sleep(1)
                        count += 1
                except AttributeError:
                    logger.error(f"Container {container} doesn't have a health check")
                    dependency = constants.SERVICE_STARTED

            elif dependency == constants.SERVICE_STARTED:
                if client.containers.get(container).status == "running":
                    return True
                else:
                    logger.debug(f"Waiting for running container: {container}")
                    await asyncio.sleep(1)
                    count += 1

    for key, value in dependencies.items():
        if await check_dependency(key, value) is True:
            continue
        else:
            return False

    return True
