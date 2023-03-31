import docker
# TODO: use configured objects from cyst_core instead of cyst_infra input?
import cyst_infrastructure
from classes import Network, NodeContainer, RouterContainer
from util import constants
from typing import List, Dict, TypedDict

client = docker.from_env()


def parse_networks(cyst_routers: cyst_infrastructure.routers):
    unique_networks = []
    network_objects = []
    networks_dict = {}
    for router in cyst_routers:
        for interface in router.interfaces:
            if interface.net not in unique_networks:
                unique_networks.append(interface.net)
                # TODO: use 'find_management_network' instead of raw string when finished
                if str(interface.net) == "192.168.50.0/24":
                    network_objects.append(Network(interface.net, interface.net[-6], interface.ip,
                                                   constants.MANAGEMENT_NETWORK))
                else:
                    network_objects.append(Network(interface.net, interface.net[-6], interface.ip))

    for network in network_objects:
        networks_dict[network.name] = network

    print("Networks:")
    for network in networks_dict.values():
        print(f"name: {network.name}, gateway: {network.gateway}, bridge_ip: {network.bridge_ip}, ip_addr: {network.ip}")
    return networks_dict


def parse_nodes(cyst_nodes: cyst_infrastructure.nodes, ):
    node_objects = {}
    for node in cyst_nodes:
        node_objects[node.id] = NodeContainer(node.interfaces[0].ip, node.interfaces[0].net, node.id,
                                              node.interfaces[0].net[1])

    print("\nNodes:")
    for mynode in node_objects.values():
        print(f"name: {mynode.name}, ip: {mynode.ip}, network: {mynode.network}, gateway: {mynode.gateway}")
    return node_objects


def parse_routers(cyst_routers: cyst_infrastructure.routers, testbed_networks: Dict[str, Network]):
    management_network = testbed_networks[constants.MANAGEMENT_NETWORK]
    router_objects = {}
    for router in cyst_routers:
        router_objects[router.id] = RouterContainer(router.interfaces, router.id)

    for router in router_objects.values():
        if router.name == constants.PERIMETER_ROUTER:
            router.gateway = management_network.bridge_ip
        else:
            for interface in router_objects[constants.PERIMETER_ROUTER].interfaces:
                if interface.net == management_network.ip:
                    router.gateway = interface.ip

    print("\nRouters:")
    for router in router_objects.values():
        print(f"name: {router.name}, router_gateway: {router.gateway} interfaces:")
        for interface in router.interfaces:
            print(interface.ip)
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
                        nodes: List[NodeContainer], routers: List[RouterContainer]):
    for node in nodes:
        for network_connection in network_connections:
            connection_ids = [network_connection.src_id, network_connections.dst_id]
            if node.name in connection_ids:
                for router in routers:
                    if connection_ids[connection_ids.index(node.name)+1] == router.name:
                        node.gateway = router.name


# TODO: needs further consultation
def find_management_network(routers, router_connections):
    pass


networks = parse_networks(cyst_infrastructure.routers)

routers = parse_routers(cyst_infrastructure.routers, networks)

nodes = parse_nodes(cyst_infrastructure.nodes)

