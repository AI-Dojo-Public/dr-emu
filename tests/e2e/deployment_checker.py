from argparse import ArgumentParser
import docker
import httpx

from dr_emu.lib.logger import logger

from test_infrastructure import all_config_items, wordpress_srv, developer, wifi_client
from shared.endpoints import Infrastructure, Run, Template, Agent
from parser.cyst_parser import CYSTParser
from rich import print
import asyncio
import deployment_script


async def get_infra_info(parser: CYSTParser):
    networks = {}
    for network in parser.networks:
        networks[str(network.ip_address)] = {}

    for appliance in [*parser.routers, *parser.nodes]:
        for interface in appliance.interfaces:
            networks[str(interface.network.ip_address)][appliance.name] = str(interface.ip_address)

    return networks


async def get_docker_networks(run_id):
    """
    Get docker networks belonging to the dr-emu infrastructure
    :param run_id:
    :return: list of docker Networks objects
    """
    docker_client = docker.from_env()
    docker_networks = {}
    infrastructure = await get_infrastructure(run_id)

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


async def get_infrastructure(run_id):
    run = httpx.get(f"http://127.0.0.1:8000/runs/get/{run_id}/").json()
    return httpx.get(f"http://127.0.0.1:8000/infrastructures/get/{run['infrastructure_ids'][0]}/").json()


async def check_correct_ipaddresses(infra_networks, docker_networks):
    result = True
    logger.info("Checking correct ip addresses of networks and nodes")

    for infra_network_ip, infra_network_containers in infra_networks.items():
        if (docker_network := docker_networks.get(infra_network_ip)) is not None:
            for container_name, container_ip in infra_network_containers.items():
                if (docker_container_ip := docker_network.get(container_name)) is not None:
                    if container_ip != docker_container_ip:
                        logger.error(
                            f"Wrong appliance IP",
                            expected_ip=container_ip,
                            actual_ip=docker_container_ip,
                            appliance_name=container_name,
                        )
                        result = False
                else:
                    logger.error(
                        "Infra appliance not deployed by docker",
                        appliance_name=container_name,
                        appliance_ip=container_ip,
                    )
                    result = False

        else:
            logger.error(
                "Network from infrastructure config not present in docker",
                network_name=docker_network.name,
                expected_ip=infra_network_ip,
            )
            result = False

    return result


async def check_running_status(parser: CYSTParser):
    result = True
    logger.info("Checking container running statuses")
    docker_client = docker.from_env()
    for appliance in [*parser.nodes, *parser.routers]:
        if docker_client.containers.get(appliance.name).status != "running":
            logger.error("Infrastructure Appliance is not running", name=appliance.name)
            result = False

    return result


async def check_network_connections_and_firewall():
    """
    Checking network connections and correct firewall rules using pings between nodes.
    Ip addresses of nodes are static and pulled from test_infrastructure interfaces.
    :return:
    """
    result = True
    logger.info("Checking network connections and firewall")
    docker_client = docker.from_env()

    wifi_client_container = docker_client.containers.get(wifi_client.id)
    wifi_client_pings = [
        wifi_client_container.exec_run(f"ping -c 2 {wordpress_srv.interfaces[0].ip}"),
        wifi_client_container.exec_run(f"ping -c 2 {developer.interfaces[0].ip}"),
    ]
    for ping in wifi_client_pings:
        if ping.exit_code != 1 and "0 packets received, 100% packet loss" not in ping.output.decode("utf-8"):
            logger.error(f"Wrong firewall rules for network with {wifi_client_container.name}")
            result = False

    wordpress_container = docker_client.containers.get(wordpress_srv.id)
    wordpress_pings = [
        wordpress_container.exec_run(f"ping -c 2 {wifi_client.interfaces[0].ip}"),
        wordpress_container.exec_run(f"ping -c 2 {developer.interfaces[0].ip}"),
    ]
    for ping in wordpress_pings:
        if ping.exit_code != 0 and "2 packets received, 0% packet loss" not in ping.output.decode("utf-8"):
            logger.error(f"Wrong firewall rules for network with {wordpress_container.name}")
            result = False

    developer_container = docker_client.containers.get(developer.id)
    developer_pings = [
        developer_container.exec_run(f"ping -c 2 {wordpress_srv.interfaces[0].ip}"),
        developer_container.exec_run(f"ping -c 2 {wifi_client.interfaces[0].ip}"),
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
    for agent_id in run["agent_ids"]:
        httpx.delete(f"{url}{Agent.delete.format(agent_id)}")
    httpx.delete(f"{url}{Template.delete.format(run['template_id'])}")

    logger.info("Clean up complete")


async def check_deployment(run_id):
    config = deployment_script.create_configuration(all_config_items)
    parser = CYSTParser(config)
    await parser.parse()

    docker_infrastructure = await get_docker_networks(run_id)
    config_infrastructure = await get_infra_info(parser)
    ipaddress_check = await check_correct_ipaddresses(config_infrastructure, docker_infrastructure)
    running_status_check = await check_running_status(parser)

    if ipaddress_check:
        fw_connections_check = await check_network_connections_and_firewall()

        if running_status_check == fw_connections_check is True:
            return True

    return False


async def main():
    parser = ArgumentParser(
        prog="dr-emu e2e tests",
        description="Tests the correctness of the testing infrastructure deployment (ip addresses, firewall and "
        "network configurations, running containers)",
    )
    parser.add_argument("token")
    ai_agent_token = parser.parse_args().token

    run_id = deployment_script.main(all_config_items, ai_agent_token)
    if await check_deployment(run_id):
        print("\n[bold green]All tests passed.[/bold green]\n")
    else:
        print("\n[bold red]Some tests failed, check the error logs.[/bold red]\n")
    await clean_up(run_id)


asyncio.run(main())
