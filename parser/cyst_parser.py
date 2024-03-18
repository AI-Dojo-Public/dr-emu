import randomname
from docker import DockerClient

from netaddr import IPNetwork

from dr_emu.lib.logger import logger
from cyst.api.configuration.network.router import RouterConfig
from cyst.api.configuration.network.node import NodeConfig
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.environment import Environment

from dr_emu.models import Network, Service, Router, Interface, Node, Attacker, FirewallRule
from parser.util import constants
from cyst_infrastructure import all_config_items


class CYSTParser:

    @property
    def infrastructure_items(self):
        return all_config_items

    def __init__(self, client: DockerClient, infra_description: str):
        self.client = client
        self.infra_description = infra_description
        self.router_image = constants.IMAGE_ROUTER
        self.networks: list[Network] = []
        self.routers: list[Router] = []
        self.attacker: Attacker
        self.nodes: list[Node] = []
        self.images: set = set()

    # @property
    # def infrastructure_items(self):
    #     if not self._infrastructure_items:
    #         # deserialize json pickled config
    #         env = Environment.create()
    #
    #         # SECURITY VULNERABILITY, EXECUTES PYTHON CODE FROM USER INPOUT
    #         self._infrastructure_items = env.configuration.general.load_configuration(self.infra_description)
    #
    #     return self._infrastructure_items

    # TODO
    async def parse_images(self):
        """
        Get images to build for infrastructure.
        :return:
        """
        self.images = set(constants.IMAGE_LIST)

    async def get_default_networks_ips(self) -> set[IPNetwork]:
        network_ips = set()

        for item in self.infrastructure_items:
            if type(item) is RouterConfig:
                for interface in item.interfaces:
                    if not any(interface.net == network_ip for network_ip in network_ips):
                        network_ips.add(interface.net)

        return network_ips

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
                        network_name := randomname.get_name(adj="colors", noun="astronomy", sep="_")
                    ) in generated_names:
                        continue

                    generated_names.add(network_name)

                    network_type = (
                        constants.NETWORK_TYPE_PUBLIC
                        if cyst_router.id == "perimeter_router"
                        else constants.NETWORK_TYPE_INTERNAL
                    )
                    network = Network(
                        ipaddress=interface.net,
                        router_gateway=interface.ip,
                        name=network_name,
                        network_type=network_type,
                    )
                    self.networks.append(network)

    async def parse_nodes(self, cyst_nodes, attacker):
        """
        Create node models from cyst infrastructure prescription.
        :param attacker: node representing the attacker
        :param cyst_nodes: node objects from cyst infrastructure
        :return:
        """
        for cyst_node in cyst_nodes:
            interfaces = []

            for interface in cyst_node.interfaces:
                interfaces.append(
                    Interface(
                        ipaddress=interface.ip,
                        network=await self.find_network(interface.net),
                    )
                )

            node_image = (
                specified_image
                if (specified_image := constants.TESTBED_IMAGES.get(cyst_node.id)) is not None
                else constants.IMAGE_NODE
            )

            services = await self.parse_services(cyst_node.active_services + cyst_node.passive_services)
            environment = envs if (envs := constants.envs.get(cyst_node.id)) is not None else {}
            command = container[constants.COMMAND] if (container := constants.TESTBED_INFO.get(cyst_node.id)) else []

            try:  # TODO: unused
                depends_on = constants.TESTBED_INFO[cyst_node.id][constants.DEPENDS_ON]
            except KeyError:
                depends_on = {}

            try:
                healthcheck = constants.TESTBED_INFO[cyst_node.id][constants.HEALTHCHECK]
            except KeyError:
                healthcheck = {}

            if cyst_node == attacker:
                node = Attacker(
                    name=cyst_node.id,
                    interfaces=interfaces,
                    image=constants.TESTBED_IMAGES["attacker_node"],
                    services=services,
                    environment=environment,
                    command=command,
                    healthcheck=healthcheck,
                )
            else:
                node = Node(
                    name=cyst_node.id,
                    interfaces=interfaces,
                    image=node_image,
                    services=services,
                    environment=environment,
                    command=command,
                    healthcheck=healthcheck,
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
            if cyst_service.type in constants.IGNORE_SERVICES:
                continue
            service_image = (
                specified_image
                if (specified_image := constants.TESTBED_IMAGES.get(cyst_service.type)) is not None
                else constants.IMAGE_NODE
            )

            configuration = await self.get_service_configuration(cyst_service.type)
            environment = envs if (envs := constants.envs.get(cyst_service.type)) is not None else {}
            command = container[constants.COMMAND] if (container := constants.TESTBED_INFO.get(cyst_service.type)) else []

            try:  # TODO: unused
                depends_on = constants.TESTBED_INFO[cyst_service.id][constants.DEPENDS_ON]
            except KeyError:
                depends_on = {}

            try:
                healthcheck = constants.TESTBED_INFO[cyst_service.id][constants.HEALTHCHECK]
            except KeyError:
                healthcheck = dict()

            service = Service(
                name=cyst_service.type,
                image=service_image,
                environment=environment,
                command=command,
                healthcheck=healthcheck,
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
            firewall_rules = []

            for interface in cyst_router.interfaces:
                network = await self.find_network(interface.net)
                interfaces.append(Interface(ipaddress=network.router_gateway, network=network))

            router_type = "perimeter" if cyst_router.id == "perimeter_router" else "internal"

            # TODO: Better FirewallRule extraction if there will be different cyst configuration
            for firewall_rule in cyst_router.traffic_processors[0].chains[0].rules:
                destination = await self.find_network(firewall_rule.dst_net)
                source = await self.find_network(firewall_rule.src_net)
                firewall_rules.append(
                    FirewallRule(
                        src_net=source,
                        dst_net=destination,
                        service=firewall_rule.service,
                        policy=firewall_rule.policy.name,
                    )
                )

            router = Router(
                name=cyst_router.id,
                router_type=router_type,
                interfaces=interfaces,
                image=constants.IMAGE_ROUTER,
                firewall_rules=firewall_rules,
            )
            self.routers.append(router)

    # Old function for static infra from file
    async def parse(self, cyst_routers: list[RouterConfig], cyst_nodes: list[NodeConfig], attacker: NodeConfig):
        """
        Create all necessary models for infrastructure based on parsed objects from cyst prescription.
        :param attacker: node representing the attacker
        :param cyst_routers: router objects from cyst infrastructure
        :param cyst_nodes: node objects from cyst infrastructure
        :return:
        """
        logger.debug("Parsing cyst infrastructure description")
        await self.parse_networks(cyst_routers)
        await self.parse_routers(cyst_routers)
        await self.parse_nodes(cyst_nodes, attacker)
        await self.parse_images()
        logger.info("Completed parsing cyst infrastructure description")

    async def parse_cyst_output(self):
        """
        Create all necessary models for infrastructure based on parsed objects from cyst prescription.
        config_items: list of configurations from cyst
        :return:
        """
        logger.debug("Parsing cyst infrastructure description")

        cyst_routers = []
        cyst_nodes = []
        attacker = None

        for item in self.infrastructure_items:
            if type(item) is RouterConfig:
                cyst_routers.append(item)
            elif type(item) is NodeConfig:
                cyst_nodes.append(item)
                # TODO: needs better solution than "attacker" id
                if "attacker" in item.id:
                    attacker = item

        await self.parse_networks(cyst_routers)
        await self.parse_routers(cyst_routers)
        await self.parse_nodes(cyst_nodes, attacker)
        await self.parse_images()
        logger.info("Completed parsing cyst infrastructure description")

    @infrastructure_items.setter
    def infrastructure_items(self, value):
        self._infrastructure_items = value
