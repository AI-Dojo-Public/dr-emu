import copy
from typing import Sequence
from uuid import uuid1

import cif
import randomname
from cyst.api.configuration import (
    ExploitConfig,
    RouterConfig,
    NodeConfig,
    ActiveServiceConfig,
    PassiveServiceConfig,
    DataConfig,
)
from cyst.api.configuration.configuration import ConfigItem
from cyst.api.environment.environment import Environment
from netaddr import IPNetwork
from sqlalchemy.ext.asyncio import AsyncSession

from dr_emu.controllers import image as image_controller
from dr_emu.lib.logger import logger
from dr_emu.models import (
    Network as DockerNetwork,
    Interface as DockerInterface,
    FirewallRule as DockerFirewallRule,
    Router as DockerRouter,
    ServiceContainer as DockerService,
    ServiceAttacker as DockerServiceAttacker,
    Node as DockerNode,
    Image as ImageModel,
    Service as ServiceModel,
    Volume,
)
from parser.lib import containers
from parser.lib.simple_models import (
    Network,
    Interface,
    FirewallRule,
    Router,
    Node,
    NodeType,
    Image,
    Service,
    FileDescription,
)
from shared import constants


class CYSTParser:
    def __init__(self, infrastructure_description: str):
        self.infrastructure = self._load_infrastructure_description(infrastructure_description)
        self.networks: list[Network] = list()
        self.routers: list[Router] = list()
        self.nodes: list[Node] = list()
        self.docker_images: set[Image] = {containers.IMAGE_DEFAULT}

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

    async def create_image(
        self, services: list[Service], data_configurations: list[DataConfig], available_cif_services: list[str]
    ) -> Image:
        firehole_config = ""  # TODO
        packages: set[str] = set()
        actual_services: list[Service] = list()
        for service in services:
            if service.type in available_cif_services:
                actual_services.append(service)
                if service.type in containers.EXPLOITS:
                    firehole_config = containers.EXPLOITS[service.type]
            else:
                packages.add(service.type)

        image_data = set()
        for data_config in data_configurations:
            image_data.add(FileDescription(contents=data_config.description, image_file_path=data_config.id))
        image = Image(
            name=f"dr_emu_{(str(uuid1())).replace('-', '')}",
            services=tuple(services),
            firehole_config=firehole_config,
            packages=packages,
            data=image_data,
        )
        if image in self.docker_images:
            return image

        self.docker_images.add(image)
        return image

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

    async def _parse_nodes(self, cyst_nodes: list[NodeConfig], exploits: list[ExploitConfig]):
        """
        Create node models from cyst infrastructure prescription.
        :param cyst_nodes: node objects from cyst infrastructure
        :return:
        """
        available_cif_services = [service[0] for service in cif.available_services()]
        for cyst_node in cyst_nodes:
            interfaces = [
                Interface(interface.ip, await self._find_network(interface.net)) for interface in cyst_node.interfaces
            ]

            if cyst_node.id in containers.NODES:
                node = copy.deepcopy(containers.NODES[cyst_node.id])
                node.interfaces = interfaces
                self.nodes.append(node)
                self.docker_images.add(node.image)
                for service_container in node.service_containers:
                    self.docker_images.add(service_container.image)
                logger.debug("Adding node", id=cyst_node.id, interfaces=interfaces)
                continue

            vulnerable_services = set()
            for exploit in exploits:
                for vuln_service in exploit.services:
                    vulnerable_services.add(vuln_service.service)
            data_configurations = []
            services = await self._parse_services(
                cyst_node.active_services + cyst_node.passive_services, vulnerable_services, data_configurations
            )

            image = await self.create_image(
                services=services,
                data_configurations=data_configurations,
                available_cif_services=available_cif_services,
            )
            node_type = NodeType.DEFAULT
            if len(cyst_node.active_services) > 0:
                node_type = NodeType.ATTACKER

            logger.debug("Adding node", id=cyst_node.id, services=services, interfaces=interfaces)
            self.nodes.append(Node(image=image, name=cyst_node.id, interfaces=interfaces, type=node_type))

    async def _parse_services(
        self,
        node_services: set[PassiveServiceConfig | ActiveServiceConfig],
        vulnerable_services: set[str],  # Not implemented yet
        data_configs: list[DataConfig],
    ) -> list[Service]:
        """
        Create service models from nodes in cyst infrastructure prescription.
        :param node_services: node objects from cyst infrastructure
        :return:´´
        """
        services: list[Service] = []

        for node_service in node_services:
            match node_service:
                case ActiveServiceConfig():
                    if node_service.type not in containers.SERVICES:
                        raise NotImplementedError(f"ActiveService {node_service.type} is not supported.")
                    services.append(containers.SERVICES[node_service.type])
                case PassiveServiceConfig():
                    for data_config in node_service.private_data:
                        data_configs.append(data_config)
                    # TODO: temporary solution instead of `vulnerable_services`
                    # TODO: wait for cve implementation
                    cves = "cve_placeholder;" if node_service.name in containers.EXPLOITS else ""
                    if node_service.name in containers.SERVICES:
                        service = containers.SERVICES[node_service.name]
                    else:
                        service = Service(type=node_service.name, version=node_service.version, cves=cves)
                    services.append(service)

        return services

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
                if not any(network.gateway == i.ip for i in interfaces):
                    interfaces.append(Interface(network.gateway, network))

            # TODO: Better FirewallRule extraction if there will be different cyst configuration
            for firewall_rule in cyst_router.traffic_processors[0].chains[0].rules:
                destination = await self._find_network(firewall_rule.dst_net)
                source = await self._find_network(firewall_rule.src_net)
                firewall_rules.append(
                    FirewallRule(source, destination, firewall_rule.service, firewall_rule.policy.name)
                )

            logger.debug("Adding router", id=cyst_router.id, type=router_type)
            self.routers.append(
                Router(
                    image=containers.IMAGE_DEFAULT,
                    name=cyst_router.id,
                    type=router_type,
                    interfaces=interfaces,
                    firewall_rules=firewall_rules,
                )
            )

    async def _parse_exploits(self, exploits: list[ExploitConfig], service: Service) -> None:
        for exploit in exploits:
            for vuln_service in exploit.services:
                if service.type == vuln_service.name:
                    # if service.version and (Version(vuln_service.min_version) <= Version(service.version) <= Version(vuln_service.max_version)):
                    service.cves += "cve_placeholder;"

    # async def _resolve_dependencies(self): # TODO:
    #     all_services = [service for node in self.nodes for service in node.image.services]
    #     for service in all_services:
    #         if service_requirements := service.requires:
    #             for possible_service in all_services:
    #                 if met_requirements := possible_service.container.services.intersection(service_requirements):
    #                     service.depends_on.append(possible_service)
    #                     service_requirements.difference_update(met_requirements)
    #                     if not service_requirements:
    #                         break

    async def bake_models(
        self, db_session: AsyncSession, infrastructure_name: str
    ) -> tuple[list[DockerNetwork], list[DockerRouter], list[DockerNode], list[Volume], list[ImageModel]]:
        """
        Create linked database models for the parsed infrastructure.
        :return: Network, Router, and Node models
        """
        networks: dict[str, DockerNetwork] = dict()
        routers: dict[str, DockerRouter] = dict()
        nodes: dict[str, DockerNode] = dict()
        volumes: dict[str, Volume] = dict()
        image_models: list[ImageModel] = []

        # Build DB of Docker networks
        for network in self.networks:
            networks[network.name] = DockerNetwork(
                ipaddress=network.subnet,
                router_gateway=network.gateway,
                name=network.name,
                network_type=network.type,
            )

        logger.info("Creating infra images", infra_name=infrastructure_name)

        db_images = await image_controller.list_images(db_session)
        await self.bake_router_models(routers, networks, db_images, image_models)
        await self.bake_node_models(nodes, volumes, networks, db_images, image_models)

        # Add new images
        for new_image in image_models:
            if new_image not in db_images:
                db_session.add(new_image)
        logger.debug("Saving new images to db", infra_name=infrastructure_name)
        await db_session.commit()

        # TODO: are dependencies necessary now?
        # Update DB with Docker containers' dependencies
        # all_services = [service for node in self.nodes for service in node.services]
        # for service in all_services:
        #     if not service.depends_on:
        #         continue
        #
        #     docker_service = next(ds for ds in all_docker_services if ds.name == service.name)
        #     for dependency in service.depends_on:
        #         docker_dependency = next(dd for dd in all_docker_services if dd.name == dependency.name)
        #         docker_service.dependencies.append(
        #             DockerDependsOn(dependency=docker_dependency, state=constants.SERVICE_STARTED)
        #         )
        return (
            list(networks.values()),
            list(routers.values()),
            list(nodes.values()),
            list(volumes.values()),
            [*db_images, *image_models],
        )

    async def bake_router_models(self, routers, networks, db_images, image_models) -> None:
        # Build DB of Docker containers (routers)
        image_model = await self.bake_image_model(containers.IMAGE_DEFAULT, db_images, image_models)

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
                image=image_model,
                firewall_rules=firewall_rules,
            )

    @staticmethod
    async def bake_image_model(
        simple_image: Image, db_images: Sequence[ImageModel], image_models: list[ImageModel]
    ) -> ImageModel:
        service_models = set()
        for service in simple_image.services:
            service_models.add(
                ServiceModel(
                    type=service.type,
                    variable_override=service.variable_override,
                    version=service.version,
                    cves=service.cves,
                )
            )
        image = ImageModel(
            services=service_models,
            firehole_config=simple_image.firehole_config,
            pull=simple_image.pull,
            name=simple_image.name,
            data=[data_description for data_description in simple_image.data],
            packages=list(simple_image.packages),
        )
        created_images = [*db_images, *image_models]
        if image in created_images:
            return created_images[created_images.index(image)]

        image_models.append(image)
        return image

    async def bake_volumes(self, container_model, container_simple_volumes, infra_volumes):
        for simple_volume in container_simple_volumes:
            if simple_volume.name in infra_volumes:
                container_model.volumes.append(infra_volumes[simple_volume.name])
            else:
                volume = Volume(name=simple_volume.name, bind=simple_volume.bind, local=simple_volume.local)
                container_model.volumes.append(volume)
                infra_volumes[volume.name] = volume

    async def bake_node_models(self, nodes, volumes, networks, db_images, image_models) -> None:
        """
        Create all necessary models for infrastructure based on parsed objects from cyst prescription.
        :return: None
        """
        # Build DB of Docker containers (nodes and services)
        all_docker_services: list[DockerService] = list()

        for node in self.nodes:
            services: list[DockerService] = list()
            interfaces: list[DockerInterface] = list()
            for service_container in node.service_containers:
                service_image = await self.bake_image_model(service_container.image, db_images, image_models)
                service_type = DockerServiceAttacker if service_container.is_attacker else DockerService
                service_container_model = service_type(
                    name=str(uuid1()),
                    image=service_image,
                    environment=copy.deepcopy(service_container.environment),
                    command=service_container.command,
                    healthcheck=service_container.healthcheck,
                    kwargs=copy.deepcopy(service_container.kwargs),
                )
                services.append(service_container_model)
                await self.bake_volumes(service_container_model, service_container.volumes, volumes)

            all_docker_services += services
            for interface in node.interfaces:
                interfaces.append(
                    DockerInterface(
                        ipaddress=interface.ip, original_ip=interface.ip, network=networks[interface.network.name]
                    )
                )
            image_model = await self.bake_image_model(node.image, db_images, image_models)
            node_model = node.type.value(
                name=node.name,
                interfaces=interfaces,
                image=image_model,
                service_containers=services,
                environment=copy.deepcopy(node.environment),
                command=node.command,
                healthcheck=node.healthcheck,
                config_instructions=[],
                kwargs=copy.deepcopy(node.kwargs),
            )
            await self.bake_volumes(node_model, node.volumes, volumes)
            nodes[node.name] = node_model

    async def parse(self) -> None:
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
        await self._parse_nodes(cyst_nodes, exploits)
        # await self._resolve_dependencies()
        logger.info("Completed parsing cyst infrastructure description")
