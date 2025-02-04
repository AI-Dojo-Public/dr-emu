from __future__ import annotations

import asyncio
from enum import Enum
from abc import abstractmethod
from enum import Enum
from typing import Optional, Any, reveal_type
from uuid import uuid1

import docker.types
from docker import DockerClient
from docker.errors import NotFound, NullResource, APIError
from docker.models.containers import Container
from docker.models.networks import Network as DockerNetwork
from docker.models.resource import Collection, Model
from docker.types import IPAMPool, IPAMConfig
from netaddr import IPAddress, IPNetwork
from sqlalchemy import ForeignKey, String, JSON, Column, Table
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    mapped_column,
    Mapped,
    MappedAsDataclass, declared_attr, validates
)
from sqlalchemy_utils import force_instant_defaults, ScalarListType, JSONType

from dr_emu.lib.logger import logger
from dr_emu.settings import settings
from shared import constants
from shared.classes import FileDescription

# TODO: add init methods with defaults to models instead of this?
force_instant_defaults()


class Base(AsyncAttrs, DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class DockerMixin:
    """
    Base class for docker models
    """

    docker_id: Mapped[str] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(unique=True)
    _client: DockerClient | None = None
    kwargs: Mapped[Optional[dict[Any, Any]]] = mapped_column(JSONType, nullable=True)

    @property
    def client(self):
        # testing issue
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    @abstractmethod
    async def create(self):
        """
        Create docker object
        :return: None
        """
        pass

    @abstractmethod
    async def get(self) -> Model | Collection[Model]:
        """
        Get docker object
        :return: Docker object
        """
        pass

    @abstractmethod
    async def delete(self):
        """
        Delete docker object
        :return: None
        """
        pass


class DockerContainerMixin(DockerMixin):
    """
    Base class for docker container models
    """

    environment: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=True)
    command: Mapped[str] = mapped_column(ScalarListType, nullable=True)
    healthcheck: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=True)
    detach: Mapped[bool] = mapped_column(default=True)
    tty: Mapped[bool] = mapped_column(default=True)
    image_id = mapped_column(ForeignKey("image.id"))

    @declared_attr
    def image(self) -> Mapped["Image"]:
        return relationship("Image")

    @abstractmethod
    async def create(self):
        """
        Create docker object
        :return: None
        """
        pass

    @abstractmethod
    async def get(self) -> Model | Collection[Model]:
        """
        Get docker object
        :return: Docker object
        """
        pass

    @abstractmethod
    async def delete(self):
        """
        Delete docker object
        :return: None
        """


class Network(DockerMixin, Base):
    """
    Docker network model.
    """

    __tablename__ = "network"

    name: Mapped[str] = mapped_column()
    driver: Mapped[str] = mapped_column(default="bridge")
    attachable: Mapped[bool] = mapped_column(default=True)
    interfaces: Mapped[list["Interface"]] = relationship(back_populates="network", cascade="all, delete-orphan")
    _ipaddress = mapped_column("ipaddress", String)
    _router_gateway = mapped_column("router_gateway", String)
    infrastructure_id: Mapped[int] = mapped_column(ForeignKey("infrastructure.id"))
    infrastructure: Mapped["Infrastructure"] = relationship(back_populates="networks")
    network_type: Mapped[str] = mapped_column()

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
        """
        Get a docker network object.
        :return: DockerNetwork
        """
        return await asyncio.to_thread(self.client.networks.get, self.docker_id)

    async def create(self):
        """
        Create a docker network.
        :return:
        """
        ipam_pool = IPAMPool(subnet=self._ipaddress, gateway=self.bridge_gateway)
        ipam_config = IPAMConfig(pool_configs=[ipam_pool])

        logger.debug("Creating network", ip=self._ipaddress, name=self.name)
        try:
            self.docker_id = (  # pyright: ignore [reportAttributeAccessIssue]
                await asyncio.to_thread(
                    self.client.networks.create,
                    self.name,
                    driver=self.driver,
                    ipam=ipam_config,
                    attachable=self.attachable,
                )
            ).id
        except APIError as err:
            logger.error(str(err), ip=self._ipaddress, name=self.name)
            raise err

        logger.debug("Network created", ip=self._ipaddress, name=self.name)

    async def delete(self):
        """
        Delete docker network object
        :return:
        """
        try:
            await asyncio.to_thread((await self.get()).remove)
        except (NotFound, NullResource):
            pass


