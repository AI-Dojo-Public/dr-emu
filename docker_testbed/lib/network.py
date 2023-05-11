import asyncio
import randomname
from netaddr import IPAddress, IPNetwork

from docker.models.networks import Network as DockerNetwork
from docker import DockerClient
from docker.types import IPAMPool, IPAMConfig

from docker_testbed.lib import base


class Network(base.BaseGeneral):
    def __init__(
        self,
        client: DockerClient,
        subnet: IPNetwork,
        router_gateway: IPAddress,
        bridge_gateway: IPAddress = None,
    ):
        super().__init__(client)
        self.client = client
        self.subnet = subnet
        self.ip = subnet.ip
        self.name = randomname.get_name(adj="colors", noun="astronomy", sep="_")
        self.router_gateway = router_gateway

        self.driver = "bridge"
        self.attachable = True

        if bridge_gateway is None:  # Doesn't work for subnets <= 4
            self.bridge_gateway = IPAddress(self.subnet.last - 1, self.subnet.version)
        else:
            self.bridge_gateway = bridge_gateway

    async def get(self) -> DockerNetwork:
        return await asyncio.to_thread(self.client.networks.get, self.id)

    async def create(self):
        ipam_pool = IPAMPool(subnet=str(self.subnet), gateway=str(self.bridge_gateway))
        ipam_config = IPAMConfig(pool_configs=[ipam_pool])

        self.id = (
            await asyncio.to_thread(
                self.client.networks.create,
                self.name,
                driver=self.driver,
                ipam=ipam_config,
                attachable=self.attachable,
            )
        ).id

    async def delete(self):
        await asyncio.to_thread((await self.get()).remove)
