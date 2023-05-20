from starlette.routing import Route
from starlette.staticfiles import StaticFiles

from testbed_app import views, settings

static = StaticFiles(directory=str(settings.STATIC_DIR))


routes = [
    Route("/", views.home, name="home"),
]
