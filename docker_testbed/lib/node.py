from netaddr import IPAddress
from abc import abstractmethod

from docker import DockerClient
from docker.models.containers import Container

from docker_testbed.lib import base
from docker_testbed.lib.network import Network
from docker_testbed.lib.service import Service
from docker_testbed.util import constants


class BaseNode(base.Base):
    def __init__(self, client: DockerClient, name: str, ip: IPAddress, network: Network,
                 image: str, tty: bool, detach: bool, cap_add: list):
        super().__init__(client)
        self.image = image
        self.name = name
        self.ip = ip
        self.network = network
        self.tty = tty
        self.detach = detach
        self.cap_add = ["NET_ADMIN"] if cap_add is None else cap_add

    def get(self) -> Container:
        return self.client.containers.get(self.id)

    def create(self):
        network_config = self.client.api.create_networking_config({
            self.network.name: self.client.api.create_endpoint_config(ipv4_address=str(self.ip))
        })
        host_config = self.client.api.create_host_config(cap_add=self.cap_add)

        self.id = self.client.api.create_container(
            self.image, name=self.name, tty=self.tty, detach=self.detach, networking_config=network_config,
            host_config=host_config
        )

    @abstractmethod
    def configure(self):
        pass

    def start(self):
        self.create()
        self.get().start()
        self.configure()

    def delete(self):
        container = self.get()
        container.stop(timeout=0)
        container.remove()


class Node(BaseNode):
    def __init__(self, client: DockerClient, name: str, ip: IPAddress, network: Network, services: list[Service],
                 image: str = constants.IMAGE_NODE, tty: bool = True, detach: bool = True, cap_add: list = None):
        super().__init__(client, name, ip, network, image, tty, detach, cap_add)
        self.services = services

        self.setup_instructions = [
            "ip route del default",
            f"ip route add default via {str(self.network.router_gateway)}"
        ]

    def configure(self):
        container = self.get()

        for instruction in self.setup_instructions:
            container.exec_run(instruction)

    def start(self):
        self.create()
        self.get().start()
        self.configure()

        self.create_services()

    def create_services(self):
        for service in self.services:
            service.create()

    def delete(self):
        self.delete_services()

        container = self.get()
        container.stop(timeout=0)
        container.remove()

    def delete_services(self):
        for service in self.services:
            service.delete()
