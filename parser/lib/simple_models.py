from netaddr import IPNetwork, IPAddress
from dataclasses import dataclass

from parser.lib.containers import Container


@dataclass
class Network:
    """
    Serializable alternative for DB model.
    """
    name: str
    type: str
    ip_address: IPNetwork
    gateway: IPAddress


@dataclass
class Interface:
    """
    Serializable alternative for DB model.
    """
    ip_address: IPAddress
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


@dataclass
class Node:
    """
    Serializable alternative for DB model.
    """
    name: str
    interfaces: list[Interface]
    container: Container
    services: list[Service]
