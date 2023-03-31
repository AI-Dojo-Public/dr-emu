import docker
import randomname
from typing import List, Dict

client = docker.from_env()


class Network:
    def __init__(self, ip, bridge_ip, gateway, name=None):
        self.gateway = gateway
        self.bridge_ip = bridge_ip
        self.ip = ip

        if name is None:
            self.name = randomname.get_name(adj='colors', noun='astronomy')
        else:
            self.name = name

    def create_network(self):
        ipam_pool = client.types.IPAMPool(
            subnet=self.ip,
            gateway=self.bridge_ip)

        ipam_config = client.types.IPAMConfig(
            pool_configs=[ipam_pool])

        client.networks.create(self.name, driver="bridge", ipam=ipam_config)


class Container:
    def __init__(self, name, gateway=None, command=None, image=None):
        self.command = command
        self.image = image
        self.name = name
        self.gateway = gateway


class NodeContainer(Container):
    def __init__(self, ip, network, name, gateway=None, command=None, image=None):
        super().__init__(name, gateway, image, command)
        self.ip = ip
        self.network = network
        self.gateway = gateway

    def create_container(self):
        container_id = client.containers.create(self.image)
        return container_id


class RouterContainer(Container):
    def __init__(self, interfaces, name, gateway=None, command=None, image=None, config_path=None):
        super().__init__(name, gateway, image, command)
        self.interfaces = interfaces
        self.config_path = config_path

    def create_router(self):
        router_id = client.containers.create(self.image)
        return router_id
