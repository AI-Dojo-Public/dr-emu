import asyncio
from netaddr import IPAddress
from docker import DockerClient

from docker_testbed.lib.network import Network
from docker_testbed.lib.node import BaseNode
from docker_testbed.util import constants


class Router(BaseNode):
    def __init__(
        self,
        client: DockerClient,
        name: str,
        ip: IPAddress,
        network: Network,
        attached_networks: list[Network],
        image: str = constants.IMAGE_ROUTER,
        tty: bool = True,
        detach: bool = True,
        cap_add: list = None,
    ):
        super().__init__(client, name, ip, network, image, tty, detach, cap_add)
        self.attached_networks = attached_networks
        self.setup_instructions = [
            "ip route del default",
            f"ip route add default via {str(self.network.router_gateway)}",
        ]

    async def configure(self):
        container = await self.get()

        if self.name == constants.PERIMETER_ROUTER:
            default_gateway = self.network.bridge_gateway
        else:
            default_gateway = self.network.router_gateway

        config_instructions = [
            "ip route del default",
            f"ip route add default via {default_gateway}",
            "iptables -t nat -A POSTROUTING -j MASQUERADE",
            "iptables-save",
        ]

        for instruction in config_instructions:
            await asyncio.to_thread(container.exec_run, instruction)

    async def connect_to_networks(self):
        for network in self.attached_networks:
            (await network.get()).connect(
                self.name, ipv4_address=str(network.router_gateway)
            )

    async def start(self):
        await self.create()
        (await self.get()).start()
        await self.connect_to_networks()
        await self.configure()
