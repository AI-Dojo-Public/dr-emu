from sqlalchemy import select

from testbed_app.lib.logger import logger
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
    logger.debug("Creating Agent", name=name)
    async with session_factory() as session:
        agent = Agent(name=name, role=role, gitlab_url=gitlab_url)
        session.add(agent)
        await session.commit()
    logger.info("Agent created", id=agent.id, name=name)

    return agent


async def list_agents() -> list[Agent]:
    """
    Return all agents saved in DB.
    :return: list of Agents
    """
    logger.debug("Pulling agents from DB")
    async with session_factory() as session:
        agents = (await session.scalars(select(Agent))).all()

    logger.debug("Pulled agents from DB")
    return agents


async def delete_agent(agent_id: int) -> Agent:
    """
    Delete agent specified by ID from DB.
    :param agent_id: ID of an agent
    :return: deleted Agent object.
    """
    logger.debug("Deleting agent", id=agent_id)
    async with session_factory() as session:
        agent = (await session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one()
        await session.delete(agent)
        await session.commit()

    logger.info("Agent deleted", id=agent.id, name=agent.name)
    return agent