class Interface(Base):
    """
    Interface model connecting networks and appliances with the addition of an ipaddress.
    """

    __tablename__ = "interface"

    network_id: Mapped[int] = mapped_column(ForeignKey("network.id"))
    network: Mapped["Network"] = relationship(back_populates="interfaces")
    _ipaddress = mapped_column("ipaddress", String)
    _original_ip = mapped_column("original_ip", String, nullable=True)
    appliance: Mapped["Appliance"] = relationship(back_populates="interfaces")
    appliance_id: Mapped[int] = mapped_column(ForeignKey("appliance.id"))

    @property
    def ipaddress(self):
        return IPAddress(self._ipaddress)

    @ipaddress.setter
    def ipaddress(self, ipaddress: IPAddress):
        self._ipaddress = str(ipaddress)

    @property
    def original_ip(self):
        return IPAddress(self._original_ip) if self._original_ip else None

    @original_ip.setter
    def original_ip(self, original_ip: IPAddress):
        self._original_ip = str(original_ip) if original_ip else None


appliances_volumes = Table(
    "appliances_volumes",
    Base.metadata,
    Column("appliance_id", ForeignKey("appliance.id"), primary_key=True),
    Column("volume_id", ForeignKey("volume.id"), primary_key=True),
)


class Appliance(DockerContainerMixin, Base):
    """
    Docker container model, parent model for Node and Router.
    """

    __tablename__ = "appliance"

    _cap_add = mapped_column("cap_add", String, default="NET_ADMIN")
    interfaces: Mapped[list["Interface"]] = relationship(back_populates="appliance", cascade="all, delete-orphan")
    type: Mapped[str]
    volumes: Mapped[list["Volume"]] = relationship(secondary=appliances_volumes, back_populates="appliances")
    infrastructure_id: Mapped[int] = mapped_column(ForeignKey("infrastructure.id"))

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "appliance",
    }

    @property
    def services(self) -> set[Service]:
        return self.image.services

    @property
    def cap_add(self) -> list[str]:
        return self._cap_add.split(";")

    @cap_add.setter
    def cap_add(self, cap_add: list[str]):
        self._cap_add = ";".join(str(item) for item in cap_add)

    async def get(self) -> Container:
        """
        Get a docker container object
        :return:
        """
        return await asyncio.to_thread(self.client.containers.get, self.docker_id)

    async def _create_network_config(self) -> docker.types.NetworkingConfig:
        """
        Create network configuration for docker container.
        :return: NetworkingConfig object
        """
        return await asyncio.to_thread(
            self.client.api.create_networking_config,
            {
                self.interfaces[0].network.name: self.client.api.create_endpoint_config(
                    ipv4_address=str(self.interfaces[0].ipaddress)
                )
            },
        )

    async def _create_host_config(self) -> docker.types.HostConfig:
        """
        Create host configuration for docker container.
        :return: HostConfig object
        """
        ksd = self.client.api.create_host_config(
            cap_add=self.cap_add,
            restart_policy={"Name": "always"},
            **self.kwargs if self.kwargs else {})

        reveal_type(ksd)
        return ksd

    async def create(self):
        """
        Create a docker container with necessary configurations.
        :return:
        """
        network_config = await self._create_network_config()
        host_config = await self._create_host_config()

        self.docker_id = (
            await asyncio.to_thread(
                self.client.api.create_container,
                self.image.name,
                name=self.name,
                tty=self.tty,
                detach=self.detach,
                networking_config=network_config,
                host_config=host_config,
                environment=self.environment,
                command=self.command,
                healthcheck=self.healthcheck,
                hostname=self.name,
            )
        )["Id"]

    @abstractmethod
    async def configure(self) -> None:
        pass

    async def start(self):
        pass

    async def delete(self):
        """
        Delete docker container represented by Appliance model (node or router)
        :return:
        """
        try:
            container = await self.get()
            await asyncio.to_thread(container.remove, v=True, force=True)  # type: ignore
        except (NotFound, NullResource):
            pass


