import pathlib
import yaml
from netaddr import IPNetwork

project_root_path = pathlib.Path(__file__).absolute().parent.parent.parent
resources_path = project_root_path / "resources"
compose_path = (project_root_path / "docker-compose.yml").as_posix()

ROUTER_TYPE_PERIMETER = "perimeter"
ROUTER_TYPE_INTERNAL = "internal"
PERIMETER_ROUTER = "perimeter_router"

NETWORK_TYPE_INTERNAL = "internal"
NETWORK_TYPE_MANAGEMENT = "management"
NETWORK_TYPE_PUBLIC = "public"

DEPENDS_ON = "depends_on"
SERVICE_HEALTHY = "service_healthy"
SERVICE_STARTED = "service_started"

FIREWALL_ALLOW = "ALLOW"
FIREWALL_DENY = "DENY"

CRYTON_NETWORK_IP = IPNetwork(
    yaml.load(open(rf"{compose_path}"), Loader=yaml.FullLoader)["networks"]["cryton"]["ipam"]["config"][0]["subnet"]
)

CRYTON_NETWORK_NAME = "docker-testbed_cryton"
