from docker import DockerClient

from abc import abstractmethod


class Base:
    def __init__(self, client: DockerClient):
        self.client = client
        self.id = ""

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def delete(self):
        pass
