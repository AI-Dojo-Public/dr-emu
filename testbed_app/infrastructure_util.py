import asyncio
from typing import Union

import randomname

from sqlalchemy.orm import joinedload

from docker_testbed.util import util, constants
from testbed_app.database import session_factory

from testbed_app.models import Infrastructure, Network, Interface
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
import docker

from docker_testbed.cyst_parser import CYSTParser
from docker_testbed.controller import Controller

from cyst_infrastructure import nodes as cyst_nodes, routers as cyst_routers


async def build_infras(number_of_infrastructures: int):
    """
    responses:
      200:
        description: Builds docker infrastructure
    """

    docker_client = docker.from_env()
    controller_start_tasks = set()
    available_networks = []
    docker_container_names = await util.get_container_names(docker_client)
    docker_network_names = await util.get_network_names(docker_client)
    await util.pull_images(docker_client, images=set(constants.IMAGE_LIST))

    for i in range(int(number_of_infrastructures)):
        # need to parse infra at every iteration due to python reference holding and because sqlalchemy models cannot be
        # deep copied
        parser = CYSTParser(docker_client)
        await parser.parse(cyst_routers, cyst_nodes)
        if not available_networks:
            available_networks += await util.get_available_networks(
                docker_client, parser.networks, number_of_infrastructures
            )
        # TODO: Move checking of used ips/names into the parser?
        # get the correct amount of networks for infra from available network list
        slice_start = 0 if i == 0 else (len(parser.networks) + 1) * i
        slice_end = slice_start + len(parser.networks) + 1

        async with session_factory() as sesssion:
            infra_names = (await sesssion.scalars(select(Infrastructure.name))).all()

        while (infra_name := randomname.generate("adj/colors")) in infra_names:
            continue

        infrastructure = Infrastructure(
            appliances=[*parser.routers, *parser.nodes],
            networks=parser.networks,
            name=infra_name,
        )

        controller = await Controller.prepare_controller_for_infra_creation(
            docker_client,
            networks=parser.networks,
            routers=parser.routers,
            nodes=parser.nodes,
            images=parser.images,
            available_networks=available_networks[slice_start:slice_end],
            infrastructure=infrastructure,
        )

        await controller.change_names(
            container_names=docker_container_names,
            network_names=docker_network_names,
        )
        controller_start_tasks.add(asyncio.create_task(controller.start()))

    await asyncio.gather(*controller_start_tasks)


async def destroy_infra(infrastructure_id: int) -> dict:
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    try:
        controller = await Controller.get_controller_with_infra_objects(
            infrastructure_id
        )
    except NoResultFound:
        return {"message": f"Infrastructure with id: {infrastructure_id} doesn't exist"}

    print(
        f"Deleting infrastructure with id: {controller.infrastructure.id}, name: {controller.infrastructure.name}."
    )
    # destroy docker objects
    await controller.stop(check_id=True)
    # delete objects from db
    await controller.delete_infrastructure()
    print(
        f"Infrastructure with id: {controller.infrastructure.id}, name: {controller.infrastructure.name} deleted."
    )


async def get_infra_ids() -> list[int]:
    async with session_factory() as session:
        return (await session.scalars(select(Infrastructure.id))).all()


async def get_infra(infrastructure_id: int) -> Union[dict, str]:
    try:
        async with session_factory() as session:
            infrastructure = (
                (
                    await session.execute(
                        select(Infrastructure)
                        .where(Infrastructure.id == infrastructure_id)
                        .options(
                            joinedload(Infrastructure.networks)
                            .subqueryload(Network.interfaces)
                            .subqueryload(Interface.appliance),
                        )
                    )
                )
                .unique()
                .scalar_one()
            )
    except NoResultFound:
        return f"Infrastructure with id: {infrastructure_id} doesn't exist"

    result = {"name": infrastructure.name, "networks": {}}
    for network in infrastructure.networks:
        result["networks"][network.name] = {
            "ip": str(network.ipaddress),
            "appliances": [],
        }
        for interface in network.interfaces:
            result["networks"][network.name]["appliances"].append(
                (interface.appliance.name, str(interface.ipaddress))
            )
    return result
