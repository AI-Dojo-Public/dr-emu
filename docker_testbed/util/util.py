import asyncio
import netaddr
from docker import DockerClient
from netaddr import IPNetwork, IPAddress

from testbed_app.models import Network
from cyst_infrastructure import RouterConfig, NodeConfig


# Unusedfunction for rewriting ip addresses based on user input prefix
def change_ipadresses(
    nodes: list[NodeConfig], routers: list[RouterConfig], ip_prefix: str
):
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
                raise RuntimeError(
                    "Format of specified ip prefix doesn't match the format of original ip addresses"
                )
            for ip_digit, prefix_digit in zip(ip_octate, prefix_octate):
                if prefix_digit == "x":
                    digit_index = prefix_octate.index(prefix_digit)
                    prefix_octate = (
                        prefix_octate[0:digit_index]
                        + ip_octate[digit_index]
                        + prefix_octate[digit_index + 1 :]
                    )
                    new_ip_octate_list[octate_index] = prefix_octate

    return ".".join([str(elem) for elem in new_ip_octate_list])


# Unused function for rewriting ip addresses based on user input prefix
async def get_docker_names(docker_client: DockerClient):
    docker_container_names = []
    docker_network_names = []
    for container in await asyncio.to_thread(docker_client.containers.list, all=True):
        docker_container_names.append(container.name)

    for network in await asyncio.to_thread(docker_client.networks.list):
        docker_network_names.append(network.name)

    return set(docker_container_names), set(docker_network_names)


async def check_used_ipaddreses(docker_client, parsed_networks: list[Network]):
    docker_networks = await asyncio.to_thread(docker_client.networks.list)
    for docker_network in docker_networks:
        if docker_network.name in ["none", "host"]:
            continue

        network_ip = docker_client.networks.get(docker_network.id).attrs["IPAM"][
            "Config"
        ][0]["Subnet"]
        for parsed_network in parsed_networks:
            if str(parsed_network.ipaddress) == network_ip:
                raise Exception(f"Network with ip address {network_ip} already exists")


async def get_available_networks(docker_client, parsed_networks: list[Network]):
    used_networks = set()
    docker_networks = await asyncio.to_thread(docker_client.networks.list)
    for docker_network in docker_networks:
        if docker_network.name in ["none", "host"]:
            continue

        used_networks.add(
            IPNetwork(
                docker_client.networks.get(docker_network.id).attrs["IPAM"]["Config"][
                    0
                ]["Subnet"]
            )
        )
    default_networks_ips = {network.ipaddress for network in parsed_networks}
    if default_networks_ips.difference(used_networks) == default_networks_ips:
        number_of_returned_subnets = 1
    else:
        number_of_returned_subnets = len(parsed_networks) + 1

    supernet = IPNetwork("192.168.0.0/16")  # Rework as a user input in the future
    subnets = supernet.subnet(24)
    available_subnets = []

    for subnet in subnets:
        if subnet not in used_networks:
            available_subnets.append(subnet)
        if len(available_subnets) == number_of_returned_subnets:
            break

    return available_subnets