class Infrastructure(Base):
    """
    Infrastructure model, bundles networks and appliances.
    """

    __tablename__ = "infrastructure"

    name: Mapped[str] = mapped_column(unique=True)
    _supernet = mapped_column("supernet", String, unique=True)
    networks: Mapped[list["Network"]] = relationship(back_populates="infrastructure", cascade="all, delete-orphan")
    routers: Mapped[list["Router"]] = relationship(back_populates="infrastructure", cascade="all, delete-orphan")
    nodes: Mapped[list["Node"]] = relationship(back_populates="infrastructure", cascade="all, delete-orphan")
    instance_id: Mapped[int] = mapped_column(ForeignKey("instance.id"), nullable=True)
    instance: Mapped["Instance"] = relationship(back_populates="infrastructure", single_parent=True)

    @property
    def supernet(self):
        return IPNetwork(self._supernet)

    @supernet.setter
    def supernet(self, supernet: IPNetwork):
        self._supernet = str(supernet)

    @property
    def volumes(self) -> set["Volume"]:
        volumes: set["Volume"] = set()
        for node in self.nodes:
            for volume in node.volumes:
                volumes.add(volume)
            for service in node.service_containers:
                for service_volume in service.volumes:
                    volumes.add(service_volume)
        return volumes


class Router(Appliance):
    """
    Router model representing docker container responsible for network routing.
    """

    __tablename__ = "router"

    id: Mapped[int] = mapped_column(ForeignKey("appliance.id"), primary_key=True)
    firewall_rules: Mapped[list["FirewallRule"]] = relationship(back_populates="router", cascade="all, delete-orphan")
    router_type: Mapped[str] = mapped_column(nullable=True)
    infrastructure: Mapped["Infrastructure"] = relationship(back_populates="routers")

    __mapper_args__ = {
        "polymorphic_identity": "router",
    }

    async def configure(self) -> None:
        """
        Configure ip routes, iptables on a router based on its type.
        :return:
        """
        config_instructions = ["ip route del default"]
        await self._setup_routes(self.infrastructure.routers, config_instructions)
        await self._setup_default_gateway(config_instructions)
        await self._setup_firewall(config_instructions)

        container = await self.get()

        for instruction in config_instructions:
            await asyncio.to_thread(container.exec_run, instruction)  # type: ignore

    async def _setup_default_gateway(self, config_instructions: list[str]):
        for interface in self.interfaces:
            if interface.network.network_type == constants.NETWORK_TYPE_MANAGEMENT:
                if self.router_type == constants.ROUTER_TYPE_PERIMETER:
                    config_instructions += [
                        f"ip route add default via {interface.network.bridge_gateway}",
                        "iptables -t nat -A POSTROUTING -j MASQUERADE",
                        "iptables-save",
                    ]

                else:
                    config_instructions.append(f"ip route add default via {interface.network.router_gateway}")

    async def _setup_firewall(self, config_instructions: list[str]):
        for fw_rule in self.firewall_rules:
            if fw_rule.policy == constants.FIREWALL_DENY:
                config_instructions += [
                    f"iptables -A FORWARD -s {fw_rule.src_net.ipaddress} -d {fw_rule.dst_net.ipaddress} -m state "
                    f"--state RELATED,ESTABLISHED -j ACCEPT",
                    f"iptables -A FORWARD -s {fw_rule.src_net.ipaddress} -d {fw_rule.dst_net.ipaddress} -j DROP",
                ]

    async def _setup_routes(self, routers: list[Router], config_instructions: list[str]):
        routes_config: list[dict[str, Any]] = []
        for router in routers:
            if self == router:
                continue
            routes: dict[str, Any] = {"via": "", "to": []}
            for interface in router.interfaces:
                if interface.network.network_type == constants.NETWORK_TYPE_MANAGEMENT:
                    routes["via"] = interface.ipaddress
                else:
                    routes["to"].append(interface.network.ipaddress)
            routes_config.append(routes)

        for route_config in routes_config:
            for network_route in route_config["to"]:
                config_instructions.append(f"ip route add {network_route} via {route_config['via']}")

    async def connect_to_networks(self):
        """
        Connect docker container representing a Router to other docker networks, where they will act as a
        gateway for Nodes.
        :return:
        """
        # Filtering instances with unique values of attribute "x"
        unique_networks = {self.interfaces[0].network}
        unique_interfaces: list[Interface] = []

        for interface in self.interfaces[1:]:
            if interface.network not in unique_networks:
                unique_interfaces.append(interface)
                unique_networks.add(interface.network)

        for interface in unique_interfaces:
            logger.debug(f"Connecting router {self.name} to network {interface.network.name}")
            (await interface.network.get()).connect(self.name, ipv4_address=str(interface.ipaddress))

    async def start(self):
        """
        Start a docker container representing a Router.
        :return:
        """
        try:
            await self.create()
            await asyncio.to_thread((await self.get()).start)
        except APIError as err:
            logger.error(
                str(err),
                container_name=self.name,
                interfaces=[str(interface.ipaddress) for interface in self.interfaces],
            )
            raise err

        await self.connect_to_networks()


