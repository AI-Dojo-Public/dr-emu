from enum import Enum
from typing import Any

from frozendict import frozendict
from packaging.version import Version


from netaddr import IPNetwork, IPAddress
from dataclasses import dataclass, field, asdict

from dr_emu.models import (
    Node as DockerNode,
    Attacker as DockerAttacker,
    Dns as DockerDns,
)


# @dataclass
# class Service:
#     """
#     Tag used to match a single service and possibly a version.
#     """
#
#     type: str
#     version: str = ""
#     cves: list[str] = field(default_factory=list)
#     variable_override: dict[str, str | int] = field(default_factory=dict)
#     depends_on: set["ServiceTag"] = field(default_factory=set)


@dataclass(frozen=True)
class Service:
    type: str
    variable_override: dict[str, str | int] = field(default_factory=frozendict)
    version: str = ""
    cves: str = ""

@dataclass(frozen=True)
class Image:
    name: str
    pull: bool = False
    firehole_config: str = ""
    services: tuple[Service, ...] = field(default_factory=tuple)

    def __key(self):
        instance_key = [self.firehole_config, self.pull]
        for service in self.services:
            instance_key += [service.type, service.version, service.cves]
            for key, value in service.variable_override.items():
                instance_key.append(f"{key}:{value}")
        return tuple(instance_key)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Image):
            return self.__key() == other.__key()
        return NotImplemented


@dataclass
class Volume:
    """
    Serializable alternative for DB model.c
    """

    name: str  # Name of volume / Path on host
    bind: str  # Path on container
    local: bool = False


# @dataclass
# class Image:
#     """
#     Serializable alternative for DB model.
#     """
#
#     tag: str
#     services: list[Service]
#     firehole_config: str = ""


@dataclass
class Healthcheck:
    """
    Container healthcheck.
    """

    test: list[str]
    interval: int
    timeout: int
    retries: int


@dataclass
class Container:
    """
    Container with ServiceTags and necessary information to run a Docker container.
    """
    image: Image
    name: str
    description: str = ""
    entrypoint: list[str] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    _healthcheck: Healthcheck | None = None
    volumes: list[Volume] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    kwargs: dict[str, Any] = field(default_factory=dict)
    requires: list["Container"] = field(default_factory=list)
    can_be_combined: bool = False
    is_attacker: bool = False

    @property
    def healthcheck(self) -> dict[str, str]:
        return asdict(self._healthcheck) if self._healthcheck else dict()


@dataclass
class Network:
    """
    Serializable alternative for DB model.
    """

    name: str
    type: str
    subnet: IPNetwork
    gateway: IPAddress


@dataclass
class Interface:
    """
    Serializable alternative for DB model.
    """

    ip: IPAddress
    network: Network


@dataclass
class FirewallRule:
    """
    Serializable alternative for DB model.
    """

    source: Network
    destination: Network
    service: str
    policy: str


@dataclass
class Router(Container):
    """
    Serializable alternative for DB model.
    """

    type: str = ""
    interfaces: list[Interface] = field(default_factory=list)
    firewall_rules: list[FirewallRule] = field(default_factory=list)


class NodeType(Enum):
    """
    Defining type of node.
    """
    DEFAULT = DockerNode
    DNS = DockerDns
    ATTACKER = DockerAttacker


@dataclass
class ServiceContainer(Container):
    """
    Serializable alternative for DB model.
    """
    name: str = field(init=False)
    tag: Service | None = None


@dataclass
class Node(Container):
    """
    Serializable alternative for DB model.
    """

    interfaces: list[Interface] = field(default_factory=list)
    service_containers: list[ServiceContainer] = field(default_factory=list)  # service containers
    type: NodeType = NodeType.DEFAULT



