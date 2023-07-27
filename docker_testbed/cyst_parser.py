import randomname
from docker import DockerClient

from netaddr import IPNetwork

from cyst_infrastructure import RouterConfig, NodeConfig, scripted_attacker

from testbed_app.models import Network, Service, Router, Interface, Node, Attacker
from docker_testbed.util import constants


class CYSTParser:
    def __init__(self, client: DockerClient):
        self.client = client
        self.router_image = constants.IMAGE_ROUTER
        self.networks: list[Network] = []
        self.routers: list[Router] = []
        self.nodes: list[Node, Attacker] = []
        self.images: set = set()

    # TODO
    async def parse_images(self):
        """
        Get images to build for infrastructure.
        :return:
        """
        self.images = set(constants.IMAGE_LIST)

    async def find_network(self, subnet: IPNetwork) -> Network:
        """
        Find network object matching the subnet ip address.
        :param subnet: network ip address
        :return: Network object
        """
        for network in self.networks:
            if network.ipaddress == subnet:
                return network

        raise RuntimeError(f"No network matching {subnet}.")

    @staticmethod
    async def get_service_configuration(name):
        """
        This method will parse given details (will need more than just a name) and return Docker image with kwargs
        """
        # TODO
        return {"image": constants.IMAGE_BASE, "kwargs": {}}

    async def parse_networks(self, cyst_routers):
        """
        Create network models from cyst infrastructure prescription.
        :param cyst_routers: router objects from cyst infrastructure
        :return:
        """
        generated_names = set()
        for cyst_router in cyst_routers:
            for interface in cyst_router.interfaces:
                if not any(interface.net == n.ipaddress for n in self.networks):
                    while (
                        network_name := randomname.get_name(
                            adj="colors", noun="astronomy", sep="_"
                        )
                    ) in generated_names:
                        continue

                    generated_names.add(network_name)

                    network_type = (
                        constants.NETWORK_TYPE_INTERNAL
                        if interface.ip != scripted_attacker.interfaces[0].ip
                        else constants.NETWORK_TYPE_PUBLIC
                    )
                    network = Network(
                        ipaddress=interface.net,
                        router_gateway=interface.ip,
                        name=network_name,
                        network_type=network_type,
                    )
                    self.networks.append(network)

    async def parse_nodes(self, cyst_nodes):
        """
        Create node models from cyst infrastructure prescription.
        :param cyst_nodes: node objects from cyst infrastructure
        :return:
        """
        for cyst_node in cyst_nodes:
            interfaces = []

            for interface in cyst_node.interfaces:
                interfaces.append(
                    Interface(
                        ipaddress=interface.ip,
                        network=(await self.find_network(interface.net)),
                    )
                )

            node_image = (
                specified_image
                if (specified_image := constants.TESTBED_IMAGES.get(cyst_node.id))
                is not None
                else constants.IMAGE_NODE
            )

            services = await self.parse_services(
                cyst_node.active_services + cyst_node.passive_services
            )

            environment = (
                envs if (envs := constants.envs.get(cyst_node.id)) is not None else {}
            )
            command = (
                container[constants.COMMAND]
                if (container := constants.TESTBED_INFO.get(cyst_node.id))
                else []
            )

            if cyst_node.id == "attacker_node":
                node = Attacker(
                    name=cyst_node.id,
                    interfaces=interfaces,
                    image=constants.TESTBED_IMAGES["attacker_node"],
                    services=services,
                    environment=environment,
                    command=command,
                )
            else:
                node = Node(
                    name=cyst_node.id,
                    interfaces=interfaces,
                    image=node_image,
                    services=services,
                    environment=environment,
                    command=command,
                )

            self.nodes.append(node)

    async def parse_services(self, node_services: list):
        """
        Create service models from nodes in cyst infrastructure prescription.
        :param node_services: node objects from cyst infrastructure
        :return:
        """
        services = []

        for cyst_service in node_services:
            service_image = (
                specified_image
                if (specified_image := constants.TESTBED_IMAGES.get(cyst_service.id))
                is not None
                else constants.IMAGE_NODE
            )

            configuration = await self.get_service_configuration(cyst_service.id)
            environment = (
                envs
                if (envs := constants.envs.get(cyst_service.id)) is not None
                else {}
            )
            command = (
                container[constants.COMMAND]
                if (container := constants.TESTBED_INFO.get(cyst_service.id))
                else []
            )

            service = Service(
                name=cyst_service.id,
                image=service_image,
                environment=environment,
                command=command,
                **configuration["kwargs"],
            )
            services.append(service)

        return services

    async def parse_routers(self, cyst_routers):
        """
        Create router models from nodes in cyst infrastructure prescription.
        :param cyst_routers: router objects from cyst infrastructure
        :return:
        """
        for cyst_router in cyst_routers:
            interfaces = []

            for interface in cyst_router.interfaces:
                network = await self.find_network(interface.net)
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

    async def parse(
        self, cyst_routers: list[RouterConfig], cyst_nodes: list[NodeConfig]
    ):
        """
        Create all necessary models for infrastructure based on parsed objects from cyst prescription.
        :param cyst_routers: router objects from cyst infrastructure
        :param cyst_nodes: node objects from cyst infrastructure
        :return:
        """
        await self.parse_networks(cyst_routers)
        await self.parse_routers(cyst_routers)
        await self.parse_nodes(cyst_nodes)
        await self.parse_images()