class FirewallRule(Base):
    """
    Represents a firewall rule, which applies a firewall policy based on source and destination.
    """

    __tablename__ = "firewall_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    src_net_id: Mapped[int] = mapped_column(ForeignKey("network.id"))
    dst_net_id: Mapped[int] = mapped_column(ForeignKey("network.id"))
    src_net: Mapped["Network"] = relationship("Network", foreign_keys=[src_net_id])
    dst_net: Mapped["Network"] = relationship("Network", foreign_keys=[dst_net_id])
    router_id: Mapped[int] = mapped_column(ForeignKey("router.id"))
    router: Mapped["Router"] = relationship(back_populates="firewall_rules")
    service: Mapped[str] = mapped_column()
    policy: Mapped[str] = mapped_column()


class Node(Appliance):
    """
    Node model representing docker container acting as a physical machine containing services
    """

    __tablename__ = "node"

    id: Mapped[int] = mapped_column(ForeignKey("appliance.id"), primary_key=True)
    service_containers: Mapped[list["ServiceContainer"]] = relationship(back_populates="parent_node",
                                                                        cascade="all, delete-orphan")
    ipc_mode: Mapped[str] = mapped_column(default="shareable", nullable=True)
    infrastructure: Mapped["Infrastructure"] = relationship(back_populates="nodes")
    depends_on: Mapped[dict[str, str]] = mapped_column(JSONType, default=dict())
    config_instructions: list[str] | list[list[str]] = []
    __mapper_args__ = {
        "polymorphic_identity": "node",
    }

    async def _create_host_config(self) -> docker.types.HostConfig:
        """
        Create host configuration for docker container.
        :return:
        """
        volumes: list[str] = []
        for volume in self.volumes:
            volumes.append(f"{volume.name}:{volume.bind}")

        return await asyncio.to_thread(
            self.client.api.create_host_config,
            cap_add=self.cap_add,
            ipc_mode=self.ipc_mode,
            restart_policy={"Name": "always"},
            binds=volumes,
            **self.kwargs if self.kwargs else {},
        )

    async def configure(self):
        """
        Configure ip tables on a Node.
        :return:
        """
        container = await self.get()

        setup_instructions = [
                                 "ip route del default",
                                 f"ip route add default via {str(self.interfaces[0].network.router_gateway)}",
                             ] + self.config_instructions

        for instruction in setup_instructions:
            await asyncio.to_thread(container.exec_run, cmd=instruction, privileged=True, user="0")  # type: ignore

    async def create(self):
        """
        Create a docker container representing a Node.
        :return:
        """
        await super().create()
        create_service_tasks: set[asyncio.Task[Any]] = await self.create_services()
        await asyncio.gather(*create_service_tasks)

    async def start(self):
        """
        Start a docker container representing a Node.
        :return:
        """
        try:
            await asyncio.to_thread((await self.get()).start)
        except APIError as err:
            logger.error(str(err), container_name=self.name, ipaddress=str(self.interfaces[0].ipaddress))
            raise err

        start_service_tasks = await self.start_services()
        await asyncio.gather(*start_service_tasks)

    async def create_services(self) -> set[asyncio.Task[Any]]:
        """
        Create services in form of docker containers, that should be connected to this Node.
        :return:
        """
        return {asyncio.create_task(service.create()) for service in self.service_containers}

    async def start_services(self) -> set[asyncio.Task[None]]:
        """
        Create services in form of docker containers, that should be connected to this Node.
        :return:
        """
        return {asyncio.create_task(service.start()) for service in self.service_containers}

    async def delete(self) -> None:
        """
        Stop and delete docker container representing a Node
        :return:
        """

        delete_services_tasks: set[asyncio.Task[None]] = await self.delete_services()
        await asyncio.gather(*delete_services_tasks)

        await super().delete()

    async def delete_services(self) -> set[asyncio.Task[None]]:
        """
        Delete docker containers representing services connected to this Node.
        :return:
        """
        return {asyncio.create_task(service.delete()) for service in self.service_containers}


