import docker
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from testbed_app import settings

docker_client = docker.from_env()

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

static = StaticFiles(directory=str(settings.STATIC_DIR))
