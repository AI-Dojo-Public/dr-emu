from docker import DockerClient
from docker.models.containers import Container

from docker_testbed.lib import base


class Service(base.Base):
    def __init__(self, client: DockerClient, name: str, parent_node: str, image: str, detach: bool = True, **kwargs):
        super().__init__(client)
        self.image = image
        self.name = name
        self.parent_node = parent_node
        self.kwargs = kwargs
        self.detach = detach

    def get(self) -> Container:
        return self.client.containers.get(self.id)

    def create(self):
        container = self.client.containers.create(self.image, name=self.name, detach=self.detach,
                                                  network_mode=f"container:{self.parent_node}", **self.kwargs)
        self.id = container.id

        container.start()

    def delete(self):
        container = self.get()
        container.stop(timeout=0)
        container.remove()
