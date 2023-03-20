import docker

client = docker.from_env()


class Container:
    def __init__(self, name, gateway):
        self.name = name
        self.gateway = name


class NodeContainer(Container):
    def __init__(self, ip, network, name, gateway):
        super().__init__(name, gateway)
        self.ip = ip
        self.network = network


class RouterContainer(Container):
    def __init__(self, interfaces, networks, name, gateway):
        super().__init__(name, gateway)
        self.interfaces = interfaces
        self.networks = networks
