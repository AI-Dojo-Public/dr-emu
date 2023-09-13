import asyncio
from typing import Optional

import docker.errors
import randomname
from docker import DockerClient
from netaddr import IPNetwork
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from docker_testbed.util import constants, util
from testbed_app.models import (
    Network,
    Node,
    Router,
    Infrastructure,
    Interface,
    Attacker,
)
from testbed_app.database import session_factory
from testbed_app.controllers import router as router_controller


# TODO: merge Infrastructure and Controller class into one? (Infrastructure Controller)
class InstanceController:
    """
    Class for handling actions regarding creating and destroying the infrastructure in docker.
    """

    def __init__(
        self,
        client: DockerClient,
        images: set,
        infrastructure: Optional[Infrastructure] = None,
    ):
        self.client = client
        self.images = images
        self.infrastructure = infrastructure

    async def start(self):
        """
        Executes all necessary functions for building an infrastructure and saves created models to the database.
        :return:
        """
        print(f"Starting infrastructure with name: {self.infrastructure.name}")

        try:
            create_network_tasks = await self.create_networks()
            await asyncio.gather(*create_network_tasks)

            start_router_tasks = await self.start_routers()
            start_node_tasks = await self.start_nodes()

            await asyncio.gather(*start_node_tasks, *start_router_tasks)

            configure_appliance_tasks = await self.configure_appliances()
            await asyncio.gather(*configure_appliance_tasks)
        except Exception as ex:
            await self.stop(check_id=True)
            raise ex

        print(f"Created infrastructure with id: {self.infrastructure.id}, name: {self.infrastructure.name}")

    async def create_networks(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating networks.
        :return: set of tasks for network creation
        """
        return {asyncio.create_task(network.create()) for network in self.infrastructure.networks}

    async def start_routers(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating and starting routers.
        :return: set of tasks to start router containers
        """
        return {asyncio.create_task(router.start()) for router in self.infrastructure.routers}

    async def start_nodes(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating and starting nodes.
        :return: set of tasks to start node containers
        """
        return {asyncio.create_task(node.start()) for node in self.infrastructure.nodes}

    async def configure_appliances(self):
        """
        Create async tasks for configuring iptables and ip routes in Nodes and Routers.
        :return:
        """
        node_configure_tasks = {asyncio.create_task(node.configure()) for node in self.infrastructure.nodes}

        routers = await router_controller.get_infra_routers(self.infrastructure.id)
        router_configure_tasks = {
            asyncio.create_task(router.configure(routers)) for router in self.infrastructure.routers
        }
        return node_configure_tasks.union(router_configure_tasks)

    async def stop(self, check_id: bool = False):
        """
        Stops and deletes all containers and networks in the infrastructure.
        :param check_id:
        :return:
        """
        print("stopping infrastructure")
        stop_container_tasks = (await self.delete_nodes(check_id)).union(await self.delete_routers(check_id))
        await asyncio.gather(*stop_container_tasks)

        delete_network_tasks = await self.delete_networks(check_id)
        await asyncio.gather(*delete_network_tasks)

    async def delete_networks(self, check_id: bool) -> set[asyncio.Task]:
        """
        Creates async tasks for deletion of networks.
        :param check_id:
        :return: set of tasks for networks deletion
        """
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
        node_tasks = set()
        for node in self.infrastructure.nodes:
            if not check_id or (check_id and node.docker_id != ""):
                node_tasks.add(asyncio.create_task(node.delete()))
        return node_tasks

    async def delete_infrastructure(self):
        """
        Delete infrastructure and all models belonging to it (cascade deletion) from db.
        :return:
        """
        async with session_factory() as session:
            await session.delete(self.infrastructure)
            await session.commit()

    async def change_ipadresses(self, available_networks: list[IPNetwork]):
        """
        Change ip addresses in models.
        :param available_networks: available ip addresses for networks
        :return:
        """
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

    @staticmethod
    async def get_controller_with_infra_objects(infrastructure_id: int = None):
        """
        Create a controller object with models that match the provided infrastructure ids.
        (used later for stopping and|or deleting docker objects referring to these models)
        :param infrastructure_id: ID of infrastructure
        :return: Controller object with models belonging to the provided infrastructures.
        """
        async with session_factory() as session:
            nodes = (
                (
                    await session.scalars(
                        select(Node)
                        .where(Node.infrastructure_id == infrastructure_id)
                        .options(joinedload(Node.services))
                    )
                )
                .unique()
                .all()
                if infrastructure_id
                else (await session.scalars(select(Node).options(joinedload(Node.services)))).unique().all()
            )

            routers = (
                (await session.scalars(select(Router).where(Router.infrastructure_id == infrastructure_id))).all()
                if infrastructure_id
                else (await session.scalars(select(Router))).all()
            )
            networks = (
                (await session.scalars(select(Network).where(Network.infrastructure_id == infrastructure_id))).all()
                if infrastructure_id
                else (await session.scalars(select(Network))).all()
            )

            # Exception handled in outer function
            infrastructure = (
                await session.execute(select(Infrastructure).where(Infrastructure.id == infrastructure_id))
            ).scalar_one()

        return InstanceController(docker.from_env(), set(), infrastructure)

    @staticmethod
    async def prepare_controller_for_infra_creation(
        docker_client: DockerClient,
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

        controller = InstanceController(docker_client, images, infrastructure)

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
        infrastructure.networks.append(management_network)

        if [str(network) for network in available_networks] != [
            str(network.ipaddress) for network in controller.infrastructure.networks
        ]:
            await asyncio.gather(
                controller.change_ipadresses(available_networks),
            )

        return controller
