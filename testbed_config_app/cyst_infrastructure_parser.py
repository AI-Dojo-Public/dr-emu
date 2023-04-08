import docker
# TODO: use configured objects from cyst_core instead of cyst_infra input?
import cyst_infrastructure
from classes import NetworkConfig, NodeContainerConfig, RouterContainerConfig
from util import constants
from typing import List, Dict, TypedDict
import itertools

client = docker.from_env()
docker_img = "nicolaka/netshoot"


def parse_networks(cyst_routers: cyst_infrastructure.routers):
    unique_networks = []
    network_objects = []
    networks_dict = {}
    for router in cyst_routers:
        for interface in router.interfaces:
            if interface.net not in unique_networks:
                unique_networks.append(interface.net)
                network_objects.append(NetworkConfig(interface.net, interface.net[-2], interface.ip))

    network_objects.append(NetworkConfig(constants.MANAGEMENT_NETWORK_IP, constants.MANAGEMENT_NETWORK_BRIDGE_IP,
                                         name=constants.MANAGEMENT_NETWORK_NAME))

    for network in network_objects:
        networks_dict[network.name] = network

    return networks_dict


def parse_nodes(cyst_nodes: cyst_infrastructure.nodes, testbed_networks: Dict[str, NetworkConfig]):
    node_objects = {}
    for node in cyst_nodes:
        for network in testbed_networks.values():
            if network.ip == node.interfaces[0].net:
                current_node = NodeContainerConfig(node.id, node.interfaces[0].ip,
                                                   network.name, network.gateway, image=docker_img)
                network.node_containers.append(current_node)
                node_objects[node.id] = current_node

    return node_objects


def parse_routers(cyst_routers: cyst_infrastructure.routers, testbed_networks: Dict[str, NetworkConfig]):
    management_network = testbed_networks[constants.MANAGEMENT_NETWORK_NAME]
    router_objects = {}

    for (router, ipaddr) in zip(cyst_routers, constants.MANAGEMENT_NETWORK_IP.iter_hosts()):
        router_objects[router.id] = RouterContainerConfig(router.id, router.interfaces, management_ipaddress=ipaddr,
                                                          command="sleep infinity", image=docker_img)

    for router in router_objects.values():
        if router.name == constants.PERIMETER_ROUTER:
            router.gateway = management_network.bridge_ip
        else:
            router.gateway = router_objects[constants.PERIMETER_ROUTER].ipaddress

    return router_objects


def confirm_router(node_id: str, cyst_routers: cyst_infrastructure.routers):
    router_ids = []

    for router in cyst_routers:
        router_ids.append(router.id)

    if node_id in router_ids:
        return True
    return False


# TODO: is gateway better in Network class?
def parse_node_gateways(cyst_routers: cyst_infrastructure.routers, network_connections: cyst_infrastructure.connections,
                        nodes: List[NodeContainerConfig], routers: List[RouterContainerConfig]):
    for node in nodes:
        for network_connection in network_connections:
            connection_ids = [network_connection.src_id, network_connections.dst_id]
            if node.name in connection_ids:
                for router in routers:
                    if connection_ids[connection_ids.index(node.name) + 1] == router.name:
                        node.gateway = router.name


# TODO: needs further consultation
def find_perimeter_router():
    pass


networks = parse_networks(cyst_infrastructure.routers)

routers = parse_routers(cyst_infrastructure.routers, networks)

nodes = parse_nodes(cyst_infrastructure.nodes, networks)

print("Networks:")
for network in networks.values():
    print(
        f"name: {network.name}, gateway: {network.gateway}, bridge_ip: {network.bridge_ip}, ip_addr: {network.ip}, nodes:")
    for node in network.node_containers:
        print(node.name)

print("\nNodes:")
for mynode in nodes.values():
    print(f"name: {mynode.name}, ip: {mynode.ipaddress} "
          f"network_name: {mynode.network_name}, gateway: {mynode.gateway}")

print("\nRouters:")
for myrouter in routers.values():
    print(f"name: {myrouter.name}, router_gateway: {myrouter.gateway} network_name: {myrouter.network_name} interfaces:")
    for interface in myrouter.interfaces:
        print(interface.ip)
