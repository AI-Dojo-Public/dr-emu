from __future__ import annotations

import asyncio
import enum
import re
from abc import abstractmethod
from typing import Optional

import docker.types
import requests
from docker import DockerClient
from docker.errors import NotFound, APIError
from docker.models.containers import Container
from docker.models.networks import Network as DockerNetwork
from docker.types import IPAMPool, IPAMConfig
from netaddr import IPAddress, IPNetwork
from sqlalchemy import ForeignKey, String, JSON, Column, Table
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    mapped_column,
    Mapped,
)
from sqlalchemy_utils import force_instant_defaults, ScalarListType, JSONType

from dr_emu.lib.exceptions import ContainerNotRunning, PackageNotAccessible
from dr_emu.lib.logger import logger
from dr_emu.resources import docker_client
from parser.util import constants

# TODO: add init methods with defaults to models instead of this?
force_instant_defaults()


class Base(AsyncAttrs, DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class DockerMixin:
    """
    Base class for docker models
    """

    docker_id: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()
    client: DockerClient = docker_client
    kwargs: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)

    @abstractmethod
    async def create(self):
        """
        Create docker object
        :return: None
        """
        pass

    @abstractmethod
    async def get(self):
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

    image: Mapped[str] = mapped_column(default=constants.IMAGE_BASE)
    environment: Mapped[dict] = mapped_column(JSONType, nullable=True)
    command: Mapped[str] = mapped_column(ScalarListType, nullable=True)
    healthcheck: Mapped[dict] = mapped_column(JSONType, nullable=True)
    detach: Mapped[bool] = mapped_column(default=True)
    tty: Mapped[bool] = mapped_column(default=True)

    @abstractmethod
    async def create(self):
        """
        Create docker object
        :return: None
        """
        pass

    @abstractmethod
    async def get(self):
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
        self.docker_id = (
            await asyncio.to_thread(
                self.client.networks.create,
                self.name,
                driver=self.driver,
                ipam=ipam_config,
                attachable=self.attachable,
            )
        ).id
        logger.debug("Network created", ip=self._ipaddress, name=self.name)

    async def delete(self):
        """
        Delete docker network object
        :return:
        """
        try:
            await asyncio.to_thread((await self.get()).remove)
        except (NotFound, NotFound):
            pass


class Interface(Base):
    """
    Interface model connecting networks and appliances with the addition of an ipaddress.
    """

    __tablename__ = "interface"

    network_id: Mapped[int] = mapped_column(ForeignKey("network.id"), primary_key=True)
    network: Mapped["Network"] = relationship(back_populates="interfaces")
    _ipaddress = mapped_column("ipaddress", String)
    appliance: Mapped["Appliance"] = relationship(back_populates="interfaces")
    appliance_id: Mapped[int] = mapped_column(ForeignKey("appliance.id"), primary_key=True)

    @property
    def ipaddress(self):
        return IPAddress(self._ipaddress)

    @ipaddress.setter
    def ipaddress(self, ipaddress: IPAddress):
        self._ipaddress = str(ipaddress)


class Appliance(DockerContainerMixin, Base):
    """
    Docker container model, parent model for Node and Router.
    """

    __tablename__ = "appliance"

    _cap_add = mapped_column("cap_add", String, default="NET_ADMIN")
    interfaces: Mapped[list["Interface"]] = relationship(back_populates="appliance", cascade="all, delete-orphan")
    type: Mapped[str]
    infrastructure_id: Mapped[int] = mapped_column(ForeignKey("infrastructure.id"))

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
        return await asyncio.to_thread(
            self.client.api.create_host_config,
            cap_add=self.cap_add,
            restart_policy={"Name": "always"},
        )

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
                self.image,
                name=self.name,
                tty=self.tty,
                detach=self.detach,
                networking_config=network_config,
                host_config=host_config,
                environment=self.environment,
                command=self.command,
                healthcheck=self.healthcheck,
            )
        )["Id"]

    @abstractmethod
    async def configure(self, *args):
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
        except NotFound:
            pass


