from testbed_app.database import create_db, destroy_db
from starlette.applications import Starlette

from testbed_app.routes import routes
from testbed_app.middleware import middleware
from testbed_app.settings import DEBUG

app = Starlette(
    routes=routes,
    on_startup=[create_db],
    on_shutdown=[],
    middleware=middleware,
    debug=DEBUG,
)
