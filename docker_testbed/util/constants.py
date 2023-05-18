from netaddr import IPAddress, IPNetwork

PERIMETER_ROUTER = "perimeter_router"
MANAGEMENT_NETWORK_SUBNET = IPNetwork("192.168.50.0/24")
MANAGEMENT_NETWORK_ROUTER_GATEWAY = IPAddress(
    MANAGEMENT_NETWORK_SUBNET.first + 1, MANAGEMENT_NETWORK_SUBNET.version
)
MANAGEMENT_NETWORK_NAME = "management_network"

IMAGE_DEBUG = "nicolaka/netshoot"
IMAGE_BASE = "alpine"
IMAGE_ROUTER = "router"
IMAGE_NODE = "node"
IMAGE = "image"

# For testing until we can work on searching images based on CVEs
IMAGE_LIST = [
    "postgres:13",
    "python:3.9-slim-buster",
    "registry.gitlab.ics.muni.cz:443/cryton/cryton-core:proxy",
    "registry.gitlab.ics.muni.cz:443/cryton/cryton-core:latest",
    "registry.gitlab.ics.muni.cz:443/cryton/cryton-cli:latest",
    "rabbitmq:3.11-management",
    "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:attacker-node",
    "nicolaka/netshoot:latest",
    "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:vuln-user",
    "wordpress:cli-2.7.1-php8.0",
    "alpine:latest",
    "wordpress:6.1.1-apache",
    "edoburu/pgbouncer:1.18.0",
    "mysql:8.0.31",
    "uexpl0it/vulnerable-packages:backdoored-vsftpd-2.3.4",
    "postgres:10.5",
]

TESTBED_IMAGES = {
    "wordpress_app": "wordpress:6.1.1-apache",
    "wordpress_db": "mysql:8.0.31",
    "vsftpd_service": "uexpl0it/vulnerable-packages:backdoored-vsftpd-2.3.4",
    "psql-service": "postgres:10.5",
    "postgres_node": "alpine:latest",
    "user_node": "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:vuln-user",
    "attacker_node": "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:attacker-node",
}
