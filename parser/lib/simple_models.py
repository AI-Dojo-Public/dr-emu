from enum import Enum
from typing import Any

from netaddr import IPNetwork, IPAddress
from dataclasses import dataclass, field

from dr_emu.models import (
    Node as DockerNode,
    Attacker as DockerAttacker,
    Dns as DockerDns,
)
from parser.lib.containers import Container


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
class Router:
    """
    Serializable alternative for DB model.
    """

    name: str
    type: str
    interfaces: list[Interface]
    container: Container
    firewall_rules: list[FirewallRule]


@dataclass
class Service:
    """
    Serializable alternative for DB model.
    """

    name: str
    container: Container
    depends_on: list["Service"] = field(default_factory=list)


class NodeType(Enum):
    """
    Defining type of node.
    """
    DEFAULT = DockerNode
    DNS = DockerDns
    ATTACKER = DockerAttacker


@dataclass
class Node:
    """
    Serializable alternative for DB model.
    """

    name: str
    interfaces: list[Interface]
    container: Container
    services: list[Service]
    type: NodeType
