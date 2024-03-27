import asyncio
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from dr_emu.controllers.infrastructure import InfrastructureController
from dr_emu.lib.logger import logger
from dr_emu.models import Run, Agent, Template, Instance, Infrastructure, Node
from dr_emu.lib.exceptions import NoAgents
from sqlalchemy.ext.asyncio import AsyncSession


async def create_run(name: str, template_id: int, agent_ids: list[int], db_session: AsyncSession) -> Run:
    """
    Create Run and save it to DB.
    :param name: Run name
    :param template_id: ID of Template that should be used in this Run
    :param agent_ids: IDs of agents that should be used in this Run
    :param db_session: Async database session
    :return: Run object
    """
    logger.debug("Creating Run", name=name, template_id=template_id, agent_ids=agent_ids)

    agents = (await db_session.scalars(select(Agent).where(Agent.id.in_(agent_ids)))).all()
    if not agents:
        raise NoAgents()
    template = (await db_session.execute(select(Template).where(Template.id == template_id))).scalar_one()

    run = Run(name=name, template=template, agents=agents)
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
        (
            await db_session.scalars(
                select(Run).options(
                    joinedload(Run.agents), joinedload(Run.instances).joinedload(Instance.infrastructure)
                )
            )
        )
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
                .options(joinedload(Run.agents), joinedload(Run.instances).joinedload(Instance.infrastructure))
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

    await InfrastructureController.build_infras(number_of_instances, run, db_session)


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
                        joinedload(Infrastructure.nodes).joinedload(Node.services),
                    )
                )
            )
        )
        .unique()
        .scalar_one()
    )
    stop_instance_tasks = set()

    for instance in run.instances:
        stop_instance_tasks.add(InfrastructureController.stop_infra(instance.infrastructure))
        await db_session.delete(instance)

    await asyncio.gather(*stop_instance_tasks)
    await db_session.commit()
