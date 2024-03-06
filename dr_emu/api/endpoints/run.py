from docker.errors import ImageNotFound
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import NoResultFound

from dr_emu.api.dependencies.core import DBSession
from dr_emu.api.helpers import nonexistent_object_msg
from dr_emu.controllers import run as run_controller
from dr_emu.lib.exceptions import NoAgents
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
            agent_ids=run.agent_ids,
            template_id=run.template_id,
            db_session=session,
        )
    except NoAgents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.AGENT, run.agent_ids)
        )
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.TEMPLATE, run.template_id)
        )
    return RunOut(
        id=run_model.id,
        name=run_model.name,
        template_id=run_model.template_id,
        agent_ids=run.agent_ids,
    )


@router.delete(
    "/delete/{run_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Object successfully deleted"}},
)
async def delete_run(run_id: int, session: DBSession, ):
    try:
        await run_controller.delete_run(run_id, session)
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.RUN, run_id))


# Make a data stream for checks that the run is still building
@router.post("/start/{run_id}/")
async def start_run(session: DBSession, run_id: int, instances: int = 1):
    try:
        await run_controller.start_run(run_id, instances, session)
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.RUN, run_id))
    except (ImageNotFound, RuntimeError, Exception) as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))

    return {"message": f"{instances} Run instances created"}


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
            agent_ids = [agent.id for agent in run.agents]
            infrastructure_ids = [instance.infrastructure.id for instance in run.instances]
            run_info = RunInfo(
                id=run.id,
                name=run.name,
                template_id=run.template_id,
                agent_ids=agent_ids,
                infrastructure_ids=infrastructure_ids,
            )
            result.append(run_info)
        return result
    else:
        return []
