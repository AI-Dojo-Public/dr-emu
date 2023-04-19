from docker import DockerClient

from docker_testbed.lib.network import Network
from docker_testbed.lib.node import Node
from docker_testbed.lib.router import Router


class Controller:
    def __init__(self, networks: list[Network], routers: list[Router], nodes: list[Node]):
        self.networks = networks
        self.routers = routers
        self.nodes = nodes

    def start(self):
        self.create_networks()
        self.start_routers()
        self.start_nodes()

    def create_networks(self):
        for network in self.networks:
            network.create()

    def start_routers(self):
        for router in self.routers:
            router.start()

    def start_nodes(self):
        for node in self.nodes:
            node.start()

    def stop(self):
        self.delete_nodes()
        self.delete_routers()
        self.delete_networks()

    def delete_networks(self):
        for network in self.networks:
            network.delete()

    def delete_routers(self):
        for router in self.routers:
            router.delete()

    def delete_nodes(self):
        for node in self.nodes:
            node.delete()
