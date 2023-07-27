import pathlib

import yaml
from netaddr import IPNetwork

compose_path = (
    pathlib.Path(__file__).absolute().parent.parent.parent / "docker-compose.yml"
).as_posix()


APPLIANCE_TYPE_ROUTER = "router"
APPLIANCE_TYPE_NODE = "node"
APPLIANCE_TYPE_ATTACKER = "attacker"

ROUTER_TYPE_PERIMETER = "perimeter"
ROUTER_TYPE_INTERNAL = "internal"
PERIMETER_ROUTER = "perimeter_router"

NETWORK_TYPE_INTERNAL = "internal"
NETWORK_TYPE_MANAGEMENT = "management"
NETWORK_TYPE_PUBLIC = "public"

IMAGE_DEBUG = "nicolaka/netshoot"
IMAGE_BASE = "alpine"
IMAGE_ROUTER = "router"
IMAGE_NODE = "node"
IMAGE = "image"
COMMAND = "command"
HEALTHCHECK = "healthcheck"
VOLUMES = "volumes"
MOUNTS = "mounts"
ENVIRONMENT = "environment"
SERVICE_HEALTHY = "service_healthy"
SERVICE_STARTED = "service_started"

CRYTON_NETWORK_IP = IPNetwork(
    yaml.load(open(rf"{compose_path}"), Loader=yaml.FullLoader)["networks"]["cryton"][
        "ipam"
    ]["config"][0]["subnet"]
)

CRYTON_NETWORK_NAME = "docker-testbed_cryton"


# For testing until we can work on searching images based on CVEs
IMAGE_LIST = [
    "postgres:13",
    "python:3.9-slim-buster",
    "registry.gitlab.ics.muni.cz:443/cryton/cryton-core:proxy",
    "registry.gitlab.ics.muni.cz:443/cryton/cryton-core:latest",
    "registry.gitlab.ics.muni.cz:443/cryton/cryton-cli:latest",
    "rabbitmq:3.11-management",
    "nicolaka/netshoot:latest",
    "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:vuln-user",
    "wordpress:cli-2.7.1-php8.0",
    "alpine:latest",
    "wordpress:6.1.1-apache",
    "edoburu/pgbouncer:1.18.0",
    "mysql:8.0.31",
    "uexpl0it/vulnerable-packages:backdoored-vsftpd-2.3.4",
    "postgres:10.5",
    "registry.gitlab.ics.muni.cz:443/cryton/cryton-worker:kali",
    "registry.gitlab.ics.muni.cz:443/cryton/configurations/metasploit-framework:0",
    "bcsecurity/empire:v4.10.0",
]

TESTBED_IMAGES = {
    "wordpress_app": "wordpress:6.1.1-apache",
    "wordpress_db": "mysql:8.0.31",
    "vsftpd_service": "uexpl0it/vulnerable-packages:backdoored-vsftpd-2.3.4",
    "psql-service": "postgres:10.5",
    "postgres_node": "alpine:latest",
    "user_node": "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:vuln-user",
    "attacker_node": "registry.gitlab.ics.muni.cz:443/cryton/cryton-worker:kali",
    "msf_service": "registry.gitlab.ics.muni.cz:443/cryton/configurations/metasploit-framework:0",
    "empire_service": "bcsecurity/empire:v4.10.0",
}


resources_path = pathlib.Path(__file__).absolute().parent.parent.parent / "resources"
project_root_path = pathlib.Path(__file__).absolute().parent.parent.parent
compose_path = (
    pathlib.Path(__file__).absolute().parent.parent.parent / "docker-compose.yml"
).as_posix()


WPS_APP_HEALTH_CHECK = {
    "test": ["CMD-SHELL", "curl localhost/wp-admin/install.php | grep WordPress"],
    "interval": 10000000000,
    "timeout": 10000000000,
    "retries": 3,
}

WPS_DB_HEALTH_CHECK = {
    "test": [
        "CMD-SHELL",
        'mysql $MYSQL_DATABASE --user=$MYSQL_USER --password=$MYSQL_PASSWORD --silent --execute "SELECT 1;"',
    ],
    "interval": 3000000000,
    "timeout": 10000000000,
    "retries": 7,
}

