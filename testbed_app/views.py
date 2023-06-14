from testbed_app.resources import templates
import docker

from sqlalchemy.orm import joinedload
from sqlalchemy import select

from testbed_app.models import Network, Router, Node
from testbed_app.database import session_factory

from docker_testbed.cyst_parser import CYSTParser
from docker_testbed.controller import Controller

from starlette.responses import JSONResponse
from starlette.schemas import SchemaGenerator


schemas = SchemaGenerator(
    {"openapi": "3.0.0", "info": {"title": "Example API", "version": "1.0"}}
)


async def home(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context=context)


async def build_infra(request):
    """
    responses:
      200:
        description: Builds docker infra
    """
    docker_client = docker.from_env()
    parser = CYSTParser(docker_client)
    parser.parse()

    controller = Controller(
        docker_client, parser.networks, parser.routers, parser.nodes, parser.images
    )

    try:
        await controller.start()
    except Exception as ex:
        await controller.stop(check_id=True)
        raise ex
    return JSONResponse({"message": "Infrastructure has been created"})


async def destroy_infra(request):
    """
    responses:
      200:
        description: Destroys docker infra
    """
    docker_client = docker.from_env()
    async with session_factory() as session:
        nodes = (
            await session.scalars(select(Node).options(joinedload(Node.services)))
        ).unique()
        routers = await session.scalars(select(Router))
        networks = await session.scalars(select(Network))

    controller = Controller(docker_client, networks, routers, nodes, set())

    await controller.stop(check_id=True)
    return JSONResponse({"message": "Infrastructure has been destroyed"})


def openapi_schema(request):
    return schemas.OpenAPIResponse(request=request)
