from cyst_infrastructure import nodes, routers, RouterConfig, InterfaceConfig
from typing import List
from netaddr import IPAddress, IPNetwork

class Network:  # Network
    def __init__(self, ip: IPAddress, subnet: IPNetwork):
        self.id = ""
        self.name = str(subnet.network)  # TODO: self.name == self.subnet
        self.ip = str(ip)
        self.subnet = subnet
        self.gateway = self.subnet.first
        self.default_gateway = self.subnet.last


class Service:  # Container
    def __init__(self):
        self.id = ""
        self.image = ""


class Node:  # Stack of containers
    def __init__(self):
        self.id = ""
        self.interfaces = []  # ip, gateway
        self.services = []


class Router(Node):  # Node, but a router
    def __init__(self):
        super().__init__()


def prepare_networks():
    networks: List[Network] = []

    for router in routers:
        for interface in router.interfaces:
            if not any(interface.net == n.subnet for n in networks):
                networks.append(Network(interface.ip, interface.net))

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

if __name__ == '__main__':