envs = {
    "attacker_node": {
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
    "msf_service": {
        "MSF_RPC_HOST": "localhost",
        "MSF_RPC_PORT": 55553,
        "MSF_RPC_SSL": True,
        "MSF_RPC_USERNAME": "cryton",
        "MSF_RPC_PASSWORD": "cryton",
    },
    "empire_service": {
        "CRYTON_WORKER_EMPIRE_USERNAME": "cryton",
        "CRYTON_WORKER_EMPIRE_PASSWORD": "cryton",
    },
    "wordpress_db": {
        "MYSQL_ROOT_PASSWORD": "wordpress",
        "MYSQL_DATABASE": "wordpress",
        "MYSQL_USER": "wordpress",
        "MYSQL_PASSWORD": "wordpress",
    },
    "wordpress_node": {
        "WORDPRESS_DB_HOST": "wordpress_db.demo",
        "WORDPRESS_DB_USER": "wordpress",
        "WORDPRESS_DB_PASSWORD": "wordpress",
        "WORDPRESS_DB_NAME": "wordpress",
    },
    "psql-service": {
        "POSTGRES_DB": "beastdb",
        "POSTGRES_USER": "dbuser",
        "POSTGRES_PASSWORD": "dbpassword",
    },
}

TESTBED_INFO = {
    "wordpress_node": {
        IMAGE: "wordpress:6.1.1-apache",
        COMMAND: None,
        HEALTHCHECK: WPS_APP_HEALTH_CHECK,
        VOLUMES: {"wordpress_app_html": {"bind": "/var/www/html", "mode": "rw"}},
    },
    "wordpress_db": {
        IMAGE: "mysql:8.0.31",
        COMMAND: None,
        HEALTHCHECK: WPS_DB_HEALTH_CHECK,
    },
    "vsftpd_node": {
        IMAGE: "uexpl0it/vulnerable-packages:backdoored-vsftpd-2.3.4",
        COMMAND: None,
        VOLUMES: [f"{(resources_path/'vsftpd.log').as_posix()}:/var/log/vsftpd.log"],
    },
    "psql-service": {
        IMAGE: "postgres:10.5",
        COMMAND: None,
        VOLUMES: [
            f"{(resources_path/'create_tables.sql').as_posix()}:/docker-entrypoint-initdb.d/create_tables.sql",
            f"{(resources_path/'fill_tables.sql').as_posix()}:/docker-entrypoint-initdb.d/fill_tables.sql",
        ],
    },
    "postgres_node": {
        IMAGE: "alpine:latest",
        COMMAND: "sleep infinity",
    },
    "user_node": {
        IMAGE: "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:vuln-user",
        COMMAND: ["sh", "-c", "service ssh start && tail -f /dev/null"],
    },
    "attacker_node": {
        IMAGE: "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:attacker-node-demo",
        COMMAND: None,
        VOLUMES: [
            f"{(resources_path/'pass_list.txt').as_posix()}:/app/resources/pass_list.txt",
            f"{(resources_path/'user_list.txt').as_posix()}:/app/resources/user_list.txt",
        ],
    },
    "msf_service": {
        IMAGE: "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:attacker-node-demo",
        COMMAND: None,
        VOLUMES: [
            f"{(resources_path / 'pass_list.txt').as_posix()}:/app/resources/pass_list.txt",
            f"{(resources_path / 'user_list.txt').as_posix()}:/app/resources/user_list.txt",
        ],
    },
    "empire_service": {
        IMAGE: "registry.gitlab.ics.muni.cz:443/cryton/beast-demo:attacker-node-demo",
        COMMAND: [
            "server",
            "--username",
            "$CRYTON_WORKER_EMPIRE_USERNAME",
            "--password",
            "$CRYTON_WORKER_EMPIRE_PASSWORD",
        ],
        VOLUMES: [
            f"{(resources_path / 'pass_list.txt').as_posix()}:/app/resources/pass_list.txt",
            f"{(resources_path / 'user_list.txt').as_posix()}:/app/resources/user_list.txt",
        ],
    },
}
