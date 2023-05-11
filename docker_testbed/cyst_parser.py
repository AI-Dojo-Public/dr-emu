from docker import DockerClient

from netaddr import IPNetwork

from cyst_infrastructure import nodes as cyst_nodes, routers as cyst_routers

from docker_testbed.lib.network import Network
from docker_testbed.lib.node import Node
from docker_testbed.lib.service import Service
from docker_testbed.lib.router import Router
from docker_testbed.util import constants


class CYSTParser:
    def __init__(self, client: DockerClient):
        self.client = client
        self.router_image = constants.IMAGE_ROUTER
        self.networks: list[Network] = []
        self.routers: list[Router] = []
        self.nodes: list[Node] = []

    def find_network(self, subnet: IPNetwork):
        for network in self.networks:
            if network.subnet == subnet:
                return network

        raise RuntimeError(f"No network matching {subnet}.")

    @staticmethod
    def get_service_configuration(name):
        """
        This method will parse given details (will need more than just a name) and return Docker image with kwargs
        """
        # TODO
        return {"image": constants.IMAGE_BASE, "kwargs": {"tty": True}}

    def parse_networks(self):
        self.networks.append(
            Network(
                self.client,
                constants.MANAGEMENT_NETWORK_SUBNET,
                constants.MANAGEMENT_NETWORK_ROUTER_GATEWAY,
            )
        )

        for cyst_router in cyst_routers:
            for interface in cyst_router.interfaces:
                if not any(interface.net == n.subnet for n in self.networks):
                    network = Network(self.client, interface.net, interface.ip)
                    self.networks.append(network)

    def parse_nodes(self):
        for cyst_node in cyst_nodes:
            services = self.parse_services(
                cyst_node.active_services + cyst_node.passive_services
            )
            interface = cyst_node.interfaces[0]

            node = Node(
                self.client,
                cyst_node.id,
                interface.ip,
                self.find_network(interface.net),
                services,
            )
            self.nodes.append(node)

    def parse_services(self, node_services: list):
        services = []

        for cyst_service in node_services:
            configuration = self.get_service_configuration(cyst_service.id)
            service = Service(
                self.client,
                cyst_service.id,
                configuration["image"],
                **configuration["kwargs"],
            )
            services.append(service)

        return services

    def parse_routers(self):
        management_network = self.networks[0]

        for cyst_router, ip_address in zip(
            cyst_routers, management_network.subnet.iter_hosts()
        ):
            router_networks = []

            for interface in cyst_router.interfaces:
                router_networks.append(self.find_network(interface.net))

            router = Router(
                self.client,
                cyst_router.id,
                ip_address,
                management_network,
                router_networks,
            )
            self.routers.append(router)

    def parse(self):
        self.parse_networks()
        self.parse_routers()
        self.parse_nodes()
