import docker
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from databases import Database

from testbed_app import settings

# database = Database(settings.DATABASE_URL)

docker_client = docker.from_env()

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

static = StaticFiles(directory=str(settings.STATIC_DIR))
