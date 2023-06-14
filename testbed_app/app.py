from starlette.applications import Starlette

from testbed_app.routes import routes
from testbed_app.event_handlers import on_shutdown, on_startup
from testbed_app.middleware import middleware

app = Starlette(
    routes=routes, on_startup=on_startup, on_shutdown=on_shutdown, middleware=middleware
)
