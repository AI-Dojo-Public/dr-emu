from docker import DockerClient
from docker.models.containers import Container

from docker_testbed.lib import base


class Service(base.BaseService):
    def __init__(self, client: DockerClient, name: str, image: str, detach: bool = True, **kwargs):
        super().__init__(client)
        self.image = image
        self.name = name
        self.kwargs = kwargs
        self.detach = detach

    def get(self) -> Container:
        return self.client.containers.get(self.id)

    def create(self, parent_node_id: str):
        container = self.client.containers.create(self.image, name=self.name, detach=self.detach,
                                                  network_mode=f"container:{parent_node_id}",
                                                  pid_mode=f"container:{parent_node_id}",
                                                  ipc_mode=f"container:{parent_node_id}",
                                                  **self.kwargs)
        self.id = container.id

        container.start()

    def delete(self):
        container = self.get()
        container.stop(timeout=0)
        container.remove()
