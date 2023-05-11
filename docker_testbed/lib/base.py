from docker import DockerClient
from abc import abstractmethod, ABC


class Base:
    def __init__(self, client: DockerClient):
        self.client = client
        self.id = ""

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def delete(self):
        pass


class BaseGeneral(Base, ABC):
    @abstractmethod
    def create(self):
        pass


class BaseService(Base, ABC):
    @abstractmethod
    def create(self, parent_node_id: str):
        pass
