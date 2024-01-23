import asyncio
from typing import Union, Optional, Sequence

import randomname
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
import docker
from docker.errors import ImageNotFound, APIError, NullResource
from netaddr import IPNetwork
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload

from parser.util import util, constants
from dr_emu.lib.logger import logger
from dr_emu.models import (
    Infrastructure,
    Network,
    Interface,
    Instance,
    Run,
    Node,
    Service,
    DependsOn,
)
from dr_emu.schemas.infrastructure import (
    InfrastructureInfo,
    NetworkSchema,
    ApplianceSchema,
    InfrastructureSchema,
)

from parser.cyst_parser import CYSTParser

from cyst_infrastructure import nodes as cyst_nodes, routers as cyst_routers, attacker


class InfrastructureController:
    """
    Class for handling actions regarding creating and destroying the infrastructure in docker.
    """

    def __init__(
        self,
        client: docker.DockerClient,
        images: set,
        infrastructure: Optional[Infrastructure] = None,
    ):
        self.client = client
        self.images = images
        self.infrastructure = infrastructure

    @staticmethod
    async def get_infra(infrastructure_id, db_session: AsyncSession):
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

        create_network_tasks = await self.create_networks()
        await asyncio.gather(*create_network_tasks)
        logger.debug("Networks created", infrastructure_id=self.infrastructure.id)

        create_node_tasks = await self.create_nodes()
        await asyncio.gather(*create_node_tasks)
        logger.debug("Nodes created", infrastructure_id=self.infrastructure.id)

        start_router_tasks = await self.start_routers()
        start_node_tasks = await self.start_nodes()
        await asyncio.gather(*start_node_tasks, *start_router_tasks)
        logger.debug("Appliances started", infrastructure_id=self.infrastructure.id)

        configure_appliance_tasks = await self.configure_appliances()
        await asyncio.gather(*configure_appliance_tasks)
        logger.debug("Appliances configured", infrastructure_id=self.infrastructure.id)

        logger.info(
            "Created infrastructure",
            id=self.infrastructure.id,
            name=self.infrastructure.name,
        )

    async def create_networks(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating networks.
        :return: set of tasks for network creation
        """
        logger.debug("Creating networks", infrastructure_id=self.infrastructure.id)
        return {asyncio.create_task(network.create()) for network in self.infrastructure.networks}

    async def start_routers(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating and starting routers.
        :return: set of tasks to start router containers
        """
        logger.debug("Starting routers", infrastructure_id=self.infrastructure.id)
        return {asyncio.create_task(router.start()) for router in self.infrastructure.routers}

    async def create_nodes(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating nodes.
        :return: set of tasks to create node containers
        """
        logger.debug("Creating nodes", infrastructure_id=self.infrastructure.id)
        return {asyncio.create_task(node.create()) for node in self.infrastructure.nodes}

    async def start_nodes(self) -> set[asyncio.Task]:
        """
        Creates async tasks for starting nodes.
        :return: set of tasks to start node containers
        """
        logger.debug("Starting nodes", infrastructure_id=self.infrastructure.id)
        return {asyncio.create_task(node.start()) for node in self.infrastructure.nodes}

    async def configure_appliances(self) -> set[asyncio.Task]:
        """
        Create async tasks for configuring iptables and ip routes in Nodes and Routers.
        :return:
        """
        logger.debug("Configuring appliances", infrastructure_id=self.infrastructure.id)
        node_configure_tasks = {asyncio.create_task(node.configure()) for node in self.infrastructure.nodes}

        routers = self.infrastructure.routers
        router_configure_tasks = {
            asyncio.create_task(router.configure(routers)) for router in self.infrastructure.routers
        }

        logger.debug("Appliances configured", infrastructure_id=self.infrastructure.id)
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
        stop_container_tasks = (await self.delete_nodes(check_id)).union(await self.delete_routers(check_id))
        await asyncio.gather(*stop_container_tasks)
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

    async def delete_networks(self, check_id: bool) -> set[asyncio.Task]:
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
        network_tasks = set()
        for network in self.infrastructure.networks:
            if not check_id or (check_id and network.docker_id != ""):
                network_tasks.add(asyncio.create_task(network.delete()))
        return network_tasks

    async def delete_routers(self, check_id: bool) -> set[asyncio.Task]:
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
        router_tasks = set()
        for router in self.infrastructure.routers:
            if not check_id or (check_id and router.docker_id != ""):
                router_tasks.add(asyncio.create_task(router.delete()))
        return router_tasks

    async def delete_nodes(self, check_id: bool) -> set[asyncio.Task]:
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
        node_tasks = set()
        for node in self.infrastructure.nodes:
            if not check_id or (check_id and node.docker_id != ""):
                node_tasks.add(asyncio.create_task(node.delete()))
        return node_tasks

    async def delete_infrastructure(self, db_session: AsyncSession):
        """
        Delete infrastructure and all models belonging to it (cascade deletion) from db.
        :param db_session: Async database session

        :return:
        """
        logger.debug(
            "Deleting infrastructure",
            name=self.infrastructure.name,
            id=self.infrastructure.id,
        )

        await db_session.delete(self.infrastructure)
        await db_session.commit()
        logger.debug(
            "Infrastructure deleted",
            name=self.infrastructure.name,
            id=self.infrastructure.id,
        )

    async def change_ipadresses(self, available_networks: list[IPNetwork]):
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

            # first address is used for management network in parent function
            for interface, available_ip in zip(network.interfaces, available_network[1:]):
                interface.ipaddress = available_ip
                if interface.appliance.type == "router" and "management" not in network.name:
                    network.router_gateway = available_ip

    async def change_names(self, container_names: set[str], network_names: set[str]):
        """
        Change names in models for container name uniqueness.
        :param container_names: already used docker container names
        :param network_names: already used network container names
        :return:
        """
        logger.debug(
            "Changing docker names to match the Infrastructure",
            infrastructure_id=self.infrastructure.id,
            infrastructure_name=self.infrastructure.name,
        )
        containers = [*self.infrastructure.nodes, *self.infrastructure.routers]
        for node in self.infrastructure.nodes:
            containers += node.services

        for container in containers:
            if container.name in container_names:
                while (new_name := f"{self.infrastructure.name}-{container.name}") in container_names:
                    continue
                container.name = new_name
                container_names.add(new_name)
            else:
                container_names.add(container.name)
        for network in self.infrastructure.networks:
            if network.name in network_names:
                while (new_name := randomname.generate(self.infrastructure.name, "noun/astronomy")) in network_names:
                    continue
                network.name = new_name
                network_names.add(new_name)
            else:
                container_names.add(network.name)

    async def resolve_dependencies(self):
        """
        Add startup container dependencies to models
        """
        logger.debug(
            "Resolving container dependencies",
            infrastructure_name=self.infrastructure.name,
        )
        containers: list[Service] = []
        for node in self.infrastructure.nodes:
            containers += node.services

        container_dict: dict[str:Service] = {container.name: container for container in containers}
        for container in containers:
            if container.name in constants.TESTBED_INFO.keys():
                if dependencies := constants.TESTBED_INFO[container.name].get(constants.DEPENDS_ON):
                    for key, value in dependencies.items():
                        if dependency := container_dict.get(key):
                            container.dependencies.append(DependsOn(dependency=dependency, state=value))
        logger.debug("Dependencies resolved", infrastructure_name=self.infrastructure.name)

    @staticmethod
    async def prepare_controller_for_infra_creation(
        docker_client: docker.DockerClient,
        infrastructure: Infrastructure,
        images,
        available_networks,
    ):
        """
        Creates a management network for routers and changes names and ip addresses of models for new infrastructure if
        needed.
        :param available_networks: IP addresses of networks that are available to use for building Infra
        :param infrastructure: Infrastructure object
        :param images: images needed for Infrastructure containers
        :param docker_client: client for docker rest api
        :return: Controller with prepared object for building a new infrastructure
        """
        logger.debug(
            "Preparing InfrastructureController",
            infrastructure_name=infrastructure.name,
            infrastructure_id=infrastructure.id,
        )

        controller = InfrastructureController(docker_client, images, infrastructure)

        await controller.resolve_dependencies()

        used_network_names = await util.get_network_names(docker_client)

        while (management_name := randomname.generate("adj/colors", "management")) in used_network_names:
            continue
        used_network_names.add(management_name)
        management_network = Network(
            ipaddress=available_networks[-1],
            router_gateway=available_networks[-1][1],
            name=management_name,
            network_type=constants.NETWORK_TYPE_MANAGEMENT,
        )

        for router, ip_address in zip(controller.infrastructure.routers, management_network.ipaddress[2:]):
            if router.router_type == constants.ROUTER_TYPE_PERIMETER:
                router.interfaces.append(
                    Interface(
                        ipaddress=management_network.router_gateway,
                        network=management_network,
                    )
                )
            else:
                router.interfaces.append(Interface(ipaddress=ip_address, network=management_network))

        controller.infrastructure.networks.append(management_network)

        if set(available_networks) != {network.ipaddress for network in controller.infrastructure.networks}:
            await asyncio.gather(
                controller.change_ipadresses(available_networks),
            )
            logger.debug(
                "IP addresses changed for new infrastructure",
                infrastructure_name=infrastructure.name,
                infrastructure_id=infrastructure.id,
            )

        return controller

    @staticmethod
    async def build_infras(number_of_infrastructures: int, run: Run, db_session: AsyncSession):
        """
        Builds docker infrastructure
        :param run: Run object
        :param number_of_infrastructures: Number of infrastructures to build
        :param db_session: Async database session
        :return:
        """
        logger.info("Building infrastructures")
        docker_client = docker.from_env()
        controller_start_tasks = set()
        available_networks = []

        docker_container_names = await util.get_container_names(docker_client)
        docker_network_names = await util.get_network_names(docker_client)
        await util.pull_images(docker_client, images=set(constants.IMAGE_LIST))

        for i in range(int(number_of_infrastructures)):
            # need to parse infra at every iteration due to python reference holding and because sqlalchemy models cannot be
            # deep copied
            parser = CYSTParser(docker_client)
            await parser.parse(cyst_routers, cyst_nodes, attacker)
            if not available_networks:
                available_networks += await util.get_available_networks(
                    docker_client, parser.networks, number_of_infrastructures
                )
            # TODO: Move checking of used ips/names into the parser?
            # get the correct amount of networks for infra from available network list
            slice_start = 0 if i == 0 else (len(parser.networks) + 1) * i
            slice_end = slice_start + len(parser.networks) + 1

            infra_names = (await db_session.scalars(select(Infrastructure.name))).all()

            while (infra_name := randomname.generate("adj/colors")) in infra_names:
                continue

            infrastructure = Infrastructure(
                routers=parser.routers,
                nodes=parser.nodes,
                networks=parser.networks,
                name=infra_name,
            )

            controller = await InfrastructureController.prepare_controller_for_infra_creation(
                docker_client,
                images=parser.images,
                available_networks=available_networks[slice_start:slice_end],
                infrastructure=infrastructure,
            )

            await controller.change_names(
                container_names=docker_container_names,
                network_names=docker_network_names,
            )
            logger.debug(
                "Docker names changed",
                infrastructure_name=infrastructure.name,
            )

            run_instance = Instance(
                run=run,
                agent_instances="placeholder",
                infrastructure=controller.infrastructure,
            )

            logger.debug(
                "Starting infrastructure",
                infrastructure_name=infrastructure.name,
                infrastructure_id=infrastructure.id,
            )

            try:
                controller_start_tasks.add(asyncio.create_task(controller.start()))
                await asyncio.gather(*controller_start_tasks)
                db_session.add(run_instance)
                await db_session.commit()
            except (ImageNotFound, APIError, RuntimeError, Exception) as error:
                logger.debug(
                    f"Deleting instance due to {type(error).__name__}",
                    infrastructure_id=infrastructure.id,
                    exception=error,
                )
                # TODO: Is there an exception where the containers(docker_ids) are created?
                try:
                    await controller.stop()
                except NullResource:
                    pass
                raise error

    @staticmethod
    async def stop_infra(infrastructure: Infrastructure):
        """
        Destroys docker infrastructure.
        :param infrastructure: Infrastructure object
        :return:
        """
        controller = InfrastructureController(docker.from_env(), set(), infrastructure)

        # destroy docker objects
        await controller.stop()
        # delete objects from db
        # await controller.delete_infrastructure()

    @staticmethod
    async def delete_infra(infrastructure: Infrastructure, db_session: AsyncSession):
        """
        Destroys docker infrastructure.
        :param infrastructure: Infrastructure object
        :param db_session: Async database session
        :return:
        """
        controller = InfrastructureController(docker.from_env(), set(), infrastructure)

        # delete objects from db
        await controller.delete_infrastructure(db_session)

    @staticmethod
    async def list_infrastructures(db_session: AsyncSession) -> Sequence[Infrastructure]:
        """
        Return names and Ids of all infrastructures in key:value -> id:name format
        :param db_session: Async database session
        :return:
        """
        logger.debug("Pulling infrastructures from db")

        return (await db_session.scalars(select(Infrastructure))).all()

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
                        joinedload(Infrastructure.networks)
                        .subqueryload(Network.interfaces)
                        .subqueryload(Interface.appliance),
                    )
                )
            )
            .unique()
            .scalar_one()
        )

        return infrastructure
