from fastapi import APIRouter
from sqlalchemy.exc import NoResultFound

from dr_emu.controllers import run as run_controller
from pydantic import BaseModel


router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    responses={404: {"description": "Not found"}},
)


class Run(BaseModel):
    name: str
    template_id: int
    agent_ids: list[int]


@router.post("/create/")
async def create_run(run: Run):
    """
    responses:
      200:
        description: Builds docker infrastructure
    """
    await run_controller.create_run(run.name, run.template_id, run.agent_ids)
    return {"message": f"Run {run.name} has been created"}


@router.get("/delete/{run_id}")
async def delete_run(run_id: int):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    try:
        await run_controller.delete_runs(run_id)
    except NoResultFound:
        return {"message": f"Run with id {run_id} ID doesn't exist!"}

    return {"message": f"Run {run_id} has been deleted"}


@router.get("/start/{run_id}")
async def start_run(run_id: int, instances: int = 1):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    try:
        await run_controller.start_run(run_id, instances)
    except NoResultFound:
        return {"message": f"Run with id {run_id} ID doesn't exist!"}

    return {"message": f"{instances} Run instances created"}


@router.get("/stop/{run_id}")
async def stop_run(run_id: int):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    try:
        await run_controller.stop_run(run_id)
    except NoResultFound:
        return {"message": f"Run with id {run_id} ID doesn't exist!"}

    return {"message": f"All instances of Run {run_id} has been stopped"}


@router.get("/")
async def list_runs():
    runs = await run_controller.list_runs()
    if runs:
        response = {"message": {}}
        for run in runs:
            response["message"][run.id] = {"name": run.name, "template_id": run.template_id}
        return response
    else:
        return {"message": "No runs have been created yet"}
