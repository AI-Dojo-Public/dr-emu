import asyncio

import docker.errors
from docker import DockerClient

from testbed_app.models import Network, Node, Router
from testbed_app.database import session_factory


class Controller:
    def __init__(
        self,
        client: DockerClient,
        networks: list[Network],
        routers: list[Router],
        nodes: list[Node],
        images: set,
    ):
        self.client = client
        self.networks = networks
        self.routers = routers
        self.nodes = nodes
        self.images = images

    async def pull_images(self):
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
        await self.pull_images()

        create_network_tasks = await self.create_networks()
        await asyncio.gather(*create_network_tasks)

        start_router_tasks = await self.start_routers()
        await asyncio.gather(*start_router_tasks)

        start_node_tasks = await self.start_nodes()
        await asyncio.gather(*start_node_tasks)

        async with session_factory() as session:
            session.add_all(self.networks)
            session.add_all(self.routers)
            session.add_all(self.nodes)
            await session.commit()

    async def create_networks(self) -> set[asyncio.Task]:
        return {asyncio.create_task(network.create()) for network in self.networks}

    async def start_routers(self) -> set[asyncio.Task]:
        return {asyncio.create_task(router.start()) for router in self.routers}

    async def start_nodes(self) -> set[asyncio.Task]:
        return {asyncio.create_task(node.start()) for node in self.nodes}

    async def stop(self, check_id: bool = False):
        stop_container_tasks = (await self.delete_nodes(check_id)).union(
            await self.delete_routers(check_id)
        )
        await asyncio.gather(*stop_container_tasks)

        delete_network_tasks = await self.delete_networks(check_id)
        await asyncio.gather(*delete_network_tasks)

        # TODO: is there a better way to do this?
        async with session_factory() as session:
            for appliance in [*self.nodes, *self.routers]:
                await session.delete(appliance)
            for network in self.networks:
                await session.delete(network)
            await session.commit()

    async def delete_networks(self, check_id: bool) -> set[asyncio.Task]:
        network_tasks = set()
        for network in self.networks:
            if not check_id or (check_id and network.docker_id != ""):
                network_tasks.add(asyncio.create_task(network.delete()))
        return network_tasks

    async def delete_routers(self, check_id: bool) -> set[asyncio.Task]:
        router_tasks = set()
        for router in self.routers:
            if not check_id or (check_id and router.docker_id != ""):
                router_tasks.add(asyncio.create_task(router.delete()))
        return router_tasks

    async def delete_nodes(self, check_id: bool) -> set[asyncio.Task]:
        node_tasks = set()
        for node in self.nodes:
            if not check_id or (check_id and node.docker_id != ""):
                node_tasks.add(asyncio.create_task(node.delete()))
        return node_tasks
