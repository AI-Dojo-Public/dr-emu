from netaddr import IPAddress

from docker import DockerClient

from docker_testbed.lib.network import Network
from docker_testbed.lib.node import BaseNode
from docker_testbed.util import constants


class Router(BaseNode):
    def __init__(self, client: DockerClient, name: str, ip: IPAddress, network: Network,
                 attached_networks: list[Network], image: str = constants.IMAGE_ROUTER,
                 tty: bool = True, detach: bool = True, cap_add: list = None):
        super().__init__(client, name, ip, network, image, tty, detach, cap_add)
        self.attached_networks = attached_networks

    def configure(self):
        container = self.get()

        if self.name == constants.PERIMETER_ROUTER:
            default_gateway = self.network.bridge_gateway
        else:
            default_gateway = self.network.router_gateway

        container.exec_run("ip route del default")
        container.exec_run(f"ip route add default via {default_gateway}")

        container.exec_run("iptables -t nat -A POSTROUTING -j MASQUERADE")
        container.exec_run("iptables-save")

    def connect_to_networks(self):
        for network in self.attached_networks:
            network.get().connect(self.name, ipv4_address=str(network.router_gateway))

    def start(self):
        self.create()
        self.get().start()
        self.connect_to_networks()
        self.configure()
