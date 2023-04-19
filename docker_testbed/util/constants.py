from netaddr import IPAddress, IPNetwork

PERIMETER_ROUTER = "perimeter_router"
MANAGEMENT_NETWORK_SUBNET = IPNetwork("192.168.50.0/24")
MANAGEMENT_NETWORK_ROUTER_GATEWAY = IPAddress(MANAGEMENT_NETWORK_SUBNET.first + 1, MANAGEMENT_NETWORK_SUBNET.version)

MANAGEMENT_NETWORK_NAME = "management_network"

IMAGE_BASE = "base"
IMAGE_NODE = "node"
IMAGE_ROUTER = "router"
ROUTER_IMAGE_DEBUG = "nicolaka/netshoot"
