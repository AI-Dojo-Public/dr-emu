import randomname
from docker import DockerClient

from netaddr import IPNetwork

from cyst_infrastructure import RouterConfig, NodeConfig

from testbed_app.models import Network, Service, Router, Interface, Node
from docker_testbed.util import constants


class CYSTParser:
    def __init__(self, client: DockerClient):
        self.client = client
        self.router_image = constants.IMAGE_ROUTER
        self.networks: list[Network] = []
        self.routers: list[Router] = []
        self.nodes: list[Node] = []
        self.images: set = set()

    # TODO
    def parse_images(self):
        self.images = set(constants.IMAGE_LIST)

    def find_network(self, subnet: IPNetwork):
        for network in self.networks:
            if network.ipaddress == subnet:
                return network

        raise RuntimeError(f"No network matching {subnet}.")

    @staticmethod
    def get_service_configuration(name):
        """
        This method will parse given details (will need more than just a name) and return Docker image with kwargs
        """
        # TODO
        return {"image": constants.IMAGE_BASE, "kwargs": {}}

    def parse_networks(self, cyst_routers):
        for cyst_router in cyst_routers:
            for interface in cyst_router.interfaces:
                if not any(interface.net == n.ipaddress for n in self.networks):
                    network_name = randomname.get_name(
                        adj="colors", noun="astronomy", sep="_"
                    )
                    network = Network(
                        ipaddress=interface.net,
                        router_gateway=interface.ip,
                        name=network_name,
                        network_type=constants.NETWORK_TYPE_INTERNAL,
                    )
                    self.networks.append(network)

    def parse_nodes(self, cyst_nodes):
        for cyst_node in cyst_nodes:
            interfaces = []
            for interface in cyst_node.interfaces:
                interfaces.append(
                    Interface(
                        ipaddress=interface.ip, network=self.find_network(interface.net)
                    )
                )

            node_image = constants.IMAGE_NODE
            if (
                specified_image := constants.TESTBED_IMAGES.get(cyst_node.id)
            ) is not None:
                node_image = specified_image

            node = Node(
                name=cyst_node.id,
                interfaces=interfaces,
                image=node_image,
            )

            services = self.parse_services(
                cyst_node.active_services + cyst_node.passive_services
            )

            node.services = services
            self.nodes.append(node)

    def parse_services(self, node_services: list):
        services = []

        for cyst_service in node_services:
            service_image = constants.IMAGE_NODE
            if (
                specified_image := constants.TESTBED_IMAGES.get(cyst_service.id)
            ) is not None:
                service_image = specified_image

            configuration = self.get_service_configuration(cyst_service.id)
            service = Service(
                name=cyst_service.id,
                image=service_image,
                **configuration["kwargs"],
            )
            services.append(service)

        return services

    def parse_routers(self, cyst_routers):
        for cyst_router in cyst_routers:
            interfaces = []

            for interface in cyst_router.interfaces:
                network = self.find_network(interface.net)
                interfaces.append(
                    Interface(ipaddress=network.router_gateway, network=network)
                )

            router_type = (
                "perimeter" if cyst_router.id == "perimeter_router" else "internal"
            )

            router = Router(
                name=cyst_router.id,
                router_type=router_type,
                interfaces=interfaces,
                image=constants.IMAGE_ROUTER,
            )
            self.routers.append(router)

    def parse(self, cyst_routers: list[RouterConfig], cyst_nodes: list[NodeConfig]):
        self.parse_networks(cyst_routers)
        self.parse_routers(cyst_routers)
        self.parse_nodes(cyst_nodes)
        self.parse_images()