class Infrastructure(Base):
    """
    Infrastructure model, bundles networks and appliances.
    """

    __tablename__ = "infrastructure"

    name: Mapped[str] = mapped_column()
    networks: Mapped[list["Network"]] = relationship(back_populates="infrastructure", cascade="all, delete-orphan")
    routers: Mapped[list["Router"]] = relationship(back_populates="infrastructure", cascade="all, delete-orphan")
    nodes: Mapped[list["Node", "Attacker"]] = relationship(
        back_populates="infrastructure", cascade="all, delete-orphan"
    )
    instance_id: Mapped[int] = mapped_column(ForeignKey("instance.id"))
    instance: Mapped["Instance"] = relationship(back_populates="infrastructure", single_parent=True)


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

    # TODO: refactor taking gateway from connections in cyst_infrastructure
    async def configure(self, routers: list[Router]):
        """
        Configure ip routes, iptables on a router based on its type.
        :return:
        """
        config_instructions = ["ip route del default"]
        await self._setup_routes(routers, config_instructions)
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

    async def _setup_routes(self, routers: list[Router], config_instructions):
        routes_config = []
        for router in routers:
            if self == router:
                continue
            routes = {"via": "", "to": []}
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
        for interface in self.interfaces[1:]:
            (await interface.network.get()).connect(self.name, ipv4_address=str(interface.ipaddress))

    async def start(self):
        """
        Start a docker container representing a Router.
        :return:
        """
        await self.create()
        await asyncio.to_thread((await self.get()).start)
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
    services: Mapped[list["Service"]] = relationship(back_populates="parent_node", cascade="all, delete-orphan")
    ipc_mode: Mapped[str] = mapped_column(default="shareable", nullable=True)
    infrastructure: Mapped["Infrastructure"] = relationship(back_populates="nodes")
    depends_on: Mapped[dict] = mapped_column(JSONType, default={})

    __mapper_args__ = {
        "polymorphic_identity": "node",
    }

    async def _create_host_config(self) -> docker.types.HostConfig:
        """
        Create host configuration for docker container.
        :return:
        """
        return await asyncio.to_thread(
            self.client.api.create_host_config,
            cap_add=self.cap_add,
            ipc_mode=self.ipc_mode,
            restart_policy={"Name": "always"},
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
        ]

        for instruction in setup_instructions:
            await asyncio.to_thread(container.exec_run, cmd=instruction, privileged=True, user="0")  # type: ignore

    async def create(self):
        """
        Create a docker container representing a Node.
        :return:
        """
        await super().create()
        create_service_tasks = await self.create_services()
        await asyncio.gather(*create_service_tasks)

    async def start(self):
        """
        Start a docker container representing a Node.
        :return:
        """
        await asyncio.to_thread((await self.get()).start)

        start_service_tasks = await self.start_services()
        await asyncio.gather(*start_service_tasks)

    async def create_services(self) -> set[asyncio.Task]:
        """
        Create services in form of docker containers, that should be connected to this Node.
        :return:
        """
        return {asyncio.create_task(service.create()) for service in self.services}

    async def start_services(self) -> set[asyncio.Task]:
        """
        Create services in form of docker containers, that should be connected to this Node.
        :return:
        """
        return {asyncio.create_task(service.start()) for service in self.services}

    async def delete(self):
        """
        Stop and delete docker container representing a Node
        :return:
        """

        delete_services_tasks = await self.delete_services()
        await asyncio.gather(*delete_services_tasks)

        await super().delete()

    async def delete_services(self) -> set[asyncio.Task]:
        """
        Delete docker containers representing services connected to this Node.
        :return:
        """
        return {asyncio.create_task(service.delete()) for service in self.services}


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
        self.client.networks.get(constants.CRYTON_NETWORK_NAME).connect(container)
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
        # # TODO: what routes to add?
        # setup_instructions = [
        #     f"ip route add  via {str(self.interfaces[0].network.router_gateway)}",
        # ]
        #
        # for instruction in setup_instructions:
        #     await asyncio.to_thread(container.exec_run, cmd=instruction)


