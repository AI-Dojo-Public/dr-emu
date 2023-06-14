from starlette.routing import Route
from starlette.staticfiles import StaticFiles

from testbed_app import views, settings

static = StaticFiles(directory=str(settings.STATIC_DIR))


routes = [
    Route("/", views.home, name="home", methods=["GET"]),
    Route("/create-infra", views.build_infra, name="create_infra", methods=["GET"]),
    Route("/destroy-infra", views.destroy_infra, name="destroy_infra", methods=["GET"]),
    Route("/schema", views.openapi_schema, include_in_schema=False)
]
