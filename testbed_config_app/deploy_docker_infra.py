from cyst_infrastructure_parser import nodes, networks, routers
from util import constants
from classes import ContainerConfig, RouterContainerConfig, NodeContainerConfig, NetworkConfig

node_img = "python:3.9-slim-buster"
router_img = "nicolaka/netshoot"

try:
    for network in networks.values():
        network.create_network()

    for router in routers.values():
        router.create_container()
        router.connect_router_to_networks(networks)
        router.container.start()
        router.configure_router(routers)

    for node in nodes.values():
        node.create_container()

    for network in networks.values():
        network.connect_node_containers()

    for node in nodes.values():
        node.container.start()
        node.configure_container()

except Exception:
    for container in [*nodes.values(), *routers.values()]:
        container.cotaniner.kill()
        container.cotaniner.remove()

    for network in networks.values():
        network.network.remove()




# "docker kill $(docker ps -q) && docker rm $(docker ps -a -q)"


