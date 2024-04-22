from dataclasses import dataclass, field, asdict
from typing import Any

from parser.util import constants


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
    volumes: list[str] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    requires: set[ServiceTag] = field(default_factory=set)
    can_be_combined: bool = False

    @property
    def healthcheck(self) -> dict:
        return asdict(self._healthcheck) if self._healthcheck else dict()


# TODO: unique variables accross infras under a single run
DEFAULT = Container(
    "registry.gitlab.ics.muni.cz:443/ai-dojo/docker-testbed/node:latest", {ServiceTag("bash"), ServiceTag("sh")}
)
ROUTER = Container("registry.gitlab.ics.muni.cz:443/ai-dojo/docker-testbed/router:latest", {ServiceTag("iptables")})
DATABASE = [
    DEFAULT,
    ROUTER,
    Container(
        "registry.gitlab.ics.muni.cz:443/cryton/cryton-worker:kali",
        {ServiceTag("scripted_actor")},
        environment={
            "CRYTON_WORKER_NAME": "attacker",
            "CRYTON_WORKER_DEBUG": True,
            "CRYTON_WORKER_MODULES_DIR": "/app/cryton-modules/modules",
            "CRYTON_WORKER_MSFRPCD_PORT": 55553,
            "CRYTON_WORKER_MSFRPCD_HOST": "localhost",
            "CRYTON_WORKER_MSFRPCD_USERNAME": "cryton",
            "CRYTON_WORKER_MSFRPCD_PASSWORD": "cryton",
            "CRYTON_WORKER_RABBIT_HOST": "cryton-rabbit",
            "CRYTON_WORKER_RABBIT_PORT": 5672,
            "CRYTON_WORKER_RABBIT_USERNAME": "cryton",
            "CRYTON_WORKER_RABBIT_PASSWORD": "cryton",
            "CRYTON_WORKER_EMPIRE_HOST": "localhost",
            "CRYTON_WORKER_EMPIRE_PORT": 1337,
            "CRYTON_WORKER_EMPIRE_USERNAME": "cryton",
            "CRYTON_WORKER_EMPIRE_PASSWORD": "cryton",
            "CRYTON_WORKER_MAX_RETRIES": 20,
        },
        can_be_combined=True,
    ),
    Container(
        "wordpress:6.1.1-apache",
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
            "WORDPRESS_DB_HOST": "wordpress_db.demo",
            "WORDPRESS_DB_USER": "wordpress",
            "WORDPRESS_DB_PASSWORD": "wordpress",
            "WORDPRESS_DB_NAME": "wordpress",
        },
        requires={ServiceTag("mysql", "8.0.31")},
    ),
    Container(
        "mysql:8.0.31",
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
            "MYSQL_ROOT_PASSWORD": "wordpress",
            "MYSQL_DATABASE": "wordpress",
            "MYSQL_USER": "wordpress",
            "MYSQL_PASSWORD": "wordpress",
        },
    ),
    Container(
        "postgres:10.5",
        {ServiceTag("postgres", "10.5.0")},
        environment={
            "POSTGRES_DB": "beastdb",
            "POSTGRES_USER": "dbuser",
            "POSTGRES_PASSWORD": "dbpassword",
        },
        volumes=[
            f"{(constants.resources_path/'create_tables.sql').as_posix()}:/docker-entrypoint-initdb.d/create_tables.sql",
            f"{(constants.resources_path/'fill_tables.sql').as_posix()}:/docker-entrypoint-initdb.d/fill_tables.sql",
        ],
    ),
    Container(
        "registry.gitlab.ics.muni.cz:443/cryton/configurations/metasploit-framework:0",
        {ServiceTag("metasploit", "0.1.0")},
        environment={
            "MSF_RPC_HOST": "localhost",
            "MSF_RPC_PORT": 55553,
            "MSF_RPC_SSL": True,
            "MSF_RPC_USERNAME": "cryton",
            "MSF_RPC_PASSWORD": "cryton",
        },
        can_be_combined=True,
    ),
    Container(
        "bcsecurity/empire:v4.10.0",
        {ServiceTag("empire", "4.10.0")},
        environment={
            "CRYTON_WORKER_EMPIRE_USERNAME": "cryton",
            "CRYTON_WORKER_EMPIRE_PASSWORD": "cryton",
        },
        can_be_combined=True,
    ),
    Container(
        "uexpl0it/vulnerable-packages:backdoored-vsftpd-2.3.4",
        {ServiceTag("vsftpd", "2.3.4")},
        volumes=[f"{(constants.resources_path/'vsftpd.log').as_posix()}:/var/log/vsftpd.log"],
    ),
]

# DATABASE = {
#     Service("jtr", "1.9.0"): Container(constants.IMAGE_NODE),
#     Service("empire", "4.10.0"): Container(constants.IMAGE_NODE),
#     Service("msf", "1.0.0"): Container(constants.IMAGE_NODE),
#     # Service("wordpress_app", "6.1.1"): Container(constants.IMAGE_NODE),
#     # Service("wordpress_db", "8.0.31"): Container(constants.IMAGE_NODE),
#     Service("vsftpd", "2.3.4"): Container(constants.IMAGE_NODE),
#     Service("postgres", "10.5.0"): Container(constants.IMAGE_NODE),
#     Service("haraka", "2.3.4"): Container(constants.IMAGE_NODE),
#     Service("tchat", "2.3.4"): Container(constants.IMAGE_NODE),
#     Service("ssh", "5.1.4"): Container(constants.IMAGE_NODE),
# }


def match(rules: set[ServiceTag]) -> list[Container]:
    """
    Get Containers that match the supplied rules.
    In case the rules aren't satisfied, return default.
    :param rules: Set of rules to match against the Containers.
    :return: Matched Containers
    """
    possible_matches: list[Container] = list()
    possible_matches_services: set[ServiceTag] = set()
    for container in DATABASE:
        if rules.issubset(container.services):
            return [container]
        elif rules.issuperset(container.services) and container.can_be_combined:
            possible_matches.append(container)
            possible_matches_services.update(container.services)
            if rules.issubset(possible_matches_services):
                return possible_matches

    return [DEFAULT]
