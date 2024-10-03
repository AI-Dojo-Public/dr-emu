from dataclasses import dataclass, field, asdict
from typing import Any
from dr_emu.lib.logger import logger


def sec_to_nano(seconds: int) -> int:
    """
    Convert seconds to nanoseconds.
    :param seconds: Number of seconds
    :return: Number of nanoseconds
    """
    return seconds * 10 ** 9


@dataclass
class Healthcheck:
    """
    Container healthcheck.
    """

    test: list[str]
    interval: int
    timeout: int
    retries: int


@dataclass(frozen=True)
class ServiceTag:
    """
    Tag used to match a single service and possibly a version.
    """

    type: str
    version: str = ""
    exploits: set[str] = field(default_factory=set)
    depends_on: set["ServiceTag"] = field(default_factory=set)


@dataclass
class Volume:
    """
    Serializable alternative for DB model.
    """

    name: str  # Name of volume / Path on host
    bind: str  # Path on container
    local: bool = False


@dataclass
class Container:
    """
    Container with ServiceTags and necessary information to run a Docker container.
    """

    image: str
    description: str = ""
    entrypoint: list[str] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    _healthcheck: Healthcheck | None = None
    volumes: list[Volume] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    kwargs: dict[str, Any] = field(default_factory=dict)
    requires: list[ServiceTag] = field(default_factory=list)
    can_be_combined: bool = False
    is_attacker: bool = False

    @property
    def healthcheck(self) -> dict[str, str]:
        return asdict(self._healthcheck) if self._healthcheck else dict()


@dataclass
class ServiceContainer(Container):
    tag: ServiceTag = ServiceTag("")


@dataclass
class NodeContainer(Container):
    services: list[ServiceTag] = field(default_factory=list)


# TODO: unique variables accross infras under a single run
DEFAULT = NodeContainer(
    "registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/node:latest", services=[ServiceTag("bash"), ServiceTag("sh")]
)
FIREHOLE = NodeContainer(
    "registry.gitlab.ics.muni.cz:443/ai-dojo/firehole", services=[ServiceTag("bash"), ServiceTag("sh")]
)
ROUTER = NodeContainer("registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/router:latest",
                       services=[ServiceTag("iptables")])
DNS_SERVER = NodeContainer(
    "registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/node:latest",
    services=[ServiceTag("bash"), ServiceTag("sh"), ServiceTag("coredns", "1.11.1")],
    volumes=[Volume("core-dns", "/etc/coredns")],
)

