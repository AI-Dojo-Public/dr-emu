from cyst_infrastructure_parser import nodes, networks, routers
from ipaddress import IPv4Address
from classes import NodeContainerConfig
import docker
import yaml

client = docker.from_env()
beast_envs = yaml.load(open(r'util/docker_envs.yml'), Loader=yaml.FullLoader)
beast_services = yaml.load(open(r'../docker-compose.yml'), Loader=yaml.FullLoader)["services"]
cryton_services = ["cryton_db", "cryton_pgbouncer", "cryton_rabbit", "cryton_core", "cryton_cli", "cryton_proxy"]


def build_cryton():
    cryton_network = client.networks.get("cryton")
    for service in cryton_services:
        cryton_service = beast_services[service]
        current_container = client.containers.create(
            cryton_service["image"],
            name=cryton_service["container_name"],
            environment=beast_envs.get(service),
            network_mode=cryton_service.get("network_mode"),
            restart_policy={"Name": "always"},
            stdin_open=cryton_service.get("stdin_open"),
            tty=cryton_service.get("tty")
        )
        if cryton_service.get("network_mode") is None:
            client.networks.get("bridge").disconnect(current_container)
            cryton_network.connect(current_container, ipv4_address=cryton_service["networks"]["cryton"]["ipv4_address"])
        # else:
        #     cryton_network.connect(current_container)
        current_container.start()


def destroy_cryton():
    for service in cryton_services:
        try:
            container = client.containers.get(beast_services[service]["container_name"])
        except Exception:
            continue
        if container.status == "running":
            container.kill()
        if container.status == "restarting":
            container.stop()
        print(f"removing {service}")
        container.remove()


def build_infra():
    wordpress_db = NodeContainerConfig("wordpress_db", IPv4Address("192.168.93.11"), IPv4Address("192.168.93.1"),
                                       image="mysql:8.0.31", envs=beast_envs["wordpress_db"])
    nodes[wordpress_db.name] = wordpress_db

    for network in networks.values():
        network.create_network()

    for router in routers.values():
        router.create_container()
        router.connect_router_to_networks(networks)
        router.container.start()
        router.configure_router(routers)

    for node in nodes.values():
        if node.name in beast_envs:
            node.create_container(environment=beast_envs[node.name])
        else:
            node.create_container()

    for network in networks.values():
        network.connect_node_containers()

    for node in nodes.values():
        node.container.start()
        node.configure_container()

        # TODO: Fix wordpress deploy b'Error: This does not seem to be a WordPress installation.\nPass --path=`path/to/wordpress` or run `wp core download`
    #     client.containers.run(
    #         "wordpress:cli-2.7.1-php8.0",
    #         ["sh", "-c", 'wp core install --url="http://192.168.93.10" --title="wordpress" --admin_name=wordpress --admin_password="wordpress" --admin_email=wordpress@wordpress.wordpress'],
    #         network_mode="container:wordpress_node"
    #     )

    build_cryton()


def destroy_infra():
    for container in [*nodes.values(), *routers.values()]:
        if container.container.status == "running":
            container.container.kill()
        print(f"removing {container.name}")
        container.container.remove()

    destroy_cryton()

    for network in networks.values():
        network.network.remove()


def start():
    build_infra()
    print("\n\nWrite following commands for:\n"
          "Destroy infra - 'end'\n"
          "Restart infra - 'restart'\n"
          "Leave running - 'ok'")

    user_input = input("input here: ")
    if user_input == "end":
        destroy_infra()
    if user_input == "restart":
        destroy_infra()
        build_infra()
    if user_input == "ok":
        pass


start()
