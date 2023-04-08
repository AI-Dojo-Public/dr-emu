from typing import Dict, List

import docker
import docker.types
import randomname
from enum import Enum
import re
from util import constants
from docker.models.containers import Container
from docker.models.networks import Network

client = docker.from_env()


class ContainerConfig(docker.client.ContainerCollection):
    def __init__(self, name, gateway, command, image, ipaddress, network_name):
        super().__init__(client)
        self.network_name = network_name
        self.ipaddress = ipaddress
        self.command = command
        self.image = image
        self.name = name
        self.gateway = gateway
        self.container_id = None

    @property
    def container(self) -> Container:
        """
        A docker container object.
        """
        return self.get(self.container_id)

    def create_container(self):
        container = self.create(image=self.image,
                                name=self.name,
                                network=self.network_name,
                                command="sleep infinity",
                                cap_add="NET_ADMIN")

        self.container_id = container.id


class NetworkConfig(docker.client.NetworkCollection):
    def __init__(self, ip, bridge_ip, gateway=None, name=None):
        super().__init__(client)
        self.gateway = gateway
        self.bridge_ip = bridge_ip
        self.ip = ip
        self.network_id = None
        self.node_containers: List[ContainerConfig] = []

        if name is None:
            self.name = randomname.get_name(adj='colors', noun='astronomy')
        else:
            self.name = name

    @property
    def network(self) -> Network:
        """
        A docker container object.
        """
        return self.get(self.network_id)

    def create_network(self):
        ipam_pool = docker.types.IPAMPool(
            subnet=str(self.ip),
            gateway=str(self.bridge_ip))

        ipam_config = docker.types.IPAMConfig(
            pool_configs=[ipam_pool])

        self.network_id = self.create(self.name, driver="bridge", ipam=ipam_config).id

    def connect_node_containers(self):
        for node in self.node_containers:
            self.network.connect(node.name, ipv4_address=str(node.ipaddress))


class NodeContainerConfig(ContainerConfig):
    def __init__(self, name, ipaddress, network_name, gateway=None, command=None, image=None):
        super().__init__(name, gateway, command, image, ipaddress, network_name)

    def configure_container(self):

        # select setup commands based on linux distro
        distro = re.search(
            "ID=([a-z]{0,10})", self.container.exec_run("cat /etc/os-release").output.decode("utf-8")
        ).group(1)
        setup_commands = DistroSetup[distro].value

        for command in setup_commands:
            self.container.exec_run(command)

        self.container.exec_run("ip route del default")
        self.container.exec_run(f"ip route add default via {str(self.gateway)}")


# TODO: figure out router config (static ip routing)
class RouterContainerConfig(ContainerConfig):
    def __init__(self, name, interfaces, gateway=None, command=None, image=None, config_path=None,
                 management_ipaddress=None, network_name=constants.MANAGEMENT_NETWORK_NAME):
        super().__init__(name, gateway, command, image, management_ipaddress, network_name)
        self.interfaces = interfaces
        self.config_path = config_path

    def configure_router(self, routers):
        for command in ["apt update -y", "apt install iproute2 -y"]:
            self.container.exec_run(command)
        if self.name == constants.PERIMETER_ROUTER:
            self.container.exec_run(f"ip route add 192.168.91.0/24 via {str(routers['internal_router'].ipaddress)}")
            self.container.exec_run(f"ip route add 192.168.92.0/24 via {str(routers['internal_router'].ipaddress)}")
            self.container.exec_run("iptables --table nat --append POSTROUTING --out-interface eth0 --source 192.168.0.0/16 -j MASQUERADE")
        else:
            self.container.exec_run("ip route del default")
            self.container.exec_run(f"ip route add default via {str(self.gateway)}")

    def connect_router_to_networks(self, networks: Dict[str, NetworkConfig]):
        networks[constants.MANAGEMENT_NETWORK_NAME].network.connect(self.container_id, ipv4_address=str(self.ipaddress))
        for network in networks.values():
            for interface in self.interfaces:
                if interface.net == network.ip:
                    network.network.connect(self.name, ipv4_address=str(interface.ip))


class DistroSetup(Enum):
    debian = ["apt update -y", "apt install iproute2 -y"]
    alpine = ["apk update", "apk add --upgrade iproute2"]
    fedora = ["dnf update -y", "dnf install iproute2 -y"]
