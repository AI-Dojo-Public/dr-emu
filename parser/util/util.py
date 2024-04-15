import asyncio
from ipaddress import IPv4Address

from docker import DockerClient
import docker.errors
from netaddr import IPNetwork, IPAddress

from dr_emu.lib.logger import logger
from dr_emu.models import Network
from cyst_infrastructure import RouterConfig, NodeConfig


# Unused function for rewriting ip addresses based on user input prefix
def change_ipadresses(nodes: list[NodeConfig], routers: list[RouterConfig], ip_prefix: str):
    for appliance in [*routers, *nodes]:
        for interface in appliance.interfaces:
            new_ip = rewrite_ipaddress_with_prefix(str(interface.ip), ip_prefix)
            new_net = rewrite_ipaddress_with_prefix(str(interface.net), ip_prefix)
            interface.ip = IPAddress(new_ip)
            interface.net = IPNetwork(new_net)

    return nodes, routers


# Unused function for rewriting ip addresses based on user input prefix
def rewrite_ipaddress_with_prefix(old_ip: str, new_ip_prefix: str):
    original_ip_octate_list = old_ip.split(".")
    new_ip_octate_list = new_ip_prefix.split(".")

    for ip_octate, prefix_octate in zip(original_ip_octate_list, new_ip_octate_list):
        octate_index = new_ip_octate_list.index(prefix_octate)
        if prefix_octate == "x":
            new_ip_octate_list[octate_index] = original_ip_octate_list[octate_index]
        elif len(prefix_octate) > 1:
            if len(prefix_octate) != len(ip_octate):
                print(prefix_octate, ip_octate)
                raise RuntimeError("Format of specified ip prefix doesn't match the format of original ip addresses")
            for ip_digit, prefix_digit in zip(ip_octate, prefix_octate):
                if prefix_digit == "x":
                    digit_index = prefix_octate.index(prefix_digit)
                    prefix_octate = (
                        prefix_octate[0:digit_index] + ip_octate[digit_index] + prefix_octate[digit_index + 1 :]
                    )
                    new_ip_octate_list[octate_index] = prefix_octate

    return ".".join([str(elem) for elem in new_ip_octate_list])


# Unused function for rewriting ip addresses based on user input prefix
async def check_used_ipaddreses(docker_client: DockerClient, parsed_networks: list[Network]):
    """
    Check already used network ip spaces.
    :param docker_client: client for docker rest api
    :param parsed_networks: Network objects parsed from cyst infrastructure
    :return:
    """
    docker_networks = await asyncio.to_thread(docker_client.networks.list)
    for docker_network in docker_networks:
        if docker_network.name in ["none", "host"]:
            continue

        network_ip = docker_client.networks.get(docker_network.id).attrs["IPAM"]["Config"][0]["Subnet"]
        for parsed_network in parsed_networks:
            if str(parsed_network.ipaddress) == network_ip:
                raise Exception(f"Network with ip address {network_ip} already exists")


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


async def get_available_networks(
    docker_client: DockerClient,
    default_networks_ips: set[IPNetwork],
    number_of_infrastructures: int,
    supernet: IPNetwork,
    subnet_mask: int
) -> list[IPNetwork]:
    """
    Get available networks for new infrastructure, also returns available ips for management networks.
    :param number_of_infrastructures:
    :param docker_client: client for docker rest api
    :param default_networks_ips: Default ip addresses of networks parsed from cyst infrastructure description
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

    if default_networks_ips.difference(used_networks) == default_networks_ips:
        available_networks += list(default_networks_ips)

    number_of_returned_subnets = (1 + len(default_networks_ips)) * number_of_infrastructures

    # TODO: what if I run out of ip address space?
    subnets = supernet.subnet(subnet_mask)

    for subnet in subnets:
        if subnet not in [*used_networks, *available_networks]:
            available_networks.append(subnet)
        if len(available_networks) == number_of_returned_subnets:
            break

    logger.debug("Completed getting available IP addressed for networks", available_subnets=available_networks)
    return available_networks


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
