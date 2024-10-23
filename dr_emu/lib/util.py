import docker.errors
from docker import DockerClient
import asyncio

from netaddr import IPNetwork

from dr_emu.lib.logger import logger

used_infra_networks: set[IPNetwork] = set()
used_docker_container_names: set[str] = set()
used_docker_network_names: set[str] = set()


# TODO: Needs testing, also, never used
# async def depends_on(client: DockerClient, dependencies: dict[str, str], timeout: int = 15) -> bool:
#     async def check_dependency(container: str, dependency: str):
#         count = 0
#         while count < timeout:
#             try:
#                 # TODO: this is HOTFIX, rework dependency to feature in models
#                 container_info: dict[str, Any] = client.api.inspect_container(container)
#             except NotFound:
#                 logger.debug(f"Waiting for dependency container: {container}")
#                 await asyncio.sleep(1)
#                 count += 1
#                 continue
#
#             if dependency == constants.SERVICE_HEALTHY:
#                 try:
#                     container_health = (
#                         client.api.inspect_container(container).get("State").get("Health").get("Status")
#                     )
#                     if container_health == "healthy":
#                         return True
#                     else:
#                         logger.debug(f"Waiting for healthy container: {container}")
#                         await asyncio.sleep(1)
#                         count += 1
#                 except AttributeError:
#                     logger.error(f"Container {container} doesn't have a health check")
#                     dependency = constants.SERVICE_STARTED
#
#             elif dependency == constants.SERVICE_STARTED:
#                 if client.containers.get(container).status == "running":
#                     return True
#                 else:
#                     logger.debug(f"Waiting for running container: {container}")
#                     await asyncio.sleep(1)
#                     count += 1
#
#     for key, value in dependencies.items():
#         if await check_dependency(key, value) is True:
#             continue
#         else:
#             return False
#
#     return True


async def get_container_names(docker_client: DockerClient) -> set[str]:
    """
    Get already used docker names from running docker containers and networks.
    :param docker_client: client for docker rest api
    :return: sets of used docker names
    """
    logger.debug("Getting docker container names")
    docker_container_names: list[str] = []
    for container in await asyncio.to_thread(docker_client.containers.list, all=True):
        docker_container_names.append(container.name)  # type: ignore

    logger.debug("Completed Getting docker container names")
    return set(docker_container_names)


async def get_network_names(docker_client: DockerClient) -> set[str]:
    """
    Get already used docker names from running docker containers and networks.
    :param docker_client: client for docker rest api
    :return: sets of used docker names
    """
    logger.debug("Getting docker network names")
    docker_network_names: list[str] = []

    for network in await asyncio.to_thread(docker_client.networks.list):
        docker_network_names.append(network.name)  # type: ignore

    logger.debug("Completed Getting docker network names")
    return set(docker_network_names)


async def get_available_networks_for_infras(
    used_networks: set[IPNetwork], number_of_infrastructures: int, used_infra_supernets: set[IPNetwork]
) -> list[IPNetwork]:
    """
    Return available subnets(supernets) for infrastructures.
    :param used_networks: Networks that already exists in docker
    :param used_infra_supernets: Subnets that are already used by other infrastructures
    :param number_of_infrastructures:
    :return: list of available Networks, that can be used during infrastructure building.
    """
    logger.debug("Getting available IP addressed for networks")
    available_networks: list[IPNetwork] = []
    # TODO: what if I run out of ip address space?
    infrastructure_subnets = IPNetwork("10.0.0.0/8").subnet(16)

    for subnet in infrastructure_subnets:
        if subnet not in [*used_networks, *available_networks, *used_infra_supernets]:
            available_networks.append(subnet)
        if len(available_networks) == number_of_infrastructures:
            break

    logger.debug("Completed getting available IP addressed for infrastructures", available_subnets=available_networks)
    return available_networks


async def generate_infrastructure_subnets(
    supernet: IPNetwork, original_networks: list[IPNetwork], used_networks: set[IPNetwork]
) -> list[IPNetwork]:
    infrastructure_subnets: list[IPNetwork] = []
    for new_subnet in supernet.subnet(original_networks[0].prefixlen):
        if new_subnet not in used_networks:
            infrastructure_subnets.append(new_subnet)
        if len(infrastructure_subnets) == len(original_networks) + 1:
            break

    logger.debug("Completed getting IP addressed for infrastructure", infrastructure_subnets=infrastructure_subnets)
    return infrastructure_subnets


async def pull_images(docker_client: DockerClient, images: set[str]) -> None:
    """
    Pull docker images that will be used in the infrastructure.
    :return:
    """
    logger.debug(f"Pulling docker images")
    async with asyncio.TaskGroup() as tg:
        for image in images:
            tg.create_task(pull_image(docker_client, image))


async def pull_image(docker_client: DockerClient, image: str):
    try:
        await asyncio.to_thread(docker_client.images.get, image)
    except docker.errors.ImageNotFound:
        logger.info(f"pulling image", image=image)
        for _ in range(3):
            try:
                await asyncio.to_thread(docker_client.images.pull, image)
                break
            except docker.errors.DockerException as err:  # TODO: find out what exception is thrown during unreachable image pull source (Server Timeout)
                logger.error(f"Could not pull image {image} due to {err}... retrying")
                await asyncio.sleep(1)


async def check_running_tasks(name: str):
    loop = asyncio.get_running_loop()
    for task in asyncio.all_tasks(loop):
        if task.get_name() == name and not task.done():
            return True
    return False
