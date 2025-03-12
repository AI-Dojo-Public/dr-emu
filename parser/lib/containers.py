from frozendict import frozendict
from parser.lib.simple_models import Node, ServiceContainer, Volume, NodeType, Service, Image


def sec_to_nano(seconds: int) -> int:
    """
    Convert seconds to nanoseconds.
    :param seconds: Number of seconds
    :return: Number of nanoseconds
    """
    return seconds * 10 ** 9


SSH = Service(type="ssh", variable_override=frozendict(SSH_PORT=22, SSH_HOST="0.0.0.0"))
FTP = Service(type="vsftpd", version="2.3.4", variable_override=frozendict(VSFTPD_PORT=21, VSFTPD_HOST="0.0.0.0"))
MYSQL = Service(type="mysql", version="8.0.31", variable_override=frozendict(MYSQL_PORT=3306, MYSQL_HOST="0.0.0.0"))
SAMBA = Service(type="samba", version="3.5.2", variable_override=frozendict(SAMBA_HOST="0.0.0.0"))
WORDPRESS = Service(type="wordpress",
                    version="6.1.1",
                    variable_override=frozendict(
                        WORDPRESS_PORT=80,
                        WORDPRESS_HOSTNAME="0.0.0.0",
                        WORDPRESS_ADMIN_NAME="wordpress",
                        WORDPRESS_ADMIN_PASSWORD="wordpress",
                        WORDPRESS_DB_USER="wordpress",
                        WORDPRESS_DB_PASSWORD="wordpress",
                        WORDPRESS_DB_HOST="node_wordpress_database",
                        WORDPRESS_DEBUG="false",
                        WORDPRESS_CERTIFICATE="/",
                        WORDPRESS_PRIVATE_KEY="/",
                        WORDPRESS_HOST="0.0.0.0",
                        WORDPRESS_TITLE="Placeholder")
                    )
METASPLOIT = Service(type="metasploit", version="0.1.0")
COREDNS = Service(type="coredns", version="1.11.1")
EMPIRE = Service(type="empire", version="4.10.0")
FIREHOLE = Service(type="firehole")
ATTACKER = Service(type="scripted_actor")

IMAGE_DEFAULT = Image(name="cif_base")
DNS_VOLUMES = [Volume("core-dns", "/etc/coredns")]

METASPLOIT_CONTAINER = ServiceContainer(
    Image(name="sadparad1se/metasploit-framework:rpc", services=(METASPLOIT,), pull=True),
    tag=METASPLOIT,
    environment={
        "METASPLOIT_RPC_USERNAME": "cryton",
        "METASPLOIT_RPC_PASSWORD": "cryton",
    },
    can_be_combined=True,
)
EMPIRE_CONTAINER = ServiceContainer(
    Image(name="bcsecurity/empire:v4.10.0", services=(EMPIRE,), pull=True),
    tag=EMPIRE,
    command=["server", "--username", "cryton", "--password", "cryton"],
    can_be_combined=True,
)
COREDNS_CONTAINER = ServiceContainer(
    Image(name="coredns/coredns", services=(COREDNS,), pull=True),
    tag=COREDNS,
    volumes=[Volume("core-dns", "/etc/coredns")],
    command=["-conf", "/etc/coredns/Corefile"],
    kwargs={"restart_policy": {"Name": "on-failure"}},
)
ATTACKER_CONTAINER = ServiceContainer(
    Image(name="registry.gitlab.ics.muni.cz:443/cryton/cryton/worker:3", services=(ATTACKER,), pull=True),
    tag=ATTACKER,
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
)

ATTACKER_NODE = Node(image=IMAGE_DEFAULT, name="node_attacker", service_containers=[ATTACKER_CONTAINER, METASPLOIT_CONTAINER],
                     is_attacker=True, type=NodeType.ATTACKER)
DNS_NODE = Node(image=IMAGE_DEFAULT, name="node_dns", service_containers=[COREDNS_CONTAINER], volumes=DNS_VOLUMES,
                type=NodeType.DNS)

NODES = {
    "node_attacker": ATTACKER_NODE,
    "node_dns": DNS_NODE,
}

SERVICES = {
    "ssh": SSH,
    "vsftpd": FTP,
    "samba": SAMBA,
    "mysql": MYSQL,
    "wordpress": WORDPRESS,
    "coredns": COREDNS,
    "attacker": ATTACKER
}

# async def match_service_container(node_services: set[Service]) -> list[ServiceContainer]:
#     """
#     Matches a set of node services with a predefined database of containers.
#     If the rules aren't satisfied, it returns the default container.
#     :param node_services: Set node services to match against the database of containers with services.
#     :return: Matched containers
#     """
#     exact_matches: list[ServiceContainer] = []
#     partial_matches: list[ServiceContainer] = []
#
#     for service_container in SERVICE_CONTAINERS:
#         for service_tag in node_services:
#             if service_tag == service_container.tag:
#                 exact_matches.append(service_container)
#             if service_tag.type.lower() == service_container.tag.type.lower():
#                 partial_matches.append(service_container)
#
#     if exact_matches:
#         return exact_matches
#     elif partial_matches:
#         return partial_matches
#     else:
#         logger.debug("No service container with the required servie tag was found in the SERVICE CONTAINER DATABASE")
#         return []


# async def match_node_container(node_services: list[Service]) -> Node:
#     """
#     Matches a set of node services with a predefined database of containers.
#     If the rules aren't satisfied, it returns the default container.
#     :param node_services: Set node services to match against the database of containers with services.
#     :return: Matched containers
#     """
#     closest_match: Node | None = None
#     closest_match_redundant_services: list[Service] = []
#
#     for db_container in CONTAINER_DB:
#         # Check if the required services are all available in the container
#         if all(service in db_container.services for service in node_services):
#             redundant_db_container_services = [service for service in db_container.services if
#                                                service not in node_services]
#             if not redundant_db_container_services:  # An exact match
#                 return db_container
#
#             # If this container has fewer redundant services than the current closest match, update the closest match
#             if closest_match is None or len(redundant_db_container_services) < len(closest_match_redundant_services):
#                 closest_match, closest_match_redundant_services = db_container, redundant_db_container_services
#
#     if closest_match:
#         return closest_match
#     else:
#         logger.error("No container with the required services was found in the CONTAINER DATABASE")
#         return DEFAULT
