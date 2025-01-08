import asyncio
import copy
from asyncio import TaskGroup
from typing import Sequence
from uuid import uuid1

import docker
import randomname
from docker import DockerClient
from docker.errors import ImageNotFound, APIError, NotFound
from netaddr import IPNetwork
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dr_emu.controllers import template as template_controller, image as image_controller
from dr_emu.database_config import sessionmanager
from dr_emu.lib import util
from dr_emu.lib.logger import logger
from dr_emu.models import (
    Infrastructure,
    Network,
    Interface,
    Instance,
    Run,
    Node,
    Attacker,
    Dns,
    ServiceAttacker,
    Volume,
    Service,
    Router, ImageState
)
from dr_emu.settings import settings
from parser.cyst_parser import CYSTParser
from shared import constants

async_lock = asyncio.Lock()


class InfrastructureController:
    """
    Class for handling actions regarding creating and destroying the infrastructure in docker.
    """

    def __init__(self, infrastructure: Infrastructure):
        self.client = docker.from_env()
        self.infrastructure = infrastructure

    @staticmethod
    async def get_infra(infrastructure_id: int, db_session: AsyncSession):
        # Exception handled in outer function
        return (
            (await db_session.execute(select(Infrastructure).where(Infrastructure.id == infrastructure_id)))
            .unique()
            .scalar_one()
        )

    async def start(self):
        """
        Executes all necessary functions for building an infrastructure and saves created models to the database.
        :return:
        """
        logger.info("Starting infrastructure", name=self.infrastructure.name)

        create_volumes_tasks = await self.create_volumes()
        await asyncio.gather(*create_volumes_tasks)
        logger.debug("Networks created", infrastructure_name=self.infrastructure.name)

        create_network_tasks = await self.create_networks()
        await asyncio.gather(*create_network_tasks)
        logger.debug("Networks created", infrastructure_name=self.infrastructure.name)

        create_node_tasks = await self.create_nodes()
        await asyncio.gather(*create_node_tasks)
        logger.debug("Nodes created", infrastructure_name=self.infrastructure.name)

        start_router_tasks = await self.start_routers()
        start_node_tasks = await self.start_nodes()
        await asyncio.gather(*start_node_tasks, *start_router_tasks)
        logger.debug("Appliances started", infrastructure_name=self.infrastructure.name)

        configure_appliance_tasks: set[asyncio.Task[None]] = await self.configure_appliances()
        await asyncio.gather(*configure_appliance_tasks)
        logger.debug("Appliances configured", infrastructure_name=self.infrastructure.name)

        logger.info(
            "Created infrastructure",
            name=self.infrastructure.name,
        )

    async def create_networks(self) -> set[asyncio.Task[None]]:
        """
        Creates async tasks for creating networks.
        :return: set of tasks for network creation
        """
        logger.debug("Creating networks", infrastructure_name=self.infrastructure.name)
        return {asyncio.create_task(network.create()) for network in self.infrastructure.networks}

    async def start_routers(self) -> set[asyncio.Task[None]]:
        """
        Creates async tasks for creating and starting routers.
        :return: set of tasks to start router containers
        """
        logger.debug("Starting routers", infrastructure_name=self.infrastructure.name)
        return {asyncio.create_task(router.start()) for router in self.infrastructure.routers}

    async def create_nodes(self) -> set[asyncio.Task[None]]:
        """
        Creates async tasks for creating nodes.
        :return: set of tasks to create node containers
        """
        logger.debug("Creating nodes", infrastructure_name=self.infrastructure.name)
        return {asyncio.create_task(node.create()) for node in self.infrastructure.nodes}

    async def start_nodes(self) -> set[asyncio.Task[None]]:
        """
        Creates async tasks for starting nodes.
        :return: set of tasks to start node containers
        """
        logger.debug("Starting nodes", infrastructure_name=self.infrastructure.name)
        return {asyncio.create_task(node.start()) for node in self.infrastructure.nodes}

    async def create_volumes(self) -> set[asyncio.Task[None]]:
        """
        Creates async tasks for creating nodes.
        :return: set of tasks to create node containers
        """
        logger.debug("Creating volumes", infrastructure_name=self.infrastructure.name)
        return {asyncio.create_task(volume.create()) for volume in self.infrastructure.volumes}

    async def configure_appliances(self) -> set[asyncio.Task[None]]:
        """
        Create async tasks for configuring iptables and ip routes in Nodes and Routers.
        :return:
        """
        logger.debug("Configuring appliances", infrastructure_name=self.infrastructure.name)
        node_configure_tasks = {asyncio.create_task(node.configure()) for node in self.infrastructure.nodes}
        router_configure_tasks = {asyncio.create_task(router.configure()) for router in self.infrastructure.routers}

        logger.debug("Appliances configured", infrastructure_name=self.infrastructure.name)
        return node_configure_tasks.union(router_configure_tasks)

    async def stop(self, check_id: bool = False):
        """
        Stops and deletes all containers and networks in the infrastructure.
        :param check_id:=
        :return:
        """
        logger.debug(
            "Stopping infrastructure",
            name=self.infrastructure.name,
            id=self.infrastructure.id,
        )
        delete_nodes_tasks = await self.delete_nodes(check_id)
        delete_routers_tasks = await self.delete_routers(check_id)
        await asyncio.gather(*delete_nodes_tasks, *delete_routers_tasks)
        logger.debug(
            "Appliances deleted",
            infrastructure_name=self.infrastructure.name,
            infrastructure_id=self.infrastructure.id,
        )

        delete_network_tasks = await self.delete_networks(check_id)
        await asyncio.gather(*delete_network_tasks)
        logger.debug(
            "Networks deleted",
            infrastructure_name=self.infrastructure.name,
            infrastructure_id=self.infrastructure.id,
        )
        logger.debug(
            "Infrastructure stopped",
            name=self.infrastructure.name,
            id=self.infrastructure.id,
        )
        delete_volumes_tasks = await self.delete_volumes()
        await asyncio.gather(*delete_volumes_tasks)
        logger.debug(
            "Volumes deleted",
            infrastructure_name=self.infrastructure.name,
            infrastructure_id=self.infrastructure.id,
        )

    async def delete_networks(self, check_id: bool) -> set[asyncio.Task[None]]:
        """
        Creates async tasks for deletion of networks.
        :param check_id:
        :return: set of tasks for networks deletion
        """
        logger.debug(
            "Deleting networks",
            infrastructure_name=self.infrastructure.name,
            infrastructure_id=self.infrastructure.id,
        )
        network_tasks: set[asyncio.Task[None]] = set()
        for network in self.infrastructure.networks:
            if not check_id or (check_id and network.docker_id != ""):
                network_tasks.add(asyncio.create_task(network.delete()))
        return network_tasks

    async def delete_routers(self, check_id: bool) -> set[asyncio.Task[None]]:
        """
        Creates async tasks for deletion of routers.
        :param check_id:
        :return: set of tasks for deletion of routers
        """
        logger.debug(
            "Deleting routers",
            infrastructure_name=self.infrastructure.name,
            infrastructure_id=self.infrastructure.id,
        )
        router_tasks: set[asyncio.Task[None]] = set()
        for router in self.infrastructure.routers:
            if not check_id or (check_id and router.docker_id != ""):
                router_tasks.add(asyncio.create_task(router.delete()))
        return router_tasks

    async def delete_nodes(self, check_id: bool) -> set[asyncio.Task[None]]:
        """
        Creates async tasks for deletion of nodes.
        :param check_id:
        :return: set of tasks for deletion of nodes
        """
        logger.debug(
            "Deleting nodes",
            infrastructure_name=self.infrastructure.name,
            infrastructure_id=self.infrastructure.id,
        )
        node_tasks: set[asyncio.Task[None]] = set()
        for node in self.infrastructure.nodes:
            if not check_id or (check_id and node.docker_id != ""):
                node_tasks.add(asyncio.create_task(node.delete()))
        return node_tasks

    async def delete_volumes(self) -> set[asyncio.Task[None]]:
        logger.debug(
            "Deleting volumes",
            infrastructure_name=self.infrastructure.name,
            infrastructure_id=self.infrastructure.id,
        )
        volume_tasks: set[asyncio.Task[None]] = set()
        for volume in self.infrastructure.volumes:
            volume_tasks.add(asyncio.create_task(volume.delete()))
        return volume_tasks

    async def change_ipaddresses(self, available_networks: list[IPNetwork]):
        """
        Change ip addresses in models.
        :param available_networks: available ip addresses for networks
        :return:
        """
        logger.debug(
            "Changing IP adresses",
            name=self.infrastructure.name,
            id=self.infrastructure.id,
        )

        for network, available_network in zip(self.infrastructure.networks, available_networks):
            network.ipaddress = available_network

            for interface, new_ip in zip(network.interfaces, available_network.iter_hosts()):
                interface.ipaddress = new_ip
                if interface.appliance.type == "router" and "management" not in network.name:
                    network.router_gateway = new_ip

    @staticmethod
    async def update_environment_variables(containers: list[Service | Node | Router],
                                           name_pairs: dict[str, str]) -> None:
        for container in containers:
            if container.environment:
                for k, v in container.environment.items():
                    if v in name_pairs:
                        container.environment[k] = name_pairs[v]

    async def change_names(self, container_names: set[str], network_names: set[str], volumes: list[Volume]):
        """
        Change names in models for container name uniqueness.
        :param container_names: already used docker container names
        :param network_names: already used network container names
        :param volumes: already used volumes
        :return:
        """
        logger.debug(
            "Changing docker names to match the Infrastructure",
            infrastructure_name=self.infrastructure.name,
        )
        containers: list[Service | Node | Router] = [*self.infrastructure.nodes, *self.infrastructure.routers]
        name_pairs: dict[str, str] = {}
        for node in self.infrastructure.nodes:
            containers += node.service_containers

        for container in containers:
            if (new_name := f"{self.infrastructure.name}-{container.name}") in container_names:
                # if by some miracle container with infra color + container_name already exists on a system
                new_name += "-dr-emu"
            name_pairs[container.name] = new_name
            container.name = new_name
            container_names.add(new_name)

        await self.update_environment_variables(containers, name_pairs)
        for network in self.infrastructure.networks:
            if (new_name := f"{self.infrastructure.name}-{network.name}") in network_names:
                new_name += "-dr-emu"
            network.name = new_name
            network_names.add(new_name)
        for volume in volumes:
            if not volume.local:
                volume.name = f"{self.infrastructure.name}-{volume.name}"

    async def create_management_network(self, management_subnet: IPNetwork):
        used_network_names = await util.get_network_names(docker.from_env())

        if (management_name := f"{self.infrastructure.name}-management") in used_network_names:
            management_name += str(uuid1())

        management_network = Network(
            ipaddress=management_subnet,
            router_gateway=management_subnet[1],
            name=management_name,
            network_type=constants.NETWORK_TYPE_MANAGEMENT,
        )

        for router, ip_address in zip(self.infrastructure.routers, management_subnet[2:-2]):
            if router.router_type == constants.ROUTER_TYPE_PERIMETER:
                router.interfaces.append(
                    Interface(
                        ipaddress=management_network.router_gateway,
                        network=management_network,
                    )
                )
            else:
                router.interfaces.append(Interface(ipaddress=ip_address, network=management_network))

        self.infrastructure.networks.append(management_network)

    async def build_infrastructure(self, run: Run, db_session: AsyncSession) -> Instance:
        try:
            await self.start()
            return Instance(
                run=run,
                infrastructure=self.infrastructure,
            )
        except (ImageNotFound, APIError, RuntimeError, Exception) as error:
            logger.error(
                f"Deleting infrastructure due to {type(error).__name__}",
                infrastructure_name=self.infrastructure.name,
                exception=str(error),
            )
            # this is necessary for the specific infra where the exception was thrown, outer exception handling is for
            # other infras
            await self.stop()
            db_session.expire(self.infrastructure, ["networks", "routers", "nodes"])
            await db_session.delete(self.infrastructure)
            raise error

    @staticmethod
    async def prepare_controller_for_infra_creation(
            infrastructure: Infrastructure,
            available_networks: list[IPNetwork],
    ):
        """
        Creates a management network for routers and changes names and ip addresses of models for new infrastructure if
        needed.
        :param available_networks: IP addresses of networks that are available to use for building Infra
        :param infrastructure: Infrastructure object
        :return: Controller with prepared object for building a new infrastructure
        """
        logger.debug(
            "Preparing InfrastructureController",
            infrastructure_name=infrastructure.name,
            infrastructure_id=infrastructure.id,
        )

        controller = InfrastructureController(infrastructure)

        management_network = available_networks.pop()
        await controller.create_management_network(management_network)

        await asyncio.gather(controller.change_ipaddresses(available_networks))
        logger.debug(
            "IP addresses changed for new infrastructure",
            infrastructure_name=infrastructure.name,
            infrastructure_id=infrastructure.id,
        )

        return controller

    @staticmethod
    async def configure_dns(nodes: list[Node]):
        hosts = ""
        dns_node: Dns | None = None

        for node in nodes:
            if isinstance(node, Dns):
                dns_node = node
                continue
            for interface in node.interfaces:
                hosts += f"{str(interface.ipaddress)} {node.name}\n"
        if dns_node:
            for node in nodes:
                if not isinstance(node, (Dns, Attacker)):
                    node.kwargs["dns"] = [str(dns_node.interfaces[0].ipaddress)]

            updated_config = copy.deepcopy(constants.DNS_CONFIG).format(hosts)
            dns_node.config_instructions = [["sh", "-c", f"printf '{updated_config}' >> /etc/coredns/Corefile"]]

    @staticmethod
    async def ensure_image_exists(image_id: int, docker_client: DockerClient):
        async with sessionmanager.session() as db_session:
            image = await image_controller.get_image(image_id, db_session)
            logger.debug("Processing image state", image_name=image.name, state=image.state)
            if image.state == ImageState.ready:
                return
            try:
                if image.state == ImageState.building:
                    await image_controller.wait_until_image_is_ready(image, db_session)
                elif image.state == ImageState.initialized:
                    await util.get_image(docker_client, image, db_session)
                await db_session.commit()
            except Exception as err:
                logger.error("Failed to get image, deleting from DB", image_name=image.name, exception=str(err))
                raise err

    @staticmethod
    async def create_controller(
            infrastructure: Infrastructure,
            used_docker_networks: set[IPNetwork],
            parser: CYSTParser,
            docker_container_names: set[str],
            docker_network_names: set[str],
            db_session: AsyncSession,
            docker_client: DockerClient,
    ):

        async with async_lock:  # TODO: figure out how to make this work without async lock
            networks, routers, nodes, volumes, images = await parser.bake_models(db_session, infrastructure.name)
            try:
                async with TaskGroup() as tg:
                    for image in images:
                        tg.create_task(InfrastructureController.ensure_image_exists(image.id, docker_client))
            except Exception as err:  # TODO: find out what exception can happen here
                [await db_session.delete(image) for image in images]
                await db_session.delete(infrastructure)
                await db_session.commit()
                raise err

        infrastructure.networks, infrastructure.routers, infrastructure.nodes = networks, routers, nodes

        available_networks = await util.generate_infrastructure_subnets(
            infrastructure.supernet, list(parser.networks_ips), used_docker_networks
        )
        controller = await InfrastructureController.prepare_controller_for_infra_creation(
            available_networks=available_networks,
            infrastructure=infrastructure,
        )

        await InfrastructureController.configure_dns(nodes)

        await controller.change_names(
            container_names=docker_container_names, network_names=docker_network_names, volumes=volumes
        )
        logger.debug(
            "Docker names changed",
            infrastructure_name=infrastructure.name,
        )

        # TODO: Kinda hotfix for unique worker names
        for node in nodes:
            if isinstance(node, Attacker):
                for service in node.service_containers:
                    if isinstance(service, ServiceAttacker):
                        service.environment["CRYTON_WORKER_NAME"] = f"attacker_{infrastructure.name}_{service.name}"
                    elif "metasploit" in service.image.name:
                        service.environment["METASPLOIT_LHOST"] = str(node.interfaces[0].ipaddress)

        db_session.add(infrastructure)
        return controller

    @staticmethod
    async def build_infras(number_of_infrastructures: int, run: Run, db_session: AsyncSession) -> list[Instance]:
        """
        Builds docker infrastructure
        :param run: Run object
        :param number_of_infrastructures: Number of infrastructures to build
        :param db_session: Async database session
        :return:
        """

        docker_client = docker.from_env()
        used_docker_networks: set[IPNetwork] = set()
        # networks.list doesn't return same objects as networks.get
        docker_networks = await asyncio.to_thread(docker_client.networks.list)
        for docker_network in docker_networks:
            if docker_network.name in ["none", "host"]:
                continue
            used_docker_networks.add(
                IPNetwork(docker_client.networks.get(docker_network.id).attrs["IPAM"]["Config"][0]["Subnet"])
            )

        logger.info("Building infrastructures")
        controllers: list[InfrastructureController] = []

        # check if management (cryton) network exists
        if not settings.ignore_management_network:
            try:
                docker_client.networks.get(settings.management_network_name)
            except NotFound:
                raise RuntimeError(
                    f"Management Network containing Cryton '{settings.management_network_name}' not found"
                )

        used_docker_container_names = await util.get_container_names(docker_client)
        used_docker_network_names = await util.get_network_names(docker_client)

        template = await template_controller.get_template(run.template_id, db_session)
        parser = CYSTParser(template.description)
        await parser.parse()

        infrastructure_names: set[str] = set()
        infrastructures: list[Infrastructure] = []

        existing_infrastructures = (await db_session.scalars(select(Infrastructure))).all()
        used_infrastructure_supernets = {infra.supernet for infra in existing_infrastructures}
        used_infrastructure_names = {infra.name for infra in existing_infrastructures}
        available_infrastructure_supernets = await util.get_available_networks_for_infras(
            used_docker_networks,
            number_of_infrastructures,
            used_infrastructure_supernets,
        )

        for i in range(number_of_infrastructures):
            while (infra_name := randomname.generate("adj/colors", "n/astronomy")) in used_infrastructure_names:
                continue
            infrastructure_names.update(infra_name)
            infrastructures.append(Infrastructure(name=infra_name,
                                                  supernet=available_infrastructure_supernets[i],
                                                  nodes=[],
                                                  networks=[],
                                                  routers=[]))
        db_session.add_all(infrastructures)
        await db_session.commit()

        for infra in infrastructures:
            controllers.append(
                await InfrastructureController.create_controller(
                    infra,
                    used_docker_networks,
                    parser,
                    used_docker_container_names,
                    used_docker_network_names,
                    db_session,
                    docker_client
                )
            )

        build_infrastructure_tasks = {
            asyncio.create_task(controller.build_infrastructure(run, db_session)) for controller in controllers
        }

        instances = await asyncio.gather(*build_infrastructure_tasks, return_exceptions=True)
        exceptions: list[Exception] = []
        if any(isinstance(task, Exception) for task in instances):
            logger.error(
                "Deleting all instances due to exceptions in attempts to build all infrastructures",
            )
            for task in instances:
                if isinstance(task, Instance):
                    await InfrastructureController.stop_infra(task.infrastructure)
                    await db_session.delete(task.infrastructure)  # commits in outer function
                elif isinstance(task, Exception):
                    exceptions.append(task)
            raise ExceptionGroup("Failed to build infrastructures", exceptions)

        return instances

    @staticmethod
    async def stop_infra(infrastructure: Infrastructure):
        """
        Destroys docker infrastructure.
        :param infrastructure: Infrastructure object
        :return:
        """
        controller = InfrastructureController(infrastructure)

        # destroy docker objects
        await controller.stop()

    @staticmethod
    async def delete_infra(infrastructure: Infrastructure, db_session: AsyncSession):
        """
        Delete infrastructure and all models belonging to it (cascade deletion) from db.
        :param infrastructure: Infrastructure object
        :param db_session: Async database session
        :return:
        """
        logger.debug(
            "Deleting infrastructure",
            name=infrastructure.name,
            id=infrastructure.id,
        )

        await db_session.delete(infrastructure.instance)
        await db_session.commit()
        logger.debug(
            "Infrastructure deleted",
            name=infrastructure.name,
            id=infrastructure.id,
        )

    @staticmethod
    async def list_infrastructures(db_session: AsyncSession) -> Sequence[Infrastructure]:
        """
        Return names and Ids of all infrastructures in key:value -> id:name format
        :param db_session: Async database session
        :return:
        """
        logger.debug("Pulling infrastructures from db")

        return (await db_session.scalars(select(Infrastructure).options(joinedload(Infrastructure.instance)))).all()

    @staticmethod
    async def get_infra_info(infrastructure_id: int, db_session: AsyncSession) -> Infrastructure:
        """
        Parse info about infrastructure specified by ID.
        :param infrastructure_id: infrastructure ID
        :param db_session: Async database session
        :return: infrastructure description
        """
        logger.debug("Getting infrastructure info", id=infrastructure_id)

        infrastructure = (
            (
                await db_session.execute(
                    select(Infrastructure)
                    .where(Infrastructure.id == infrastructure_id)
                    .options(
                        joinedload(Infrastructure.instance),
                        joinedload(Infrastructure.routers),
                        joinedload(Infrastructure.networks).joinedload(Network.interfaces),
                        joinedload(Infrastructure.nodes).joinedload(Node.service_containers),
                    )
                )
            )
            .unique()
            .scalar_one()
        )

        return infrastructure
