from fastapi import FastAPI

from testbed_app.middleware import middleware
from testbed_app.settings import DEBUG
from testbed_app.controllers import database
from testbed_app.api.endpoints import run, infrastructure, agent, template

app = FastAPI(
    on_startup=[database.create_db],
    on_shutdown=[],
    middleware=middleware,
    debug=DEBUG,
)

app.include_router(run.router)
app.include_router(infrastructure.router)
app.include_router(agent.router)
app.include_router(template.router)


@app.get("/")
async def home() -> dict[str, str]:
    return {"message": "Dr-Emu will see you now"}