SERVICE_CONTAINERS = [
    ServiceContainer(
        "sadparad1se/metasploit-framework:rpc",
        tag=ServiceTag("metasploit", "0.1.0"),
        environment={
            "METASPLOIT_RPC_USERNAME": "cryton",
            "METASPLOIT_RPC_PASSWORD": "cryton",
        },
        can_be_combined=True,
        is_attacker=True,
    ),
    ServiceContainer(
        "bcsecurity/empire:v4.10.0",
        tag=ServiceTag("empire", "4.10.0"),
        command=["server", "--username", "cryton", "--password", "cryton"],
        can_be_combined=True,
        is_attacker=True,
    ),
    ServiceContainer(
        "coredns/coredns",
        tag=ServiceTag("coredns", "1.11.1"),
        volumes=[Volume("core-dns", "/etc/coredns")],
        command=["-conf", "/etc/coredns/Corefile"],
        kwargs={"restart_policy": {"Name": "on-failure"}},
    ),
    ServiceContainer(
        "registry.gitlab.ics.muni.cz:443/cryton/cryton/worker:2",
        tag=ServiceTag("scripted_actor"),
        environment={
            "CRYTON_WORKER_NAME": "attacker",
            "CRYTON_WORKER_DEBUG": True,
            "CRYTON_WORKER_METASPLOIT_PORT": 55553,
            "CRYTON_WORKER_METASPLOIT_HOST": "127.0.0.1",
            "CRYTON_WORKER_METASPLOIT_USERNAME": "cryton",
            "CRYTON_WORKER_METASPLOIT_PASSWORD": "cryton",
            "CRYTON_WORKER_METASPLOIT_SSL": True,
            "CRYTON_WORKER_METASPLOIT_REQUIRE": True,
            "CRYTON_WORKER_RABBIT_HOST": "cryton-rabbit",
            "CRYTON_WORKER_RABBIT_PORT": 5672,
            "CRYTON_WORKER_RABBIT_USERNAME": "cryton",
            "CRYTON_WORKER_RABBIT_PASSWORD": "cryton",
            "CRYTON_WORKER_EMPIRE_HOST": "127.0.0.1",
            "CRYTON_WORKER_EMPIRE_PORT": 1337,
            "CRYTON_WORKER_EMPIRE_USERNAME": "cryton",
            "CRYTON_WORKER_EMPIRE_PASSWORD": "cryton",
            "CRYTON_WORKER_MAX_RETRIES": 3,
        },
        is_attacker=True,
    ),
]
CONTAINER_DB = [
    DEFAULT,
    ROUTER,
    DNS_SERVER,
    FIREHOLE,
    NodeContainer(
        "registry.gitlab.ics.muni.cz:443/ai-dojo/cif/base_wordpress_firehole",
        services=[ServiceTag("wordpress", "6.1.1")],
        _healthcheck=Healthcheck(
            [
                "CMD-SHELL",
                "curl localhost/wp-admin/install.php | grep WordPress",
            ],
            sec_to_nano(20),
            sec_to_nano(10),
            3,
        ),
        environment={
            "WORDPRESS_DB_HOST": "wordpress_db_node",
            "WORDPRESS_DB_USER": "wordpress",
            "WORDPRESS_DB_PASSWORD": "wordpress",
            "WORDPRESS_ADMIN_NAME": "wordpress",
            "WORDPRESS_ADMIN_PASSWORD": "wordpress",
        },
        requires=[ServiceTag("mysql", "8.0.31")],
    ),
    NodeContainer(
        "registry.gitlab.ics.muni.cz:443/ai-dojo/cif/base_mysql",
        services=[ServiceTag("mysql", "8.0.31")],
        _healthcheck=Healthcheck(
            test=[
                "CMD-SHELL",
                'mysql $MYSQL_DATABASE --user=$MYSQL_USER --password=$MYSQL_PASSWORD --silent --execute "SELECT 1;"',
            ],
            interval=sec_to_nano(20),
            timeout=sec_to_nano(10),
            retries=3,
        ),
        environment={
            "MYSQL_ROOT_PASSWORD": "wordpress",
            "MYSQL_DATABASE": "wordpress",
            "MYSQL_USER": "wordpress",
            "MYSQL_PASSWORD": "wordpress",
        },
    ),
    NodeContainer("registry.gitlab.ics.muni.cz:443/ai-dojo/cif/base_ftp", services=[ServiceTag("vsftpd", "2.3.4")]),
    NodeContainer(
        "registry.gitlab.ics.muni.cz:443/ai-dojo/cif/base_ssh_client-workstation_client-developer",
        services=[ServiceTag("ssh", "5.1.4"), ServiceTag("bash", "8.1.0")],
        environment={},
    ),
    NodeContainer(
        "registry.gitlab.ics.muni.cz:443/ai-dojo/cif/base_client-workstation_client-phished",
        services=[ServiceTag("bash", "8.1.0")],
        environment={},
    ),
    NodeContainer("registry.gitlab.ics.muni.cz:443/ai-dojo/cif/base",
                  services=[ServiceTag("mail", "8.1.0")]),
    NodeContainer("registry.gitlab.ics.muni.cz:443/ai-dojo/cif/base_chat",
                  services=[ServiceTag("chat", "0.1.0")]),
]

SERVICE_PORTS = {
    "mysql": ("MYSQL_PORT", 3306),
    "vsftpd": ("FTP_PORT", 21)
}


async def match_service_container(node_services: list[ServiceTag]) -> list[ServiceContainer | None]:
    """
    Matches a set of node services with a predefined database of containers.
    If the rules aren't satisfied, it returns the default container.
    :param node_services: Set node services to match against the database of containers with services.
    :return: Matched containers
    """
    exact_matches: list[ServiceContainer | None] = []
    partial_matches: list[ServiceContainer | None] = []

    for service_container in SERVICE_CONTAINERS:
        for service_tag in node_services:
            if service_tag == service_container.tag:
                exact_matches.append(service_container)
            if service_tag.type.lower() == service_container.tag.type.lower():
                partial_matches.append(service_container)

    if exact_matches:
        return exact_matches
    elif partial_matches:
        return partial_matches
    else:
        logger.debug("No service container with the required servie tag was found in the SERVICE CONTAINER DATABASE")
        return []


async def match_node_container(node_services: list[ServiceTag]) -> NodeContainer:
    """
    Matches a set of node services with a predefined database of containers.
    If the rules aren't satisfied, it returns the default container.
    :param node_services: Set node services to match against the database of containers with services.
    :return: Matched containers
    """
    closest_match: NodeContainer | None = None
    closest_match_redundant_services: list[ServiceTag] = []

    for db_container in CONTAINER_DB:
        # Check if the required services are all available in the container
        if all(service in db_container.services for service in node_services):
            redundant_db_container_services = [service for service in db_container.services if
                                               service not in node_services]
            if not redundant_db_container_services:  # An exact match
                return db_container

            # If this container has fewer redundant services than the current closest match, update the closest match
            if closest_match is None or len(redundant_db_container_services) < len(closest_match_redundant_services):
                closest_match, closest_match_redundant_services = db_container, redundant_db_container_services

    if closest_match:
        return closest_match
    else:
        logger.error("No container with the required services was found in the CONTAINER DATABASE")
        return DEFAULT
