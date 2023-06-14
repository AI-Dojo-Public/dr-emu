from __future__ import annotations
import asyncio
from typing import Optional
from abc import abstractmethod
from netaddr import IPAddress, IPNetwork

import docker.types
from docker import DockerClient
from docker.models.containers import Container
from docker.models.networks import Network as DockerNetwork
from docker.types import IPAMPool, IPAMConfig

from sqlalchemy import ForeignKey, String, JSON
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    mapped_column,
    Mapped,
)
from sqlalchemy_utils import force_instant_defaults

from testbed_app.resources import docker_client
from docker_testbed.util import constants

# TODO: add init to models that require defaults instead of this?
force_instant_defaults()


class Base(AsyncAttrs, DeclarativeBase):
    pass


class DockerMixin:
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    docker_id: Mapped[str] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column()
    client: DockerClient = docker_client
    kwargs: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    @abstractmethod
    async def create(self):
        pass

    @abstractmethod
    async def get(self):
        pass

    @abstractmethod
    async def delete(self):
        pass


class DockerContainerMixin(DockerMixin):
    __abstract__ = True

    image: Mapped[str] = mapped_column(default=constants.IMAGE_BASE)
    detach: Mapped[bool] = mapped_column(default=True)

    @abstractmethod
    async def create(self):
        pass

    @abstractmethod
    async def get(self):
        pass

    @abstractmethod
    async def delete(self):
        pass


class Network(DockerMixin, Base):
    __tablename__ = "network"

    name: Mapped[str] = mapped_column()
    driver: Mapped[str] = mapped_column(default="bridge")
    attachable: Mapped[bool] = mapped_column(default=True)
    interfaces: Mapped[list["Interface"]] = relationship(
        back_populates="network", cascade="all, delete-orphan"
    )
    _ipaddress = mapped_column("ipaddress", String)
    _router_gateway = mapped_column("router_gateway", String)

    @property
    def ipaddress(self):
        return IPNetwork(self._ipaddress)

    @ipaddress.setter
    def ipaddress(self, ipaddress: IPNetwork):
        self._ipaddress = str(ipaddress)

    @property
    def router_gateway(self):
        return IPAddress(self._router_gateway)

    @router_gateway.setter
    def router_gateway(self, ipaddress: IPAddress):
        self._router_gateway = str(ipaddress)

    @property
    def bridge_gateway(self):
        return str(IPAddress(self.ipaddress.last - 1, self.ipaddress.version))

    async def get(self) -> DockerNetwork:
        return await asyncio.to_thread(self.client.networks.get, self.docker_id)

    async def create(self):
        ipam_pool = IPAMPool(subnet=self._ipaddress, gateway=self.bridge_gateway)
        ipam_config = IPAMConfig(pool_configs=[ipam_pool])

        self.docker_id = (
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


class Interface(Base):
    __tablename__ = "interface"

    network_id: Mapped[int] = mapped_column(ForeignKey("network.id"), primary_key=True)
    network: Mapped["Network"] = relationship(back_populates="interfaces")
    _ipaddress = mapped_column("ipaddress", String)
    appliance: Mapped["Appliance"] = relationship(back_populates="interfaces")
    appliance_id: Mapped[int] = mapped_column(
        ForeignKey("appliance.id"), primary_key=True
    )

    @property
    def ipaddress(self):
        return IPAddress(self._ipaddress)

    @ipaddress.setter
    def ipaddress(self, ipaddress: IPAddress):
        self._ipaddress = str(ipaddress)


class Appliance(DockerContainerMixin, Base):
    __tablename__ = "appliance"

    _cap_add = mapped_column("cap_add", String, default="NET_ADMIN")
    tty: Mapped[bool] = mapped_column(default=True)
    interfaces: Mapped[list["Interface"]] = relationship(
        back_populates="appliance", cascade="all, delete-orphan"
    )
    type: Mapped[str]

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "appliance",
    }

    @property
    def cap_add(self) -> list[str]:
        return self._cap_add.split(";")

    @cap_add.setter
    def cap_add(self, cap_add: list):
        self._cap_add = ";".join(str(item) for item in cap_add)

    async def get(self) -> Container:
        return await asyncio.to_thread(self.client.containers.get, self.docker_id)

    async def _create_network_config(self) -> docker.types.NetworkingConfig:
        return await asyncio.to_thread(
            self.client.api.create_networking_config,
            {
                self.interfaces[0].network.name: self.client.api.create_endpoint_config(
                    ipv4_address=str(self.interfaces[0].ipaddress)
                )
            },
        )

    async def _create_host_config(self) -> docker.types.HostConfig:
        return await asyncio.to_thread(
            self.client.api.create_host_config, cap_add=self.cap_add
        )

    async def create(self):
        network_config = await self._create_network_config()
        host_config = await self._create_host_config()

        self.docker_id = (
            await asyncio.to_thread(
                self.client.api.create_container,
                self.image,
                name=self.name,
                tty=self.tty,
                detach=self.detach,
                networking_config=network_config,
                host_config=host_config,
            )
        )["Id"]

    @abstractmethod
    async def configure(self):
        pass

    async def start(self):
        pass

    async def delete(self):
        container = await self.get()
        await asyncio.to_thread(container.remove, v=True, force=True)