class Service(DockerContainerMixin, Base):
    """
    Service model representing docker container acting as a service running on Node, connected via network_mode.
    """

    __tablename__ = "service"

    parent_node_id: Mapped[int] = mapped_column(ForeignKey("node.id"))
    parent_node: Mapped["Node"] = relationship(back_populates="services")
    dependencies: Mapped[list["DependsOn"]] = relationship(  # TODO: is this the same as depends_on in Node?
        back_populates="dependant",
        foreign_keys="DependsOn.dependant_service_id",
        cascade="all, delete-orphan",
    )

    async def get(self) -> Container:
        """
        Get a docker container representing a Service.
        :return:
        """
        return await asyncio.to_thread(self.client.containers.get, self.docker_id)

    async def create(self):
        """
        Create docker container representing a Service.
        :return:
        """
        kwargs = self.kwargs if self.kwargs is not None else {}

        container = await asyncio.to_thread(
            self.client.containers.create,
            image=self.image,
            name=self.name,
            detach=self.detach,
            network_mode=f"container:{self.parent_node.name}",
            pid_mode=f"container:{self.parent_node.name}",
            ipc_mode=f"container:{self.parent_node.name}",
            environment=self.environment,
            command=self.command,
            healthcheck=self.healthcheck,
            tty=self.tty,
            **kwargs,
        )

        self.docker_id = container.id

    async def start(self):
        if self.dependencies:
            if not await self.wait_for_dependency():
                raise RuntimeError(f"Some dependency of container {self.name} didn't start within timeout")
        await asyncio.to_thread((await self.get()).start)

    async def delete(self):
        """
        Stop and delete a docker container representing a Service.
        :return:
        """
        try:
            container = await self.get()
            await asyncio.to_thread(container.remove, v=True, force=True)  # type: ignore
        except NotFound:
            pass

    async def wait_for_dependency(self, timeout=35) -> bool:
        async def check_dependency(dependency_model: DependsOn):
            count = 0
            while count < timeout:
                try:
                    container_info = await asyncio.to_thread(
                        self.client.api.inspect_container,
                        dependency_model.dependency.name,
                    )
                except (NotFound, APIError):
                    logger.debug(f"Waiting for dependency container: {dependency_model.dependency.name}")
                    await asyncio.sleep(1)
                    count += 1
                    continue

                if dependency_model.state == constants.SERVICE_HEALTHY:
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


agent_association_table = Table(
    "agent_association_table",
    Base.metadata,
    Column("agent_id", ForeignKey("agent.id")),
    Column("run_id", ForeignKey("run.id")),
)


class ContainerState(enum.Enum):
    service_healthy = constants.SERVICE_HEALTHY
    service_started = constants.SERVICE_STARTED


class DependsOn(Base):
    """Class for dependency container startup"""

    __tablename__ = "depends_on"
    dependant_service_id: Mapped[int] = mapped_column(ForeignKey("service.id"))
    dependency_service_id: Mapped[int] = mapped_column(ForeignKey("service.id"))

    dependant: Mapped["Service"] = relationship(back_populates="dependencies", foreign_keys=[dependant_service_id])
    dependency: Mapped["Service"] = relationship(foreign_keys=[dependency_service_id])

    state: Mapped[ContainerState] = mapped_column()


class AgentInstallationMethod(Base):
    """Class for different types of agent installation"""

    __tablename__ = "agent_installation_method"
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent.id"))
    agent: Mapped["Agent"] = relationship(back_populates="install_method")
    package_name: Mapped[str] = mapped_column()
    type: Mapped[str]

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "agent_installation_method",
    }

    @abstractmethod
    async def get_install_command(self) -> str:
        """
        Create installation command to install agent from specified source
        """

    @abstractmethod
    async def get_update_command(self):
        """
        Create update command to update agent package from specified source
        """


class AgentPypi(AgentInstallationMethod):
    __mapper_args__ = {
        "polymorphic_identity": "pypi",
    }

    async def get_install_command(self) -> str:
        return f"pip install {self.package_name}"

    async def get_update_command(self) -> str:
        return f"pip install -U {self.package_name}"


