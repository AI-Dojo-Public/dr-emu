import docker

from docker_testbed.cyst_parser import CYSTParser
from docker_testbed.controller import Controller
from docker_testbed.util import util, constants

from cyst_infrastructure import nodes as cyst_nodes, routers as cyst_routers

from starlette.responses import JSONResponse, Response
from starlette.requests import Request
from starlette.schemas import SchemaGenerator


schemas = SchemaGenerator(
    {"openapi": "3.0.0", "info": {"title": "Example API", "version": "1.0"}}
)


async def home(request: Request) -> Response:
    response = Response("Hello, world!", media_type="text/plain")
    return response


# TODO: exception handling for overlying docker networks etc.
async def build_infra(request: Request) -> Response:
    """
    responses:
      200:
        description: Builds docker infra
    """

    number_of_infrastructures = request.query_params.get("infrastructures", 1)

    # TODO: add docker networks check for already existing IP addresses
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

    return JSONResponse({"message": "Infrastructures has been created"})


async def destroy_infra(request: Request) -> Response:
    """
    responses:
      200:
        description: Destroys docker infra
    """
    infrastructure_ids = request.query_params.getlist("id")
    infrastructure_ids = [
        int(infrastructure_id) for infrastructure_id in infrastructure_ids
    ]

    controller = await Controller.get_controller_with_infra_objects(infrastructure_ids)

    # destroy docker objects
    await controller.stop(check_id=True)
    # delete objects from db
    await controller.delete_infrastructures()

    return JSONResponse({"message": "Infrastructure has been destroyed"})


def openapi_schema(request: Request):
    return schemas.OpenAPIResponse(request=request)
