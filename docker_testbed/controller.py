import asyncio
from typing import Optional

import docker.errors
import randomname
from docker import DockerClient
from netaddr import IPNetwork
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from docker_testbed.cyst_parser import CYSTParser
from docker_testbed.util import constants, util
from testbed_app.models import Network, Node, Router, Infrastructure, Interface
from testbed_app.database import session_factory


class Controller:
    """
    Class for handling actions regarding creating and destroying the infrastructure in docker.
    """
    def __init__(
        self,
        client: DockerClient,
        networks: list[Network],
        routers: list[Router],
        nodes: list[Node],
        images: set,
        infrastructures: Optional[list[Infrastructure]] = None,
    ):
        self.client = client
        self.networks = networks
        self.routers = routers
        self.nodes = nodes
        self.images = images
        self.infrastructures = infrastructures

    async def pull_images(self):
        """
        Pull docker images that will be used in the infrastructure.
        :return:
        """
        pull_image_tasks = set()

        for image in self.images:
            try:
                await asyncio.to_thread(self.client.images.get, image)
            except docker.errors.ImageNotFound:
                print(f"pulling image: {image}")
                pull_image_tasks.add(
                    asyncio.create_task(
                        asyncio.to_thread(self.client.images.pull, image)
                    )
                )

        if pull_image_tasks:
            await asyncio.gather(*pull_image_tasks)

    async def start(self):
        """
        Executes all necessary functions for building an infrastructure and saves created models to the database.
        :return:
        """
        print("starting infrastructure")
        await self.pull_images()
        infrastructure = Infrastructure(
            appliances=[*self.routers, *self.nodes], networks=self.networks
        )

        create_network_tasks = await self.create_networks()
        await asyncio.gather(*create_network_tasks)

        start_router_tasks = await self.start_routers()
        start_node_tasks = await self.start_nodes()

        await asyncio.gather(*start_node_tasks, *start_router_tasks)

        configure_appliance_tasks = await self.configure_appliances()
        await asyncio.gather(*configure_appliance_tasks)

        async with session_factory() as session:
            session.add_all(
                [*self.networks, *self.routers, *self.nodes, infrastructure]
            )
            await session.commit()

    async def create_networks(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating networks.
        :return: set of tasks for network creation
        """
        return {asyncio.create_task(network.create()) for network in self.networks}

    async def start_routers(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating and starting routers.
        :return: set of tasks to start router containers
        """
        return {asyncio.create_task(router.start()) for router in self.routers}

    async def start_nodes(self) -> set[asyncio.Task]:
        """
        Creates async tasks for creating and starting nodes.
        :return: set of tasks to start node containers
        """
        return {asyncio.create_task(node.start()) for node in self.nodes}

    async def configure_appliances(self):
        """
        Create async tasks for configuring iptables and ip routes in Nodes and Routers.
        :return:
        """
        node_configure_tasks = {
            asyncio.create_task(node.configure()) for node in self.nodes
        }
        router_configure_tasks = {
            asyncio.create_task(router.configure()) for router in self.routers
        }
        return node_configure_tasks.union(router_configure_tasks)

    async def stop(self, check_id: bool = False):
        """
        Stops and deletes all containers and networks in the infrastructure.
        :param check_id:
        :return:
        """
        print("stopping infrastructure")
        stop_container_tasks = (await self.delete_nodes(check_id)).union(
            await self.delete_routers(check_id)
        )
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
        for network in self.networks:
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
        for router in self.routers:
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
        for node in self.nodes:
            if not check_id or (check_id and node.docker_id != ""):
                node_tasks.add(asyncio.create_task(node.delete()))
        return node_tasks

    async def delete_infrastructures(self):
        """
        Delete infrastructure and all models belonging to it (cascade deletion) from db.
        :return:
        """
        async with session_factory() as session:
            infra_delete_tasks = set()

            for infrastructure in self.infrastructures:
                infra_delete_tasks.add(
                    asyncio.create_task(session.delete(infrastructure))
                )

            await asyncio.gather(*infra_delete_tasks)
            await session.commit()

    async def change_ipadresses(self, available_networks: list[IPNetwork]):
        """
        Change ip addresses in models.
        :param available_networks: available ip addresses for networks
        :return:
        """
        for network, available_network in zip(self.networks, available_networks):
            network.ipaddress = available_network

            # TODO: make difference for routers and nodes? (routers would have first available ip)
            for interface, available_ip in zip(
                network.interfaces, available_network[1:]
            ):
                interface.ipaddress = available_ip
                if (
                    interface.appliance.type == "router"
                    and "management" not in network.name
                ):
                    network.router_gateway = available_ip

    async def change_names(self, container_names: set[str], network_names: set[str]):
        """
        Change names in models for container name uniqueness.
        :param container_names: already used docker container names
        :param network_names: already used network container names
        :return:
        """
        containers = [*self.nodes, *self.routers]
        for node in self.nodes:
            containers += node.services

        for container in containers:
            if container.name in container_names:
                # TODO: containers limited by the number of colors :)
                while (
                    new_name := randomname.generate("adj/colors", container.name)
                ) in container_names:
                    continue
                container.name = new_name

        for network in self.networks:
            if network.name in network_names:
                # TODO: networks limited by the number of colors :)
                while (
                    new_name := randomname.generate("adj/colors", network.name)
                ) in network_names:
                    continue
                network.name = new_name

    @staticmethod
    async def get_controller_with_infra_objects(infrastructure_ids: int = None):
        """
        Create a controller object with models that match the provided infrastructure ids.
        (used later for stopping and|or deleting docker objects referring to these models)
        :param infrastructure_ids: IDs of infrastructures
        :return: Controller object with models belonging to the provided infrastructures.
        """
        async with session_factory() as session:
            nodes = (
                (
                    await session.scalars(
                        select(Node)
                        .where(Node.infrastructure_id == infrastructure_ids)
                        .options(joinedload(Node.services))
                    )
                )
                .unique()
                .all()
                if infrastructure_ids
                else (
                    await session.scalars(
                        select(Node).options(joinedload(Node.services))
                    )
                )
                .unique()
                .all()
            )

            routers = (
                (
                    await session.scalars(
                        select(Router).where(
                            Router.infrastructure_id == infrastructure_ids
                        )
                    )
                ).all()
                if infrastructure_ids
                else (await session.scalars(select(Router))).all()
            )
            networks = (
                (
                    await session.scalars(
                        select(Network).where(
                            Network.infrastructure_id == infrastructure_ids
                        )
                    )
                ).all()
                if infrastructure_ids
                else (await session.scalars(select(Network))).all()
            )

            infrastructures = (
                (
                    await session.scalars(
                        select(Infrastructure).where(
                            Infrastructure.id == infrastructure_ids
                        )
                    )
                ).all()
                if infrastructure_ids
                else (await session.scalars(select(Infrastructure))).all()
            )

        return Controller(
            docker.from_env(), networks, routers, nodes, set(), infrastructures
        )

    @staticmethod
    async def prepare_controller_for_infra_creation(docker_client: DockerClient, parser: CYSTParser):
        """
        Creates a management network for routers and changes names and ip addresses of models for new infrastructure if
        needed.
        :param docker_client: client for docker rest api
        :param parser: CYSTParser object
        :return: Controller with prepared object for building a new infrastructure
        """
        controller = Controller(
            docker_client,
            parser.networks,
            parser.routers,
            parser.nodes,
            parser.images,
        )
        available_networks = await util.get_available_networks(
            docker_client, parser.networks
        )
        management_network = Network(
            ipaddress=available_networks[-1],
            router_gateway=available_networks[-1][1],
            name=randomname.generate("adj/colors", "management"),
            network_type=constants.NETWORK_TYPE_MANAGEMENT,
        )
        for router, ip_address in zip(
            controller.routers, management_network.ipaddress[2:]
        ):
            if router.router_type == constants.ROUTER_TYPE_PERIMETER:
                router.interfaces.append(
                    Interface(
                        ipaddress=management_network.router_gateway,
                        network=management_network,
                    )
                )
            else:
                router.interfaces.append(
                    Interface(ipaddress=ip_address, network=management_network)
                )

        controller.networks.append(management_network)

        # 1 available network means that only management network with default cyst infra should be created
        if len(available_networks) > 1:
            container_names, network_names = await util.get_docker_names(docker_client)
            await asyncio.gather(
                controller.change_ipadresses(available_networks),
                controller.change_names(container_names, network_names),
            )

        return controller
