from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from dr_emu.lib.logger import logger
from dr_emu.database_config import session_factory
from dr_emu.models import Agent, AgentPypi, AgentGit, AgentLocal, AgentInstallationMethod


async def update_agent(agent_id: int) -> Agent:
    async with session_factory() as session:
        agent = (
            await session.execute(
                select(Agent)
                .where(Agent.id == agent_id)
                .options(joinedload(Agent.install_method).selectin_polymorphic([AgentGit, AgentPypi, AgentLocal]))
            )
        ).scalar_one()

        await agent.update_package()

    return agent


async def create_agent(
    name: str,
    role: str,
    source: AgentInstallationMethod,
) -> Agent:
    """
    Create an Agent object and save it to DB.
    :param source: From where should be agent installed (pypi, git, local folder)
    :param name: Name of an Agent
    :param role: role of an Agent (attacker, defender)
    :return: created Agent object
    """
    logger.debug("Creating Agent", name=name)
    async with session_factory() as session:
        agent = Agent(name=name, role=role, install_method=source)

        logger.info("Installing agent", name=agent.name)
        await agent.install()
        logger.info("Agent installed", name=agent.name)

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