class Router(Appliance):
    __tablename__ = "router"

    id: Mapped[int] = mapped_column(ForeignKey("appliance.id"), primary_key=True)
    router_type: Mapped[str] = mapped_column(nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "router",
    }

    # TODO: refactor taking gateway from connections in cyst_infrastructure
    async def configure(self):
        container = await self.get()

        default_gateway = self.interfaces[0].network.bridge_gateway

        for interface in self.interfaces:
            if interface.network.name == constants.MANAGEMENT_NETWORK_NAME:
                if self.router_type == constants.ROUTER_TYPE_PERIMETER:
                    default_gateway = interface.network.bridge_gateway

        config_instructions = [
            "ip route del default",
            f"ip route add default via {default_gateway}",
            "iptables -t nat -A POSTROUTING -j MASQUERADE",
            "iptables-save",
        ]

        for instruction in config_instructions:
            await asyncio.to_thread(container.exec_run, instruction)

    async def connect_to_networks(self):
        for interface in self.interfaces[1:]:
            (await interface.network.get()).connect(
                self.name, ipv4_address=str(interface.ipaddress)
            )

    async def start(self):
        await self.create()
        (await self.get()).start()
        await self.connect_to_networks()
        await self.configure()


class Node(Appliance):
    __tablename__ = "node"

    id: Mapped[int] = mapped_column(ForeignKey("appliance.id"), primary_key=True)
    services: Mapped[list["Service"]] = relationship(
        back_populates="parent_node", cascade="all, delete-orphan"
    )
    ipc_mode: Mapped[str] = mapped_column(default="shareable", nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "node",
    }

    async def _create_host_config(self) -> docker.types.HostConfig:
        return await asyncio.to_thread(
            self.client.api.create_host_config,
            cap_add=self.cap_add,
            ipc_mode=self.ipc_mode,
        )

    async def configure(self):
        container = await self.get()

        setup_instructions = [
            "ip route del default",
            f"ip route add default via {str(self.interfaces[0].network.router_gateway)}",
        ]

        for instruction in setup_instructions:
            await asyncio.to_thread(container.exec_run, cmd=instruction)

    async def start(self):
        await self.create()
        await asyncio.to_thread((await self.get()).start)

        await self.configure()

        create_service_tasks = await self.create_services()
        await asyncio.gather(*create_service_tasks)

    async def create_services(self) -> set[asyncio.Task]:
        return {asyncio.create_task(service.create()) for service in self.services}

    async def delete(self):
        delete_services_tasks = await self.delete_services()
        await asyncio.gather(*delete_services_tasks)

        container = await self.get()
        await asyncio.to_thread(container.remove, v=True, force=True)

    async def delete_services(self) -> set[asyncio.Task]:
        return {asyncio.create_task(service.delete()) for service in self.services}


class Service(DockerContainerMixin, Base):
    __tablename__ = "service"

    parent_node_id: Mapped[int] = mapped_column(ForeignKey("node.id"))
    parent_node: Mapped["Node"] = relationship(back_populates="services")

    async def get(self) -> Container:
        return await asyncio.to_thread(self.client.containers.get, self.docker_id)

    async def create(self):
        kwargs = self.kwargs if self.kwargs is not None else {}

        container = await asyncio.to_thread(
            self.client.containers.create,
            image=self.image,
            name=self.name,
            detach=self.detach,
            network_mode=f"container:{self.parent_node.name}",
            pid_mode=f"container:{self.parent_node.name}",
            ipc_mode=f"container:{self.parent_node.name}",
            **kwargs,
        )
        self.docker_id = container.id

        await asyncio.to_thread(container.start)

    async def delete(self):
        container = await self.get()
        await asyncio.to_thread(container.remove, v=True, force=True)