class AgentLocal(AgentInstallationMethod):
    __tablename__ = "agent_local_install"
    id: Mapped[int] = mapped_column(ForeignKey("agent_installation_method.id"), primary_key=True)
    path: Mapped[str] = mapped_column()

    __mapper_args__ = {
        "polymorphic_identity": "local",
    }

    async def get_install_command(self) -> str:
        return f"pip install {self.path}"

    async def get_update_command(self) -> str:
        return f"pip install -U {self.path}"


class AgentGit(AgentInstallationMethod):
    __tablename__ = "agent_git_install"
    id: Mapped[int] = mapped_column(ForeignKey("agent_installation_method.id"), primary_key=True)
    access_token: Mapped[str] = mapped_column(default="")  # TODO: secure the token
    username: Mapped[str] = mapped_column()
    host: Mapped[str] = mapped_column()
    owner: Mapped[str] = mapped_column()
    repo_name: Mapped[str] = mapped_column()

    __mapper_args__ = {
        "polymorphic_identity": "git",
    }

    @property
    def git_url(self) -> str:
        url = f"https://{self.username}:{self.access_token}@{self.host}/{self.owner}/{self.repo_name}"
        if "#subdirectory" in self.repo_name:
            url += "/"
        else:
            url += ".git"
        return url

    # TODO: gitlab with access token redirects by default?
    # NOT USED
    async def validate_project_existence(self):
        """
        Check that the project url exists and is accessible
        """
        url = f"https://{self.username}:{self.access_token}@{self.host}/{self.owner}/{self.repo_name}.git"
        try:
            response = requests.get(
                url,
                allow_redirects=False,
            )
        except requests.exceptions.ConnectionError as ex:
            raise ex

        if response.status_code != 200:
            raise PackageNotAccessible(f"Cannot access git url. status_code: {response.status_code}, url: {url}")

    async def get_install_command(self) -> str:
        return f"python3 -m pip install '{self.package_name} @ git+{self.git_url}'"

    async def get_update_command(self) -> str:
        return f"python3 -m pip install -U '{self.package_name} @ git+{self.git_url}'"


class Agent(Base):
    __tablename__ = "agent"
    name: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column()  # Defender or Attacker
    install_method: Mapped["AgentInstallationMethod"] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    runs: Mapped[list["Run"]] = relationship(secondary=agent_association_table, back_populates="agents")

    @staticmethod
    async def _execute_command(command):
        """
        Execute agent related command on CYST container.
        """
        if (cyst_container := docker_client.containers.get("cyst-demo")).status != "running":
            raise ContainerNotRunning("Docker container with CYST is not running")

        result = await asyncio.to_thread(cyst_container.exec_run, command)
        if result.exit_code != 0:
            raise RuntimeError(result.output)

        return result

    async def install(self):
        """
        Download the agent from gitlab repository and install it in the cyst container
        """
        installation_command = await self.install_method.get_install_command()
        installation_result = await self._execute_command(installation_command)

        # check installation
        pip_list_result = await self._execute_command("pip list")
        if (
            re.search(
                self.install_method.package_name,
                str(pip_list_result.output),
                re.IGNORECASE,
            )
            is None
        ):
            raise RuntimeError(f"Agent was not found in installed packages. {installation_result}")

    async def update_package(self):
        """
        Update agent package.
        """
        update_command = await self.install_method.get_update_command()
        await self._execute_command(update_command)


class Template(Base):
    __tablename__ = "template"
    name: Mapped[str] = mapped_column()
    description: Mapped[dict] = mapped_column(JSON)
    runs: Mapped[list["Run"]] = relationship(back_populates="template")


class Run(Base):
    __tablename__ = "run"
    name: Mapped[str] = mapped_column()
    agents: Mapped[list["Agent"]] = relationship(
        secondary=agent_association_table,
        back_populates="runs",
    )
    template: Mapped["Template"] = relationship(back_populates="runs")
    template_id: Mapped[int] = mapped_column(ForeignKey("template.id"))
    instances: Mapped[list["Instance"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Instance(Base):
    __tablename__ = "instance"
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"))
    run: Mapped["Run"] = relationship(back_populates="instances")
    agent_instances: Mapped[str] = mapped_column()
    infrastructure: Mapped["Infrastructure"] = relationship(
        back_populates="instance", uselist=False, cascade="all, delete, delete-orphan"
    )
