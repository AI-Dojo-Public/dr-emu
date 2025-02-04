from argparse import ArgumentParser
import docker

from dr_emu.lib.logger import logger

from test_infrastructure import all_config_items, wordpress_srv, developer, wifi_client
from shared.endpoints import Run, Template
from parser.cyst_parser import CYSTParser
from rich import print
import asyncio
import deployment_script
import httpx


async def get_infrastructure(run_id):
    run = httpx.get(f"http://127.0.0.1:8000/runs/get/{run_id}/").json()
    return httpx.get(f"http://127.0.0.1:8000/infrastructures/get/{run['infrastructure_ids'][0]}/").json()


async def get_infra_info(infrastructure_info: dict, parser: CYSTParser):
    appliance_ips = {}
    appliance_names = {}

    for network in infrastructure_info["networks"]:
        for appliance in network["appliances"]:
            if (original_ip := appliance["original_ip"]) is not None:
                appliance_ips[original_ip] = appliance["ip"]
                for node in parser.nodes:
                    if node.name in appliance["name"]:
                        appliance_names[node.name] = appliance['name']

    return appliance_ips, appliance_names


async def get_docker_networks(infrastructure):
    """
    Get docker networks belonging to the dr-emu infrastructure
    :return: list of docker Networks objects
    """
    docker_client = docker.from_env()
    docker_networks = {}

    for network in infrastructure["networks"]:
        if (docker_network := docker_client.networks.get(network["name"]).attrs) is not None:
            docker_network_ip = docker_network["IPAM"]["Config"][0]["Subnet"]
            docker_networks[docker_network_ip] = {}
            for container_id, container_info in docker_network["Containers"].items():
                docker_networks[docker_network_ip][container_info["Name"]] = container_info["IPv4Address"].split("/")[0]
        else:
            logger.error(
                "Network from infra not deployed by docker", network_name=network["name"], network_ip=network["ip"]
            )

    return docker_networks


async def check_running_status(appliance_names: dict):
    result = True
    logger.info("Checking container running statuses")
    docker_client = docker.from_env()
    for original_name, docker_name in appliance_names.items():
        if docker_client.containers.get(docker_name).status != "running":
            logger.error("Infrastructure Appliance is not running", name=docker_name)
            result = False

    return result

async def install_ping(docker_container: docker.models.containers.Container):
    docker_container.exec_run(f"apt-get update -y")
    docker_container.exec_run(f"apt-get install -y iputils-ping")

async def check_network_connections_and_firewall(appliance_ips: dict, appliance_names: dict):
    """
    Checking network connections and correct firewall rules using pings between nodes.
    Ip addresses of nodes are static and pulled from test_infrastructure interfaces.
    :return:
    """
    result = True
    logger.info("Checking network connections and firewall")
    docker_client = docker.from_env()

    wifi_client_container = docker_client.containers.get(appliance_names[wifi_client.id])
    wordpress_container = docker_client.containers.get(appliance_names[wordpress_srv.id])
    developer_container = docker_client.containers.get(appliance_names[developer.id])

    async with asyncio.TaskGroup() as tg:
        for container in [wifi_client_container, wordpress_container, developer_container]:
            tg.create_task(install_ping(container))

    wifi_client_pings = [
        wifi_client_container.exec_run(f"ping -c 2 {appliance_ips[str(wordpress_srv.interfaces[0].ip)]}"),
        wifi_client_container.exec_run(f"ping -c 2 {appliance_ips[str(developer.interfaces[0].ip)]}"),
    ]
    for ping in wifi_client_pings:
        if ping.exit_code != 1 and "0 packets received, 100% packet loss" not in ping.output.decode("utf-8"):
            logger.error(f"Wrong firewall rules for network with {wifi_client_container.name}")
            result = False

    wordpress_pings = [
        wordpress_container.exec_run(f"ping -c 2 {appliance_ips[str(wifi_client.interfaces[0].ip)]}"),
        wordpress_container.exec_run(f"ping -c 2 {appliance_ips[str(developer.interfaces[0].ip)]}"),
    ]
    for ping in wordpress_pings:
        if ping.exit_code != 0 and "2 packets received, 0% packet loss" not in ping.output.decode("utf-8"):
            logger.error(f"Wrong firewall rules for network with {wordpress_container.name}")
            result = False

    developer_pings = [
        developer_container.exec_run(f"ping -c 2 {appliance_ips[str(wordpress_srv.interfaces[0].ip)]}"),
        developer_container.exec_run(f"ping -c 2 {appliance_ips[str(wifi_client.interfaces[0].ip)]}"),
    ]
    for ping in developer_pings:
        if ping.exit_code != 0 and "2 packets received, 0% packet loss" not in ping.output.decode("utf-8"):
            logger.error(f"Wrong firewall rules for network with {developer_container.name}")
            result = False
    return result


async def clean_up(run_id):
    logger.info("Cleaning up testing infrastructure")

    url = "http://127.0.0.1:8000"
    run = httpx.get(f"{url}{Run.get.format(run_id)}").json()
    httpx.post(f"{url}{Run.stop.format(run_id)}", timeout=300)
    httpx.delete(f"{url}{Run.delete.format(run_id)}")
    httpx.delete(f"{url}{Template.delete.format(run['template_id'])}")

    logger.info("Clean up complete")


async def check_deployment(run_id):
    config = deployment_script.create_configuration(all_config_items)
    parser = CYSTParser(config)
    await parser.parse()

    infrastructure_info = await get_infrastructure(run_id)
    docker_infrastructure = await get_docker_networks(infrastructure_info)
    appliance_ips, appliance_names = await get_infra_info(infrastructure_info, parser)
    running_status_check = await check_running_status(appliance_names)
    fw_connections_check = await check_network_connections_and_firewall(appliance_ips, appliance_names)

    if docker_infrastructure and running_status_check and fw_connections_check:
        return True
    return False


async def main():
    parser = ArgumentParser(
        prog="dr-emu e2e tests",
        description="Tests the correctness of the testing infrastructure deployment (ip addresses, firewall and "
        "network configurations, running containers)",
    )
    parser.add_argument("token")

    run_id = await deployment_script.main(all_config_items)
    if await check_deployment(run_id):
        print("\n[bold green]All tests passed.[/bold green]\n")
    else:
        print("\n[bold red]Some tests failed, check the error logs.[/bold red]\n")
    await clean_up(run_id)


asyncio.run(main())
