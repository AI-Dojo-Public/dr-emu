from sqlalchemy.orm import joinedload

from testbed_app.database import create_db, destroy_db, session_factory
from fastapi import FastAPI

from testbed_app.middleware import middleware
from testbed_app.models import Infrastructure
from testbed_app.settings import DEBUG
from sqlalchemy import select
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
    for _ in range(int(number_of_infrastructures)):
        parser = CYSTParser(docker_client)
        parser.parse(cyst_routers, cyst_nodes)
        controller = await Controller.prepare_controller_for_infra_creation(
            docker_client, parser
        )

        try:
            await controller.start()
        except Exception as ex:
            await controller.stop(check_id=True)
            raise ex

    return {"message": "Infrastructures have been created"}


@app.get("/infrastructures/delete/{infrastructure_id}")
async def destroy_infra(infrastructure_id: int):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """

    controller = await Controller.get_controller_with_infra_objects(infrastructure_id)

    # destroy docker objects
    await controller.stop(check_id=True)
    # delete objects from db
    await controller.delete_infrastructures()

    return {"message": f"Infrastructure {infrastructure_id} has been destroyed"}


@app.get("/infrastructures/")
async def get_infra_ids():
    async with session_factory() as session:
        infrastracture_ids = (await session.scalars(select(Infrastructure.id))).all()

    return {"infrastructure_ids": infrastracture_ids}


@app.get("/infrastructures/get/{infrastructure_id}")
async def get_infra(infrastructure_id: int):
    async with session_factory() as session:
        if infrastructure_id:
            infrastractures = (
                await session.scalars(
                    select(Infrastructure)
                    .where(Infrastructure.id == infrastructure_id)
                    .options(
                        joinedload(Infrastructure.appliances),
                        joinedload(Infrastructure.networks),
                    )
                )
            ).unique().all()

    result = {"message": {"appliances": [], "networks": {}}}
    for infrastracture in infrastractures:
        for appliance in infrastracture.appliances:
            result["message"]["appliances"].append(appliance.name)
        for network in infrastracture.networks:
            result["message"]["networks"].update({network.name: str(network.ipaddress)})

    return result
