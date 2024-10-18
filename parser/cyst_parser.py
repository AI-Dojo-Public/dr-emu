import randomname
from netaddr import IPNetwork
from uuid import uuid1
from packaging.version import Version
from dataclasses import asdict
import copy
from cyst.api.configuration import (
    ExploitConfig,
    RouterConfig,
    NodeConfig,
    ActiveServiceConfig,
    PassiveServiceConfig,
)
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.environment import Environment

from shared import constants
from dr_emu.lib.logger import logger

from parser.lib.simple_models import Network, Interface, FirewallRule, Router, Service, Node, NodeType
from dr_emu.models import (
    Network as DockerNetwork,
    Interface as DockerInterface,
    FirewallRule as DockerFirewallRule,
    Router as DockerRouter,
    Service as DockerService,
    ServiceAttacker as DockerServiceAttacker,
    Node as DockerNode,
    Attacker as DockerAttacker,
    Dns as DockerDns,
    DependsOn as DockerDependsOn,
    Volume
)
from parser.lib import containers


class CYSTParser:
    def __init__(self, infrastructure_description: str):
        self.infrastructure = self._load_infrastructure_description(infrastructure_description)
        self.networks: list[Network] = list()
        self.routers: list[Router] = list()
        self.nodes: list[Node] = list()

    @staticmethod
    def _load_infrastructure_description(description: str) -> list[ConfigItem]:
        """
        Load CYST configuration from pickled template.
        :param description: CYST infrastructure description
        :return: CYST configuration
        """
        # SECURITY VULNERABILITY, EXECUTES PYTHON CODE FROM USER INPUT
        return Environment.create().configuration.general.load_configuration(description)

    @property
    def networks_ips(self) -> set[IPNetwork]:
        return {network.subnet for network in self.networks}

    @property
    def docker_images(self) -> set[str]:
        images: set[str] = set()
        for router in self.routers:
            images.add(router.container.image)
        for node in self.nodes:
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
        for network in self.networks:
            if network.subnet == subnet:
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
                if not any(interface.net == network.subnet for network in self.networks):
                    while (network_name := randomname.generate("nouns/astronomy")) in generated_names:
                        continue

                    generated_names.add(network_name)
                    network_type = (
                        constants.NETWORK_TYPE_PUBLIC
                        if cyst_router.id == "perimeter_router"
                        else constants.NETWORK_TYPE_INTERNAL
                    )
                    subnet = IPNetwork(interface.net.cidr)
                    logger.debug(
                        "Adding network", name=network_name, type=network_type, ip=subnet, gateway=interface.ip
                    )
                    self.networks.append(Network(network_name, network_type, subnet, interface.ip))

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
            services, service_tags = await self._parse_services(cyst_node.active_services + cyst_node.passive_services)

            node_type = NodeType.DEFAULT
            if len(cyst_node.active_services) > 0:
                node_type = NodeType.ATTACKER
            elif "dns" in cyst_node.id or "dns" in [service.type for service in cyst_node.passive_services]:
                node_type = NodeType.DNS

            logger.debug("Adding node", id=cyst_node.id, services=[service.container.image for service in services],
                         service_tags=service_tags)
            # TODO: Figure out how to match node containers while not breaking the node-service architecture
            node_container = await containers.match_node_container(service_tags)
            self.nodes.append(Node(cyst_node.id, interfaces, node_container, service_tags, services, node_type))

    async def _parse_services(self, node_services: list[PassiveServiceConfig | ActiveServiceConfig]) -> tuple[
        list[Service], list[containers.ServiceTag]]:
        """
        Create service models from nodes in cyst infrastructure prescription.
        :param node_services: node objects from cyst infrastructure
        :return:
        """
        service_tags: list[containers.ServiceTag] = []
        for node_service in node_services:
            match node_service:
                case ActiveServiceConfig():
                    service_tags.append(containers.ServiceTag(node_service.type))
                case PassiveServiceConfig():
                    service_tags.append(containers.ServiceTag(node_service.type, node_service.version))

        return ([Service(str(uuid1()), container) for container in
                 await containers.match_service_container(service_tags)], service_tags)

    async def _parse_routers(self, cyst_routers: list[RouterConfig]):
        """
        Create router models from nodes in cyst infrastructure prescription.
        :param cyst_routers: router objects from cyst infrastructure
        :return:
        """
        for cyst_router in cyst_routers:
            router_type = "perimeter" if cyst_router.id == "perimeter_router" else "internal"
            interfaces: list[Interface] = list()
            firewall_rules: list[FirewallRule] = list()

            for interface in cyst_router.interfaces:
                network = await self._find_network(interface.net)
                # TODO: remove later; Router is now also Switch in CYST Core
                if not any(network.gateway == i.ip for i in interfaces) and interface.index not in [router_config.port for router_config in cyst_router.routing_table]:
                    interfaces.append(Interface(network.gateway, network))

            # TODO: Better FirewallRule extraction if there will be different cyst configuration
            for firewall_rule in cyst_router.traffic_processors[0].chains[0].rules:
                destination = await self._find_network(firewall_rule.dst_net)
                source = await self._find_network(firewall_rule.src_net)
                firewall_rules.append(
                    FirewallRule(source, destination, firewall_rule.service, firewall_rule.policy.name)
                )

            logger.debug("Adding router", id=cyst_router.id, type=router_type)
            self.routers.append(Router(cyst_router.id, router_type, interfaces, containers.ROUTER, firewall_rules))

    async def _parse_exploits(self, exploits: list[ExploitConfig]):
        all_service_tags = [service for node in self.nodes for service in node.service_tags]

        for exploit in exploits:
            for vuln_service in exploit.services:
                for service_tag in all_service_tags:
                    if service_tag.type == vuln_service.name and (
                            Version(vuln_service.min_version) <= Version(service_tag.version) <= Version(
                        vuln_service.max_version)):
                        service_tag.exploits.add("cve_placeholder")

    async def _resolve_dependencies(self):
        all_services = [service for node in self.nodes for service in node.services]
        for service in all_services:
            if service_requirements := service.container.requires:
                for possible_service in all_services:
                    if (met_requirements := possible_service.container.tag) in service_requirements:
                        service.depends_on.append(possible_service)
                        service_requirements.append(met_requirements)
                        if not service_requirements:
                            break

    async def bake_models(self) -> tuple[list[DockerNetwork], list[DockerRouter], list[DockerNode], list[Volume]]:
        """
        Create linked database models for the parsed infrastructure.
        :return: Network, Router, and Node models
        """
        networks: dict[str, DockerNetwork] = dict()
        routers: dict[str, DockerRouter] = dict()
        nodes: dict[str, DockerNode] = dict()
        volumes: dict[str, Volume] = dict()

        # Build DB of Docker networks
        for network in self.networks:
            networks[network.name] = DockerNetwork(
                ipaddress=network.subnet,
                router_gateway=network.gateway,
                name=network.name,
                network_type=network.type,
            )

        # Build DB of Docker containers (routers)
        for router in self.routers:
            interfaces: list[DockerInterface] = list()
            firewall_rules: list[DockerFirewallRule] = list()
            for interface in router.interfaces:
                interfaces.append(
                    DockerInterface(
                        ipaddress=interface.ip, original_ip=interface.ip, network=networks[interface.network.name]
                    )
                )
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

        # Build DB of Docker containers (nodes and services)
        all_docker_services: list[DockerService] = list()
        for node in self.nodes:
            services: list[DockerService] = list()
            interfaces: list[DockerInterface] = list()
            for service in node.services:
                service_type = DockerServiceAttacker if service.container.is_attacker else DockerService
                service_model = service_type(
                    name=service.name,
                    image=service.container.image,
                    environment=copy.deepcopy(service.container.environment),
                    command=service.container.command,
                    healthcheck=service.container.healthcheck,
                    kwargs=copy.deepcopy(service.container.kwargs)
                )
                services.append(service_model)
                for volume in service.container.volumes:
                    if volume.name in volumes:
                        service_model.volumes.append(volumes[volume.name])
                    else:
                        volume = Volume(name=volume.name, bind=volume.bind, local=volume.local)
                        volume.services.append(service_model)
                        volumes[volume.name] = volume

            all_docker_services += services
            for interface in node.interfaces:
                interfaces.append(
                    DockerInterface(
                        ipaddress=interface.ip, original_ip=interface.ip, network=networks[interface.network.name]
                    )
                )

            node_model = node.type.value(
                name=node.name,
                interfaces=interfaces,
                image=node.container.image,
                services=services,
                service_tags=[asdict(service_tag) for service_tag in node.service_tags],
                environment=copy.deepcopy(node.container.environment),
                command=node.container.command,
                healthcheck=node.container.healthcheck,
                config_instructions=[],
                kwargs=copy.deepcopy(node.container.kwargs),
            )
            for volume in node.container.volumes:
                if volume.name in volumes:
                    node_model.volumes.append(volumes[volume.name])
                else:
                    volume = Volume(name=volume.name, bind=volume.bind, local=volume.local)
                    volume.appliances.append(node_model)
                    volumes[volume.name] = volume
            nodes[node.name] = node_model
        # Update DB with Docker containers' dependencies
        all_services = [service for node in self.nodes for service in node.services]
        for service in all_services:
            if not service.depends_on:
                continue

            docker_service = next(ds for ds in all_docker_services if ds.name == service.name)
            for dependency in service.depends_on:
                docker_dependency = next(dd for dd in all_docker_services if dd.name == dependency.name)
                docker_service.dependencies.append(
                    DockerDependsOn(dependency=docker_dependency, state=constants.SERVICE_STARTED)
                )

        return list(networks.values()), list(routers.values()), list(nodes.values()), list(volumes.values())

    async def parse(self):
        """
        Create all necessary models for infrastructure based on parsed objects from cyst prescription.
        :return: None
        """
        logger.debug("Parsing cyst infrastructure description")

        cyst_routers: list[RouterConfig] = list()
        cyst_nodes: list[NodeConfig] = list()
        exploits: list[ExploitConfig] = list()

        for item in self.infrastructure:
            match item:
                case RouterConfig():
                    item: RouterConfig
                    cyst_routers.append(item)
                case NodeConfig():
                    item: NodeConfig
                    cyst_nodes.append(item)
                case ExploitConfig():
                    item: ExploitConfig
                    exploits.append(item)

        await self._parse_networks(cyst_routers)
        await self._parse_routers(cyst_routers)
        await self._parse_nodes(cyst_nodes)
        await self._parse_exploits(exploits)
        await self._resolve_dependencies()
        logger.info("Completed parsing cyst infrastructure description")
