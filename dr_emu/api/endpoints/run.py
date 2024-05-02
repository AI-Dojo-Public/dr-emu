from docker.errors import ImageNotFound, APIError, NotFound
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import NoResultFound

from dr_emu.api.dependencies.core import DBSession
from dr_emu.api.helpers import nonexistent_object_msg
from dr_emu.controllers import run as run_controller
from dr_emu.schemas.run import Run, RunOut, RunInfo
from shared import constants

router = APIRouter(
    prefix="/runs",
    tags=["runs"],
    responses={
        404: {"description": "Not found"},
    },
)


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    responses={201: {"description": "Object successfully created"}},
    response_model=RunOut,
)
async def create_run(run: Run, session: DBSession):
    try:
        run_model = await run_controller.create_run(
            name=run.name,
            template_id=run.template_id,
            db_session=session,
        )
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.TEMPLATE, run.template_id)
        )
    return RunOut(
        id=run_model.id,
        name=run_model.name,
        template_id=run_model.template_id,
    )


@router.delete(
    "/delete/{run_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Object successfully deleted"}},
)
async def delete_run(
    run_id: int,
    session: DBSession,
):
    try:
        await run_controller.delete_run(run_id, session)
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.RUN, run_id))


# Make a data stream for checks that the run is still building


run_start_description = """
Start specified number of Run instances.

## Instance limit
The maximum number of instances possible is 256 dues to IP address space given that the whole 
private ip range of the **10.0.0.0/8** is available.
"""


@router.post(
    "/start/{run_id}/",
    description=run_start_description,
    )
async def start_run(session: DBSession, run_id: int, instances: int = 1):
    try:
        await run_controller.start_run(
            run_id, instances, session
        )
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.RUN, run_id)
        )
    except (ImageNotFound, RuntimeError, APIError) as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))
    except Exception as err:
        raise err

    return {"message": f"{instances} Run instances started"}


@router.post("/stop/{run_id}/")
async def stop_run(run_id: int, session: DBSession):
    try:
        await run_controller.stop_run(run_id, session)
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.RUN, run_id))

    return {"message": f"All instances of Run {run_id} has been stopped"}


@router.get("/", response_model=list[RunInfo])
async def list_runs(session: DBSession):
    runs = await run_controller.list_runs(session)
    if runs:
        result = []
        for run in runs:
            infrastructure_ids = [instance.infrastructure.id for instance in run.instances]
            run_info = RunInfo(
                id=run.id,
                name=run.name,
                template_id=run.template_id,
                infrastructure_ids=infrastructure_ids,
            )
            result.append(run_info)
        return result
    else:
        return []


@router.get("/get/{run_id}/", response_model=RunInfo)
async def get_run(run_id: int, session: DBSession):
    try:
        run = await run_controller.get_run(run_id, session)
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.RUN, run_id))

    infrastructure_ids = [instance.infrastructure.id for instance in run.instances]

    return RunInfo(
        id=run.id,
        name=run.name,
        template_id=run.template_id,
        infrastructure_ids=infrastructure_ids,
    )
