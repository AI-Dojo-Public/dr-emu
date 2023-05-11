import asyncio

from docker import DockerClient
from docker.models.containers import Container

from docker_testbed.lib import base


class Service(base.BaseService):
    def __init__(
        self, client: DockerClient, name: str, image: str, detach: bool = True, **kwargs
    ):
        super().__init__(client)
        self.image = image
        self.name = name
        self.kwargs = kwargs
        self.detach = detach

    async def get(self) -> Container:
        return await asyncio.to_thread(self.client.containers.get, self.id)

    async def create(self, parent_node_id: str):
        container = await asyncio.to_thread(
            self.client.containers.create,
            self.image,
            name=self.name,
            detach=self.detach,
            network_mode=f"container:{parent_node_id}",
            pid_mode=f"container:{parent_node_id}",
            ipc_mode=f"container:{parent_node_id}",
            **self.kwargs,
        )
        self.id = container.id

        await asyncio.to_thread(container.start)

    async def delete(self):
        container = await self.get()
        await asyncio.to_thread(container.remove, v=True, force=True)