class Attacker(Node):
    __mapper_args__ = {
        "polymorphic_identity": "attacker",
    }

    async def start(self):
        """
        Start a docker container representing an Attacker.
        :return:
        """

        container = await self.get()
        await asyncio.to_thread(container.start)

        # connect attacker to cryton network
        if not settings.ignore_management_network:
            self.client.networks.get(settings.management_network_name).connect(container)
        start_service_tasks = await self.start_services()
        await asyncio.gather(*start_service_tasks)

    async def configure(self):
        """
        Configure ip tables on a Node.
        :return:
        """
        pass
        # container = await self.get()
        #
        # setup_instructions = [
        #     f"ip route add  via {str(self.interfaces[0].network.router_gateway)}",
        # ]
        #
        # for instruction in setup_instructions:
        #     await asyncio.to_thread(container.exec_run, cmd=instruction)


class Dns(Node):
    __mapper_args__ = {
        "polymorphic_identity": "dns",
    }


services_volumes = Table(
    "services_volumes",
    Base.metadata,
    Column("service_container_id", ForeignKey("service_container.id"), primary_key=True),  # type: ignore
    Column("volume_id", ForeignKey("volume.id"), primary_key=True),  # type: ignore
)


class ServiceContainer(DockerContainerMixin, Base):
    """
    Service model representing docker container acting as a service running on Node, connected via network_mode.
    """

    __tablename__ = "service_container"

    parent_node_id: Mapped[int] = mapped_column(ForeignKey("node.id"))
    parent_node: Mapped["Node"] = relationship(back_populates="service_containers")
    dependencies: Mapped[list["DependsOn"]] = relationship(
        back_populates="dependant",
        foreign_keys="DependsOn.dependant_service_id",
        cascade="all, delete-orphan",
    )
    volumes: Mapped[list["Volume"]] = relationship(secondary=services_volumes, back_populates="service_containers")
    model_type: Mapped[str]

    __mapper_args__ = {
        "polymorphic_on": "model_type",
        "polymorphic_identity": "service",
    }

    async def get(self) -> Container:
        """
        Get a docker container representing a Service.
        :return:
        """
        return await asyncio.to_thread(self.client.containers.get, self.docker_id)

    async def create(self) -> None:
        """
        Create docker container representing a Service.
        :return:
        """
        kwargs = self.kwargs if self.kwargs is not None else {}
        volumes: list[str] = []
        for volume in self.volumes:
            volumes.append(f"{volume.name}:{volume.bind}")
        container = await asyncio.to_thread(
            self.client.containers.create,
            image=self.image.name,
            name=self.name,
            detach=self.detach,  # type: ignore
            network_mode=f"container:{self.parent_node.name}",
            pid_mode=f"container:{self.parent_node.name}",
            ipc_mode=f"container:{self.parent_node.name}",
            environment=self.environment,
            command=self.command,
            healthcheck=self.healthcheck,
            tty=self.tty,
            volumes=volumes,
            **kwargs,
        )

        self.docker_id = container.id

    async def start(self):
        if self.dependencies:
            if not await self.wait_for_dependency():
                raise RuntimeError(f"Some dependency of container {self.name} didn't start within timeout")

        try:
            await asyncio.to_thread((await self.get()).start)
        except APIError as err:
            logger.error(str(err), container_name=self.name)
            raise err

    async def delete(self):
        """
        Stop and delete a docker container representing a Service.
        :return:
        """
        try:
            container = await self.get()
            await asyncio.to_thread(container.remove, v=True, force=True)  # type: ignore
        except (NotFound, NullResource):
            pass

    async def wait_for_dependency(self, timeout: int = 35) -> bool:
        async def check_dependency(dependency_model: DependsOn):
            count = 0
            while count < timeout:
                try:
                    container_info: dict[str, Any] = await asyncio.to_thread(
                        self.client.api.inspect_container,
                        dependency_model.dependency.name,
                    )
                except (NotFound, NullResource, APIError):
                    logger.debug(f"Waiting for dependency container: {dependency_model.dependency.name}")
                    await asyncio.sleep(1)
                    count += 1
                    continue

                if dependency_model.state == constants.SERVICE_HEALTHY:  # type: ignore
                    if container_info["State"]["Status"] != "running":
                        await asyncio.sleep(1)
                        count += 1
                        continue
                    else:
                        try:
                            container_health = container_info["State"]["Health"]["Status"]
                            if container_health == "healthy":
                                return True
                            else:
                                logger.debug(f"Waiting for healthy container: {dependency_model.dependency.name}")
                                await asyncio.sleep(1)
                                count += 1
                        except KeyError:
                            logger.error(
                                f"Container {dependency_model.dependency.name} doesn't have a health check. Changing "
                                f"dependency to 'container_started'"
                            )
                            dependency_model.state = constants.SERVICE_STARTED

                elif dependency_model.state == constants.SERVICE_STARTED:
                    if container_info["State"]["Status"] == "running":
                        return True
                    else:
                        logger.debug(f"Waiting for dependency container: {dependency_model.dependency.name}")
                        await asyncio.sleep(1)
                        count += 1

        for dependency in self.dependencies:
            if await check_dependency(dependency) is True:
                continue
            else:
                return False

        return True


