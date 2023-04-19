import randomname
from netaddr import IPAddress, IPNetwork

from docker.models.networks import Network as DockerNetwork
from docker import DockerClient
from docker.types import IPAMPool, IPAMConfig

from docker_testbed.lib import base


class Network(base.Base):
    def __init__(self, client: DockerClient, subnet: IPNetwork, router_gateway: IPAddress,
                 bridge_gateway: IPAddress = None):
        super().__init__(client)
        self.client = client
        self.subnet = subnet
        self.ip = subnet.ip
        self.name = randomname.get_name(adj='colors', noun='astronomy', sep="_")
        self.router_gateway = router_gateway

        if bridge_gateway is None:  # Doesn't work for subnets <= 4
            self.bridge_gateway = IPAddress(self.subnet.last - 1, self.subnet.version)
        else:
            self.bridge_gateway = bridge_gateway

    def get(self) -> DockerNetwork:
        return self.client.networks.get(self.id)

    def create(self, attachable: bool = True):
        ipam_pool = IPAMPool(subnet=str(self.subnet), gateway=str(self.bridge_gateway))
        ipam_config = IPAMConfig(pool_configs=[ipam_pool])

        self.id = self.client.networks.create(self.name, driver="bridge", ipam=ipam_config, attachable=attachable).id

    def delete(self):
        self.get().remove()
