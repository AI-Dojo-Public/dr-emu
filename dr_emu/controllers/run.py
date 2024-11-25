import asyncio
from typing import Sequence

from docker.errors import ImageNotFound, APIError
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload

from fastapi import APIRouter, HTTPException, status

from dr_emu.settings import settings
from dr_emu.api.helpers import nonexistent_object_msg
from dr_emu.controllers.infrastructure import InfrastructureController
from dr_emu.lib.logger import logger
from dr_emu.models import Run, Template, Instance, Infrastructure, Node, ServiceContainer

from sqlalchemy.ext.asyncio import AsyncSession

from shared import constants


async def create_run(name: str, template_id: int, db_session: AsyncSession) -> Run:
    """
    Create Run and save it to DB.
    :param name: Run name
    :param template_id: ID of Template that should be used in this Run
    :param db_session: Async database session
    :return: Run object
    """
    logger.debug("Creating Run", name=name, template_id=template_id)

    template = (await db_session.execute(select(Template).where(Template.id == template_id))).scalar_one()

    run = Run(name=name, template=template)
    db_session.add(run)
    await db_session.commit()

    logger.info("Run created", name=run.name, id=run.id)

    return run


async def list_runs(db_session: AsyncSession) -> Sequence[Run]:
    """
    List all Runs saved in DB.
    :param db_session: Async database session
    :return: list of Runs
    """
    logger.debug("Listing runs")

    runs = (
        (await db_session.scalars(select(Run).options(joinedload(Run.instances).joinedload(Instance.infrastructure))))
        .unique()
        .all()
    )

    return runs


async def get_run(run_id: int, db_session: AsyncSession) -> Run:
    """
    List all Runs saved in DB.
    :param run_id: run ID
    :param db_session: Async database session
    :return: list of Runs
    """
    logger.debug("Listing runs")

    run = (
        (
            await db_session.execute(
                select(Run)
                .where(Run.id == run_id)
                .options(joinedload(Run.instances).joinedload(Instance.infrastructure))
            )
        )
        .unique()
        .scalar_one()
    )

    return run


async def delete_run(run_id: int, db_session: AsyncSession) -> Run:
    """
    Delete Run specified by ID from DB.
    :param run_id: Run ID
    :param db_session: Async database session
    :return: deleted Run object
    """
    logger.debug("Deleting run", id=run_id)

    run = (await db_session.execute(select(Run).where(Run.id == run_id))).scalar_one()
    await db_session.delete(run)
    await db_session.commit()
    logger.info("Run deleted", name=run.name, id=run.id)
    return run


async def start_run(run_id: int, number_of_instances: int, db_session: AsyncSession):
    """
    Start number of specified Run instances (infrastructure clones)
    :param run_id: ID of Run
    :param number_of_instances: number of instances to start
    :param db_session: Async database session
    :return:
    :raises: sqlalchemy.exc.NoResultFound
    """

    run = (await db_session.execute(select(Run).where(Run.id == run_id))).scalar_one()
    try:
        run_instances = await InfrastructureController.build_infras(number_of_instances, run, db_session)
        db_session.add_all(run_instances)
        await db_session.commit()
    except* (ImageNotFound, RuntimeError, APIError, TypeError) as ex:
        if settings.debug:
            raise ex
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))
    except* Exception as err:
        raise err


async def stop_run(run_id: int, db_session: AsyncSession):
    """
    Stop all instances of this Run
    :param run_id:
    :param db_session: Async database session
    :return:
    :raises: sqlalchemy.exc.NoResultFound
    """

    run = (
        (
            await db_session.execute(
                select(Run)
                .where(Run.id == run_id)
                .options(
                    joinedload(Run.instances)
                    .joinedload(Instance.infrastructure)
                    .options(
                        joinedload(Infrastructure.routers),
                        joinedload(Infrastructure.networks),
                        joinedload(Infrastructure.nodes).options(
                            joinedload(Node.service_containers).joinedload(ServiceContainer.volumes), joinedload(Node.volumes)
                        ),
                    )
                )
            )
        )
        .unique()
        .scalar_one()
    )

    async with asyncio.TaskGroup() as tg:
        for instance in run.instances:
            tg.create_task(InfrastructureController.stop_infra(instance.infrastructure))
            await db_session.delete(instance)

    await db_session.commit()
