import asyncio
from netaddr import IPAddress
from abc import abstractmethod

import docker.types
from docker import DockerClient
from docker.models.containers import Container

from docker_testbed.lib import base
from docker_testbed.lib.network import Network
from docker_testbed.lib.service import Service
from docker_testbed.util import constants


class BaseNode(base.BaseGeneral):
    def __init__(
        self,
        client: DockerClient,
        name: str,
        ip: IPAddress,
        network: Network,
        image: str,
        tty: bool,
        detach: bool,
        cap_add: list,
    ):
        super().__init__(client)
        self.image = image
        self.name = name
        self.ip = ip
        self.network = network
        self.tty = tty
        self.detach = detach
        self.cap_add = ["NET_ADMIN"] if cap_add is None else cap_add

    async def get(self) -> Container:
        return await asyncio.to_thread(self.client.containers.get, self.id)

    async def _create_network_config(self) -> docker.types.NetworkingConfig:
        return await asyncio.to_thread(
            self.client.api.create_networking_config,
            {
                self.network.name: self.client.api.create_endpoint_config(
                    ipv4_address=str(self.ip)
                )
            },
        )

    async def _create_host_config(self) -> docker.types.HostConfig:
        return await asyncio.to_thread(
            self.client.api.create_host_config, cap_add=self.cap_add
        )

    async def create(self):
        network_config = await self._create_network_config()
        host_config = await self._create_host_config()

        self.id = (
            await asyncio.to_thread(
                self.client.api.create_container,
                self.image,
                name=self.name,
                tty=self.tty,
                detach=self.detach,
                networking_config=network_config,
                host_config=host_config,
            )
        )["Id"]

    @abstractmethod
    async def configure(self):
        pass

    async def start(self):
        await self.create()
        await asyncio.to_thread((await self.get()).start)
        await self.configure()

    async def delete(self):
        container = await self.get()
        await asyncio.to_thread(container.remove, v=True, force=True)


class Node(BaseNode):
    def __init__(
        self,
        client: DockerClient,
        name: str,
        ip: IPAddress,
        network: Network,
        services: list[Service],
        image: str = constants.IMAGE_NODE,
        tty: bool = True,
        detach: bool = True,
        cap_add: list = None,
    ):
        super().__init__(client, name, ip, network, image, tty, detach, cap_add)
        self.services = services
        self.ipc_mode = "shareable"

        self.setup_instructions = [
            "ip route del default",
            f"ip route add default via {str(self.network.router_gateway)}",
        ]

    async def _create_host_config(self) -> docker.types.HostConfig:
        return await asyncio.to_thread(
            self.client.api.create_host_config,
            cap_add=self.cap_add,
            ipc_mode=self.ipc_mode,
        )

    async def configure(self):
        container = await self.get()

        for instruction in self.setup_instructions:
            await asyncio.to_thread(container.exec_run, cmd=instruction)

    async def start(self):
        await self.create()
        await asyncio.to_thread((await self.get()).start)

        create_service_tasks = await self.create_services()
        await asyncio.gather(*create_service_tasks)

        await self.configure()

    async def create_services(self) -> set[asyncio.Task]:
        return {
            asyncio.create_task(service.create(self.id)) for service in self.services
        }

    async def delete(self):
        delete_services_tasks = await self.delete_services()
        await asyncio.gather(*delete_services_tasks)

        container = await self.get()
        await asyncio.to_thread(container.remove, v=True, force=True)

    async def delete_services(self) -> set[asyncio.Task]:
        return {asyncio.create_task(service.delete()) for service in self.services}
