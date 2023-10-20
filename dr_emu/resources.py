import docker
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from dr_emu import settings

docker_client = docker.from_env()

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

static = StaticFiles(directory=str(settings.STATIC_DIR))
