from testbed_app.database import create_db
from fastapi import FastAPI

from testbed_app.middleware import middleware

from testbed_app.settings import DEBUG

from testbed_app import infrastructure_util


app = FastAPI(
    on_startup=[create_db],
    on_shutdown=[],
    middleware=middleware,
    debug=DEBUG,
)


@app.get("/")
async def home() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/infrastructures/create/{number_of_infrastructures}")
async def build_infrastructures(number_of_infrastructures: int):
    """
    responses:
      200:
        description: Builds docker infrastructure
    """
    await infrastructure_util.build_infras(number_of_infrastructures)

    return {"message": "Infrastructures have been created"}


@app.get("/infrastructures/delete/{infrastructure_id}")
async def destroy_infra(infrastructure_id: int):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    await infrastructure_util.destroy_infra(infrastructure_id)

    return {"message": f"Infrastructure {infrastructure_id} has been destroyed"}


@app.get("/infrastructures/")
async def get_infra_ids():
    return {"infrastructure_ids": await infrastructure_util.get_infra_ids()}


@app.get("/infrastructures/get/{infrastructure_id}")
async def get_infra(infrastructure_id: int):
    return {"message": await infrastructure_util.get_infra(infrastructure_id)}
