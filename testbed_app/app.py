import asyncio
import randomname

from sqlalchemy.orm import joinedload

from docker_testbed.util import util, constants
from testbed_app.database import create_db, session_factory
from fastapi import FastAPI

from testbed_app.middleware import middleware
from testbed_app.models import Infrastructure
from testbed_app.settings import DEBUG
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
import docker

from docker_testbed.cyst_parser import CYSTParser
from docker_testbed.controller import Controller

from cyst_infrastructure import nodes as cyst_nodes, routers as cyst_routers

app = FastAPI(
    on_startup=[create_db],
    on_shutdown=[],
    middleware=middleware,
    debug=DEBUG,
)


@app.get("/")
async def home() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/infrastructures/create/{number_of_infrastructures}")
async def build_infra(number_of_infrastructures: int):
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

        print(f"INFRA NAMES: {infra_names}")
        while (infra_name := randomname.generate('adj/colors')) in infra_names:
            continue

        infrastructure = Infrastructure(
            appliances=[*parser.routers, *parser.nodes],
            networks=parser.networks,
            name=infra_name
        )

        controller = await Controller.prepare_controller_for_infra_creation(
            docker_client,
            networks=parser.networks,
            routers=parser.routers,
            nodes=parser.nodes,
            images=parser.images,
            available_networks=available_networks[slice_start:slice_end],
            infrastructure=infrastructure
        )

        await controller.change_names(
            container_names=docker_container_names,
            network_names=docker_network_names,
        )
        controller_start_tasks.add(asyncio.create_task(controller.start()))

    await asyncio.gather(*controller_start_tasks)

    return {"message": "Infrastructures have been created"}


@app.get("/infrastructures/delete/{infrastructure_id}")
async def destroy_infra(infrastructure_id: int):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    try:
        controller = await Controller.get_controller_with_infra_objects(infrastructure_id)
    except NoResultFound:
        return {"message": f"Infrastructure with id: {infrastructure_id} doesn't exist"}

    # destroy docker objects
    await controller.stop(check_id=True)
    # delete objects from db
    await controller.delete_infrastructure()

    return {"message": f"Infrastructure {infrastructure_id} has been destroyed"}


@app.get("/infrastructures/")
async def get_infra_ids():
    async with session_factory() as session:
        infrastructure_ids = (await session.scalars(select(Infrastructure.id))).all()

    return {"infrastructure_ids": infrastructure_ids}


@app.get("/infrastructures/get/{infrastructure_id}")
async def get_infra(infrastructure_id: int):
    async with session_factory() as session:
        if infrastructure_id:
            infrastructures = (
                (
                    await session.scalars(
                        select(Infrastructure)
                        .where(Infrastructure.id == infrastructure_id)
                        .options(
                            joinedload(Infrastructure.appliances),
                            joinedload(Infrastructure.networks),
                        )
                    )
                )
                .unique()
                .all()
            )

    result = {"message": {"appliances": [], "networks": {}}}
    for infrastructure in infrastructures:
        for appliance in infrastructure.appliances:
            result["message"]["appliances"].append(appliance.name)
        for network in infrastructure.networks:
            result["message"]["networks"].update({network.name: str(network.ipaddress)})

    return result
