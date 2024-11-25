from fastapi import FastAPI
from contextlib import asynccontextmanager

from dr_emu.middleware import middleware
from dr_emu.settings import settings
from dr_emu.database_config import sessionmanager
from dr_emu.api.endpoints import run, infrastructure, template, image


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function that handles startup and shutdown events.
    To understand more, read https://fastapi.tiangolo.com/advanced/events/
    """
    yield
    if sessionmanager._engine is not None:
        # Close the DB connection
        await sessionmanager.close()


app = FastAPI(
    lifespan=lifespan,
    middleware=middleware,
    debug=settings.debug,
)

# Routers
app.include_router(run.router)
app.include_router(infrastructure.router)
app.include_router(template.router)
app.include_router(image.router)


@app.get("/")
async def home() -> dict[str, str]:
    return {"message": "Dr-Emu will see you now"}
