import asyncio

from docker_testbed.lib.network import Network
from docker_testbed.lib.node import Node
from docker_testbed.lib.router import Router


class Controller:
    def __init__(
        self, networks: list[Network], routers: list[Router], nodes: list[Node]
    ):
        self.networks = networks
        self.routers = routers
        self.nodes = nodes

    async def start(self):
        create_network_tasks = await self.create_networks()
        await asyncio.gather(*create_network_tasks)

        start_node_tasks = (await self.start_routers()).union(await self.start_nodes())
        await asyncio.gather(*start_node_tasks)

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

    async def delete_networks(self, check_id: bool) -> set[asyncio.Task]:
        network_tasks = set()
        for network in self.networks:
            if not check_id or (check_id and network.id != ""):
                network_tasks.add(asyncio.create_task(network.delete()))
        return network_tasks

    async def delete_routers(self, check_id: bool) -> set[asyncio.Task]:
        router_tasks = set()
        for router in self.routers:
            if not check_id or (check_id and router.id != ""):
                router_tasks.add(asyncio.create_task(router.delete()))
        return router_tasks

    async def delete_nodes(self, check_id: bool) -> set[asyncio.Task]:
        node_tasks = set()
        for node in self.nodes:
            if not check_id or (check_id and node.id != ""):
                node_tasks.add(asyncio.create_task(node.delete()))
        return node_tasks
