from fastapi import FastAPI

from dr_emu.middleware import middleware
from dr_emu.settings import DEBUG
from dr_emu.controllers import database
from dr_emu.api.endpoints import run, infrastructure, agent, template

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
