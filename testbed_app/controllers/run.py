from sqlalchemy import select

from testbed_app.database import session_factory
from testbed_app.models import Run, Agent, Template


async def create_run(name: str, template_id: int, agent_ids: list[int]) -> Run:
    """
    Create Run and save it to DB.
    :param name: Run name
    :param template_id: ID of Template that should be used in this Run
    :param agent_ids: IDs of agents that should be used in this Run
    :return: Run object
    """
    async with session_factory() as session:
        agents = (await session.scalars(select(Agent).where(Agent.id.in_(agent_ids)))).all()
        template = (await session.execute(select(Template).where(Template.id == template_id))).scalar_one()

        run = Run(name=name, template=template, agents=agents)
        session.add(run)
        await session.commit()

    return run


async def list_runs() -> list[Run]:
    """
    List all Runs saved in DB.
    :return: list of Runs
    """
    async with session_factory() as session:
        runs = (await session.scalars(select(Run))).all()

    return runs


async def delete_runs(run_id: int) -> Run:
    """
    Delete Run specified by ID from DB.
    :param run_id: Run ID
    :return: deleted Run object
    """
    async with session_factory() as session:
        run = (await session.execute(select(Run).where(Run.id == run_id))).scalar_one()
        await session.delete(run)
        await session.commit()

    return run
