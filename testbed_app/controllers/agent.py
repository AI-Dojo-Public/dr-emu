from sqlalchemy import select

from testbed_app.database_config import session_factory
from testbed_app.models import Agent


async def create_agent(name: str, role: str, gitlab_url: str) -> Agent:
    """
    Create an Agent object and save it to DB.
    :param name: Name of an Agent
    :param role: role of an Agent (attacker, defender)
    :param gitlab_url: gitlab url from which agent is downloaded
    :return: created Agent object
    """
    async with session_factory() as session:
        agent = Agent(name=name, role=role, gitlab_url=gitlab_url)
        session.add(agent)
        await session.commit()

    return agent


async def list_agents() -> list[Agent]:
    """
    Return all agents saved in DB.
    :return: list of Agents
    """
    async with session_factory() as session:
        agents = (await session.scalars(select(Agent))).all()

    return agents


async def delete_agent(agent_id: int) -> Agent:
    """
    Delete agent specified by ID from DB.
    :param agent_id: ID of an agent
    :return: deleted Agent object.
    """
    async with session_factory() as session:
        agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one()
        await session.delete(agent)
        await session.commit()

    return agent
