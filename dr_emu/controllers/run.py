import asyncio
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from dr_emu.controllers.infrastructure import InfrastructureController
from dr_emu.database_config import session_factory
from dr_emu.lib.logger import logger
from dr_emu.models import Run, Agent, Template, Instance, Infrastructure, Node
from dr_emu.lib.exceptions import NoAgents
from docker.errors import ImageNotFound


async def create_run(name: str, template_id: int, agent_ids: list[int]) -> Run:
    """
    Create Run and save it to DB.
    :param name: Run name
    :param template_id: ID of Template that should be used in this Run
    :param agent_ids: IDs of agents that should be used in this Run
    :return: Run object
    """
    logger.debug("Creating Run", name=name, template_id=template_id, agent_ids=agent_ids)
    async with session_factory() as session:
        agents = (await session.scalars(select(Agent).where(Agent.id.in_(agent_ids)))).all()
        if not agents:
            raise NoAgents()
        template = (await session.execute(select(Template).where(Template.id == template_id))).scalar_one()

        run = Run(name=name, template=template, agents=agents)
        session.add(run)
        await session.commit()

    logger.info("Run created", name=run.name, id=run.id)

    return run


async def list_runs() -> list[Run]:
    """
    List all Runs saved in DB.
    :return: list of Runs
    """
    logger.debug("Listing runs")
    async with session_factory() as session:
        runs = (await session.scalars(select(Run))).all()

    return runs


async def delete_runs(run_id: int) -> Run:
    """
    Delete Run specified by ID from DB.
    :param run_id: Run ID
    :return: deleted Run object
    """
    logger.debug("Deleting run", id=run_id)
    async with session_factory() as session:
        run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
        await session.delete(run)
        await session.commit()
    logger.info("Run deleted", name=run.name, id=run.id)
    return run


async def start_run(run_id: int, number_of_instances: int):
    """
    Start number of specified Run instances (infrastructure clones)
    :param run_id: ID of Run
    :param number_of_instances: number of instances to start
    :return:
    :raises: sqlalchemy.exc.NoResultFound
    """
    async with session_factory() as session:
        run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()

    await InfrastructureController.build_infras(number_of_instances, run)


async def stop_run(run_id: int):
    """
    Stop all instances of this Run
    :param run_id:
    :return:
    :raises: sqlalchemy.exc.NoResultFound
    """
    async with session_factory() as session:
        run = (
            (
                await session.execute(
                    select(Run)
                    .where(Run.id == run_id)
                    .options(
                        joinedload(Run.instances)
                        .subqueryload(Instance.infrastructure)
                        .options(
                            joinedload(Infrastructure.routers),
                            joinedload(Infrastructure.nodes).subqueryload(Node.services),
                            joinedload(Infrastructure.networks),
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
            await session.delete(instance)

        await asyncio.gather(*stop_instance_tasks)
        await session.commit()
