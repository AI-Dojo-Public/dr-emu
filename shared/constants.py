import pathlib

project_root_path = pathlib.Path(__file__).absolute().parent.parent.parent
resources_path = project_root_path / "resources"

TEMPLATE = "Template"
RUN = "Run"
INFRASTRUCTURE = "Infrastructure"

# Router types
ROUTER_TYPE_PERIMETER = "perimeter"
ROUTER_TYPE_INTERNAL = "internal"
PERIMETER_ROUTER = "perimeter_router"

# Network types
NETWORK_TYPE_INTERNAL = "internal"
NETWORK_TYPE_MANAGEMENT = "management"
NETWORK_TYPE_PUBLIC = "public"

# Docker compose features
DEPENDS_ON = "depends_on"
SERVICE_HEALTHY = "service_healthy"
SERVICE_STARTED = "service_started"

# Firewall rules
FIREWALL_ALLOW = "ALLOW"
FIREWALL_DENY = "DENY"