class ServiceAttacker(ServiceContainer):
    __mapper_args__ = {
        "polymorphic_on": "model_type",
        "polymorphic_identity": "attacker",
    }


class ContainerState(Enum):
    service_healthy = constants.SERVICE_HEALTHY
    service_started = constants.SERVICE_STARTED


class DependsOn(Base):
    """Class for dependency container startup"""

    __tablename__ = "depends_on"
    dependant_service_id: Mapped[int] = mapped_column(ForeignKey("service_container.id"))
    dependency_service_id: Mapped[int] = mapped_column(ForeignKey("service_container.id"))
    dependant: Mapped["ServiceContainer"] = relationship(back_populates="dependencies",
                                                         foreign_keys=[dependant_service_id])
    dependency: Mapped["ServiceContainer"] = relationship(foreign_keys=[dependency_service_id])
    state: Mapped[ContainerState] = mapped_column()


class Template(Base):
    __tablename__ = "template"
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column(JSON)
    runs: Mapped[list["Run"]] = relationship(back_populates="template")


class Run(Base):
    __tablename__ = "run"
    name: Mapped[str] = mapped_column()
    template: Mapped["Template"] = relationship(back_populates="runs")
    template_id: Mapped[int] = mapped_column(ForeignKey("template.id"))
    instances: Mapped[list["Instance"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Instance(Base):
    __tablename__ = "instance"
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"))
    run: Mapped["Run"] = relationship(back_populates="instances")
    infrastructure: Mapped["Infrastructure"] = relationship(
        back_populates="instance", uselist=False, cascade="all, delete, delete-orphan"
    )


class Volume(DockerMixin, Base):
    __tablename__ = "volume"
    bind: Mapped[str] = mapped_column()  # Place where the volume will be mounted inside the container
    local: Mapped[bool] = mapped_column()
    appliances: Mapped[list["Appliance"]] = relationship(back_populates="volumes", secondary=appliances_volumes)
    service_containers: Mapped[list["ServiceContainer"]] = relationship(back_populates="volumes",
                                                                        secondary=services_volumes)

    async def create(self):
        """
        Create docker object
        :return: None
        """
        self.docker_id = self.client.volumes.create(name=self.name).id

    async def get(self):
        """
        Get docker object
        :return: Docker object
        """
        return self.client.volumes.get(volume_id=self.docker_id)

    async def delete(self):
        """
        Delete docker object
        :return: None
        """
        volume = await self.get()
        volume.remove(force=True)


images_services = Table(
    "images_services",
    Base.metadata,
    Column("service_id", ForeignKey("service.id"), primary_key=True),  # type: ignore
    Column("image_id", ForeignKey("image.id"), primary_key=True),  # type: ignore
)


class Service(MappedAsDataclass, Base):
    __tablename__ = "service"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    type: Mapped[str] = mapped_column()
    variable_override: Mapped[dict[str, str | int]] = mapped_column(JSONType, default_factory=dict)
    version: Mapped[str] = mapped_column(default="")
    cves: Mapped[str] = mapped_column(default="")
    # accounts: Mapped[list["Account"]] = relationship(back_populates="service")

    def __key(self):
        instance_key = [self.type, self.version, self.cves]
        for key, value in self.variable_override.items():
            instance_key.append(f"{key}:{value}")
        return tuple(instance_key)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Service):
            return self.__key() == other.__key()
        return NotImplemented


class ImageState(Enum):
    initialized = "initialized"
    building = "building"
    ready = "ready"


class Image(MappedAsDataclass, Base):
    __tablename__ = "image"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    services: Mapped[set["Service"]] = relationship(secondary=images_services, cascade="all, delete",)
    data: list[FileDescription]
    packages: Mapped[list[str]] = mapped_column(ScalarListType(separator="|"), default_factory=list)
    firehole_config: Mapped[str] = mapped_column(default="")
    pull: Mapped[bool] = mapped_column(default=False)
    name: Mapped[str] = mapped_column(unique=True, default=None)
    state: Mapped[ImageState] = mapped_column(default=ImageState.initialized)
    _data: list[str] = mapped_column("data", ScalarListType(separator="|"), default_factory=list)

    @property
    def data(self):
        return [FileDescription(contents=eval(data)[1], image_file_path=eval(data)[0]) for data in self._data]

    @data.setter
    def data(self, data: list[FileDescription]):
        self._data = [str((file_decs.image_file_path, file_decs.contents)) for file_decs in data]

    def __key(self):
        instance_key = [self.firehole_config, self.pull]
        for service in self.services:
            instance_key += [service.type, service.version, service.cves]
            for key, value in service.variable_override.items():
                instance_key.append(f"{key}:{value}")
        [instance_key.append(data_config) for data_config in self.data]
        return tuple(instance_key)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Image):
            return self.__key() == other.__key()
        return NotImplemented
