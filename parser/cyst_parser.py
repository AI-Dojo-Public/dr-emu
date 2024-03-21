import randomname
from netaddr import IPNetwork
from uuid import uuid1

from cyst.api.configuration import (
    RouterConfig,
    NodeConfig,
    ActiveServiceConfig,
    PassiveServiceConfig,
    ExploitConfig,
    ConnectionConfig,
)
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.environment import Environment

from dr_emu.lib.logger import logger
from parser.util import constants
from parser.lib.simple_models import Network, Interface, FirewallRule, Router, Service, Node
from dr_emu.models import (
    Network as DockerNetwork,
    Interface as DockerInterface,
    FirewallRule as DockerFirewallRule,
    Router as DockerRouter,
    Service as DockerService,
    Node as DockerNode,
)
from parser.lib import containers


class CYSTParser:
    # TODO: once the CYST Core gets fixed, replace with this
    # def __init__(self, infrastructure_description: str):
    #     self._infrastructure = self._load_infrastructure_description(infrastructure_description)
    def __init__(self, infrastructure: list[RouterConfig | NodeConfig | ExploitConfig | ConnectionConfig]):
        self._infrastructure = infrastructure
        self._networks: list[Network] = list()
        self._routers: list[Router] = list()
        self._nodes: list[Node] = list()

    @staticmethod
    def _load_infrastructure_description(description: str) -> list[ConfigItem]:
        """
        Load CYST configuration from pickled template.
        :param description: CYST infrastructure description
        :return: CYST configuration
        """
        # SECURITY VULNERABILITY, EXECUTES PYTHON CODE FROM USER INPOUT
        return Environment.create().configuration.general.load_configuration(description)

    @property
    def networks_ips(self) -> set[IPNetwork]:
        return {network.ip_address for network in self._networks}

    @property
    def docker_images(self) -> set[str]:
        images: set[str] = set()
        for router in self._routers:
            images.add(router.container.image)
        for node in self._nodes:
            images.add(node.container.image)
            for service in node.services:
                images.add(service.container.image)

        logger.debug(f"Listing used images", images=images)
        return images

    async def _find_network(self, subnet: IPNetwork) -> Network:
        """
        Find network object matching the subnet ip address.
        :param subnet: network ip address
        :return: Network object
        """
        for network in self._networks:
            if network.ip_address == subnet:
                return network

        raise RuntimeError(f"No network matching {subnet}.")

    async def _parse_networks(self, cyst_routers: list[RouterConfig]):
        """
        Create network models from cyst infrastructure prescription.
        :param cyst_routers: router objects from cyst infrastructure
        :return:
        """
        generated_names = set()
        for cyst_router in cyst_routers:
            for interface in cyst_router.interfaces:
                if not any(interface.net == network.ip_address for network in self._networks):
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
                    logger.debug(
                        "Adding network", name=network_name, type=network_type, net=interface.net, ip=interface.ip
                    )
                    self._networks.append(Network(network_name, network_type, interface.net, interface.ip))

    async def _parse_nodes(self, cyst_nodes: list[NodeConfig]):
        """
        Create node models from cyst infrastructure prescription.
        :param cyst_nodes: node objects from cyst infrastructure
        :return:
        """
        for cyst_node in cyst_nodes:
            interfaces = [
                Interface(interface.ip, await self._find_network(interface.net)) for interface in cyst_node.interfaces
            ]
            services = await self._parse_services(cyst_node.active_services + cyst_node.passive_services)

            logger.debug("Adding node", id=cyst_node.id, services=[service.container.image for service in services])
            self._nodes.append(Node(cyst_node.id, interfaces, containers.DEFAULT, services))

    async def _parse_services(self, node_services: list[PassiveServiceConfig | ActiveServiceConfig]) -> list[Service]:
        """
        Create service models from nodes in cyst infrastructure prescription.
        :param node_services: node objects from cyst infrastructure
        :return:
        """
        match_rules = set()
        for node_service in node_services:
            match node_service:
                case ActiveServiceConfig():
                    match_rules.add(containers.ServiceTag(node_service.type))
                case PassiveServiceConfig():
                    match_rules.add(containers.ServiceTag(node_service.type, node_service.version))

        return [Service(str(uuid1()), container) for container in containers.match(match_rules)]

    async def _parse_routers(self, cyst_routers: list[RouterConfig]):
        """
        Create router models from nodes in cyst infrastructure prescription.
        :param cyst_routers: router objects from cyst infrastructure
        :return:
        """
        for cyst_router in cyst_routers:
            router_type = "perimeter" if cyst_router.id == "perimeter_router" else "internal"
            interfaces = list()
            firewall_rules = list()

            for interface in cyst_router.interfaces:
                network = await self._find_network(interface.net)
                interfaces.append(Interface(network.gateway, network))

            # TODO: Better FirewallRule extraction if there will be different cyst configuration
            for firewall_rule in cyst_router.traffic_processors[0].chains[0].rules:
                destination = await self._find_network(firewall_rule.dst_net)
                source = await self._find_network(firewall_rule.src_net)
                firewall_rules.append(
                    FirewallRule(source, destination, firewall_rule.service, firewall_rule.policy.name)
                )

            logger.debug("Adding router", id=cyst_router.id, type=router_type)
            self._routers.append(Router(cyst_router.id, router_type, interfaces, containers.ROUTER, firewall_rules))

    async def bake_models(self) -> tuple[list[DockerNetwork], list[DockerRouter], list[DockerNode]]:
        """
        Create linked database models for the parsed infrastructure.
        :return: Network, Router, and Node models
        """
        networks: dict[str, DockerNetwork] = dict()
        routers: dict[str, DockerRouter] = dict()
        nodes: dict[str, DockerNode] = dict()

        for network in self._networks:
            networks[network.name] = DockerNetwork(
                ipaddress=network.ip_address,
                router_gateway=network.gateway,
                name=network.name,
                network_type=network.type,
            )

        for router in self._routers:
            interfaces: list[DockerInterface] = list()
            firewall_rules: list[DockerFirewallRule] = list()
            router_interface_ips = set()
            for interface in router.interfaces:
                if interface.ip_address not in router_interface_ips:
                    interfaces.append(
                        DockerInterface(ipaddress=interface.ip_address, network=networks[interface.network.name])
                    )
                    router_interface_ips.add(interface.ip_address)
            for firewall_rule in router.firewall_rules:
                firewall_rules.append(
                    DockerFirewallRule(
                        src_net=networks[firewall_rule.source.name],
                        dst_net=networks[firewall_rule.destination.name],
                        service=firewall_rule.service,
                        policy=firewall_rule.policy,
                    )
                )

            routers[router.name] = DockerRouter(
                name=router.name,
                router_type=router.type,
                interfaces=interfaces,
                image=router.container.image,
                firewall_rules=firewall_rules,
            )

        for node in self._nodes:
            services: list[DockerService] = list()
            interfaces: list[DockerInterface] = list()
            for service in node.services:
                services.append(
                    DockerService(
                        name=service.name,
                        image=service.container.image,
                        environment=service.container.environment,
                        command=service.container.command,
                        healthcheck=service.container.healthcheck,
                    )
                )
            for interface in node.interfaces:
                interfaces.append(
                    DockerInterface(ipaddress=interface.ip_address, network=networks[interface.network.name])
                )

            nodes[node.name] = DockerNode(
                name=node.name,
                interfaces=interfaces,
                image=node.container.image,
                services=services,
                environment=node.container.environment,
                command=node.container.command,
                healthcheck=node.container.healthcheck,
            )

        return list(networks.values()), list(routers.values()), list(nodes.values())

    async def parse(self):
        """
        Create all necessary models for infrastructure based on parsed objects from cyst prescription.
        :return: None
        """
        logger.debug("Parsing cyst infrastructure description")

        cyst_routers: list[RouterConfig] = list()
        cyst_nodes: list[NodeConfig] = list()
        for item in self._infrastructure:
            match item:
                case RouterConfig():
                    item: RouterConfig
                    cyst_routers.append(item)
                case NodeConfig():
                    item: NodeConfig
                    cyst_nodes.append(item)

        await self._parse_networks(cyst_routers)
        await self._parse_routers(cyst_routers)
        await self._parse_nodes(cyst_nodes)
        logger.info("Completed parsing cyst infrastructure description")
