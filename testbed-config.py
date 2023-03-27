import docker
import yaml

client = docker.from_env()


class Network:
    def __init__(self, subnet, name, bridge_ip, gateway):
        self.gateway = gateway
        self.bridge_ip = bridge_ip
        self.name = name
        self.subnet = subnet

    def create_network(self):
        ipam_pool = client.types.IPAMPool(
            subnet=self.subnet,
            gateway=self.bridge_ip)

        ipam_config = client.types.IPAMConfig(
            pool_configs=[ipam_pool])

        client.networks.create(self.name, driver="bridge", ipam=ipam_config)


class Container:
    def __init__(self, image, name, gateway, command):
        self.command = command
        self.image = image
        self.name = name
        self.gateway = gateway


class NodeContainer(Container):
    def __init__(self, ip, network, name, gateway, image, command):
        super().__init__(name, gateway, image, command)
        self.ip = ip
        self.network = network

    def create_container(self):
        client.containers.create(self.image, self)


class RouterContainer(Container):
    def __init__(self, interfaces, networks, config_path, name, gateway,  image, command):
        super().__init__(name, gateway, image, command)
        self.interfaces = interfaces
        self.networks = networks
        self.config_path = config_path

    def create_router(self):
        router_id = client.containers.run(self.image)
        return router_id


with open('docker-compose.yml', 'r') as file:
    demo_compose = yaml.safe_load(file)

print(demo_compose)
