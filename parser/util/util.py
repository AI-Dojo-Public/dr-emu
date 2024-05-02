import asyncio
from typing import Sequence

from docker import DockerClient
import docker.errors
from netaddr import IPNetwork, IPAddress

from dr_emu.lib.logger import logger
from dr_emu.models import Network
from cyst_infrastructure import RouterConfig, NodeConfig


# TODO:  move to dr_emu.lib.util
async def get_container_names(docker_client: DockerClient) -> set[str]:
    """
    Get already used docker names from running docker containers and networks.
    :param docker_client: client for docker rest api
    :return: sets of used docker names
    """
    logger.debug("Getting docker container names")
    docker_container_names = []
    for container in await asyncio.to_thread(docker_client.containers.list, all=True):
        docker_container_names.append(container.name)

    logger.debug("Completed Getting docker container names")
    return set(docker_container_names)


# TODO:  move to dr_emu.lib.util
async def get_network_names(docker_client: DockerClient) -> set[str]:
    """
    Get already used docker names from running docker containers and networks.
    :param docker_client: client for docker rest api
    :return: sets of used docker names
    """
    logger.debug("Getting docker network names")
    docker_network_names = []

    for network in await asyncio.to_thread(docker_client.networks.list):
        docker_network_names.append(network.name)

    logger.debug("Completed Getting docker network names")
    return set(docker_network_names)


# TODO:  move to dr_emu.lib.util
async def get_available_networks_for_infras(
    docker_client: DockerClient,
    number_of_infrastructures: int,
    used_infra_supernets: set[IPNetwork]
) -> list[IPNetwork]:
    """
    Return available subnets(supernets) for infrastructures.
    :param used_infra_supernets: Subnets that are already used by other infrastructures
    :param number_of_infrastructures:
    :param docker_client: client for docker rest api
    :return: list of available Networks, that can be used during infrastructure building.
    """
    logger.debug("Getting available IP addressed for networks")
    used_networks = set()
    available_networks = []
    docker_networks = await asyncio.to_thread(docker_client.networks.list)
    for docker_network in docker_networks:
        if docker_network.name in ["none", "host"]:
            continue
        used_networks.add(IPNetwork(docker_client.networks.get(docker_network.id).attrs["IPAM"]["Config"][0]["Subnet"]))

    # TODO: what if I run out of ip address space?
    infrastructure_subnets = IPNetwork("10.0.0.0/8").subnet(16)

    for subnet in infrastructure_subnets:
        if subnet not in [*used_networks, *available_networks, *used_infra_supernets]:
            available_networks.append(subnet)
        if len(available_networks) == number_of_infrastructures:
            break

    logger.debug("Completed getting available IP addressed for infrastructures", available_subnets=available_networks)
    return available_networks


# TODO:  move to dr_emu.lib.util
async def generate_infrastructure_subnets(supernet: IPNetwork, original_networks: list[IPNetwork]) -> list[IPNetwork]:
    infrastructure_subnets = []
    for new_subnet in supernet.subnet(original_networks[0].prefixlen):
        infrastructure_subnets.append(new_subnet)
        if len(infrastructure_subnets) == len(original_networks) + 1:
            break

    logger.debug("Completed getting IP addressed for infrastructure", infrastructure_subnets=infrastructure_subnets)
    return infrastructure_subnets


async def pull_images(docker_client, images):
    """
    Pull docker images that will be used in the infrastructure.
    :return:
    """
    pull_image_tasks = set()
    logger.debug(f"Pulling docker images")
    for image in images:
        try:
            await asyncio.to_thread(docker_client.images.get, image)
        except docker.errors.ImageNotFound:
            logger.info(f"pulling image", image=image)
            pull_image_tasks.add(asyncio.create_task(asyncio.to_thread(docker_client.images.pull, image)))

    if pull_image_tasks:
        await asyncio.gather(*pull_image_tasks)

    logger.info("Completed pulling docker images")
