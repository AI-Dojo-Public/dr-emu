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

    def stop(self, check_id: bool = False):
        self.delete_nodes(check_id)
        self.delete_routers(check_id)
        self.delete_networks(check_id)

    def delete_networks(self, check_id: bool):
        for network in self.networks:
            if not check_id or (check_id and network.id != ""):
                network.delete()

    def delete_routers(self, check_id: bool):
        for router in self.routers:
            if not check_id or (check_id and router.id != ""):
                router.delete()

    def delete_nodes(self, check_id: bool):
        for node in self.nodes:
            if not check_id or (check_id and node.id != ""):
                node.delete()
