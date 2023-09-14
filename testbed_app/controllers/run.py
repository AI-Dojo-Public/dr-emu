from sqlalchemy import select

from testbed_app.database_config import session_factory
from testbed_app.lib.logger import logger
from testbed_app.models import Run, Agent, Template


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
