from dataclasses import dataclass, field, asdict
from typing import Any
from dr_emu.lib.logger import logger


def sec_to_nano(seconds: int) -> int:
    """
    Convert seconds to nanoseconds.
    :param seconds: Number of seconds
    :return: Number of nanoseconds
    """
    return seconds * 10**9


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

    name: str
    version: str = ""


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
    services: set[ServiceTag]
    description: str = ""
    entrypoint: list[str] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    _healthcheck: Healthcheck | None = None
    volumes: list[Volume] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    requires: set[ServiceTag] = field(default_factory=set)
    can_be_combined: bool = False
    is_attacker: bool = False
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def healthcheck(self) -> dict:
        return asdict(self._healthcheck) if self._healthcheck else dict()


# TODO: unique variables accross infras under a single run
DEFAULT = Container(
    "registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/node:latest", {ServiceTag("bash"), ServiceTag("sh")}
)
ROUTER = Container("registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/router:latest", {ServiceTag("iptables")})
DNS_SERVER = Container(
    "registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/node:latest",
    {ServiceTag("bash"), ServiceTag("sh"), ServiceTag("coredns", "1.11.1")},
    volumes=[Volume("core-dns", "/etc/coredns")],
)

DATABASE = [
    DEFAULT,
    ROUTER,
    DNS_SERVER,
    Container(
        "registry.gitlab.ics.muni.cz:443/cryton/cryton/worker:latest",
        {ServiceTag("scripted_actor")},
        environment={
            "CRYTON_WORKER_NAME": "attacker",
            "CRYTON_WORKER_DEBUG": True,
            "CRYTON_WORKER_METASPLOIT_PORT": 55553,
            "CRYTON_WORKER_METASPLOIT_HOST": "127.0.0.1",
            "CRYTON_WORKER_METASPLOIT_USERNAME": "cryton",
            "CRYTON_WORKER_METASPLOIT_PASSWORD": "cryton",
            "CRYTON_WORKER_METASPLOIT_SSL": True,
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
        can_be_combined=True,
        is_attacker=True,
    ),
    Container(
        "registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/web-server:latest",
        {ServiceTag("wordpress", "6.1.1")},
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
            "WORDPRESS_DB_USER": "cdri",
            "WORDPRESS_DB_PASSWORD": "cdri",
            "WORDPRESS_DB_NAME": "cdri",
            "WP_HOSTNAME": "wordpress_node",
            "WP_ADMIN_NAME": "wordpress",
            "WP_ADMIN_PASSWORD": "wordpress",
        },
        requires={ServiceTag("mysql", "8.0.31")},
    ),
    Container(
        "registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/database-server:latest",
        {ServiceTag("mysql", "8.0.31")},
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
            "MYSQL_ROOT_PASSWORD": "cdri",
            "MYSQL_DATABASE": "cdri",
            "MYSQL_USER": "cdri",
            "MYSQL_PASSWORD": "cdri",
        },
    ),
    Container(
        "sadparad1se/metasploit-framework:rpc",
        {ServiceTag("metasploit", "0.1.0")},
        environment={
            "METASPLOIT_RPC_USERNAME": "cryton",
            "METASPLOIT_RPC_PASSWORD": "cryton",
        },
        can_be_combined=True,
    ),
    Container(
        "bcsecurity/empire:v4.10.0",
        {ServiceTag("empire", "4.10.0")},
        command=["server", "--username", "cryton", "--password", "cryton"],
        can_be_combined=True,
    ),
    Container("registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/ftp-server:latest", {ServiceTag("vsftpd", "2.3.4")}),
    Container(
        "coredns/coredns",
        {ServiceTag("coredns", "1.11.1")},
        volumes=[Volume("core-dns", "/etc/coredns")],
        command=["-conf", "/etc/coredns/Corefile"],
        kwargs={"restart_policy": {"Name": "on-failure"}},
    ),
    Container(
        "registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/workstation:developer",
        {ServiceTag("ssh", "5.1.4"), ServiceTag("bash", "8.1.0")},
        environment={"CRYTON_WORKER_RABBIT_HOST": "cryton-rabbit", "CRYTON_WORKER_NAME": "developer"},
    ),
    Container(
        "registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/workstation:phished",
        {ServiceTag("bash", "8.1.0")},
        # TODO: worker name should be unique
        environment={"CRYTON_WORKER_RABBIT_HOST": "cryton-rabbit", "CRYTON_WORKER_NAME": "client"},
    ),
    Container("registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/mail-server:latest", {ServiceTag("mail", "8.1.0")}),
    Container("registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/chat-server:latest", {ServiceTag("chat", "0.1.0")}),
]


def match_container(node_services: set[ServiceTag]) -> list[Container]:
    """
    Matches a set of node services with a predefined database of containers.
    If the rules aren't satisfied, it returns the default container.
    :param node_services: Set node services to match against the database of containers with services.
    :return: Matched containers
    """
    closest_match: Container | None = None
    closest_match_redundant_services: set[ServiceTag] = set()
    partial_matches: list[Container] = list()
    partial_matches_services: set[ServiceTag] = set()

    for db_container in DATABASE:
        # Check if the required services are all available in the container
        if not node_services.difference(db_container.services):
            redundant_db_container_services = db_container.services.difference(node_services)
            if not redundant_db_container_services:  # An exact match
                return [db_container]

            # If this container has fewer redundant services than the current closest match, update the closest match
            if closest_match is None or redundant_db_container_services < closest_match_redundant_services:
                closest_match, closest_match_redundant_services = db_container, redundant_db_container_services

        # Check if at least one of the required services is in the container
        if (
            db_container.can_be_combined
            and node_services.difference(db_container.services) < node_services
            and db_container.services.difference(partial_matches_services)
        ):
            partial_matches.append(db_container)
            partial_matches_services.update(db_container.services)

    # If the partial matches match the requirements, use them
    if not node_services.difference(partial_matches_services):
        return partial_matches

    if closest_match:
        return [closest_match]
    else:
        logger.error("No container with the required services was found in the CONTAINER DATABASE, using default.")
        return [DEFAULT]
