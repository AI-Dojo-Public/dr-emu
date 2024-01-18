from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dr_emu.lib.logger import logger
from dr_emu.models import (
    Agent,
    AgentPypi,
    AgentGit,
    AgentLocal,
    AgentInstallationMethod,
)


async def update_agent(agent_id: int, db_session: AsyncSession) -> Agent:
    agent = (
        await db_session.execute(
            select(Agent)
            .where(Agent.id == agent_id)
            .options(joinedload(Agent.install_method).selectin_polymorphic([AgentGit, AgentPypi, AgentLocal]))
        )
    ).scalar_one()

    await agent.update_package()

    return agent


async def create_agent(name: str, role: str, source: AgentInstallationMethod, db_session: AsyncSession) -> Agent:
    """
    Create an Agent object and save it to DB.
    :param source: From where should be agent installed (pypi, git, local folder)
    :param name: Name of an Agent
    :param role: role of an Agent (attacker, defender)
    :param db_session: Async database session
    :return: created Agent object
    """
    logger.debug("Creating Agent", name=name)

    agent = Agent(name=name, role=role, install_method=source)

    logger.info("Installing agent", name=agent.name)
    await agent.install()
    logger.info("Agent installed", name=agent.name)

    db_session.add(agent)
    await db_session.commit()
    logger.info("Agent created", id=agent.id, name=name)

    return agent


async def list_agents(db_session: AsyncSession) -> Sequence[Agent]:
    """
    Return all agents saved in DB.
    :param db_session: Async database session
    :return: list of Agents
    """
    logger.debug("Pulling agents from DB")

    agents = (
        await db_session.scalars(
            select(Agent).options(
                joinedload(Agent.install_method).selectin_polymorphic([AgentGit, AgentPypi, AgentLocal])
            )
        )
    ).all()

    logger.debug("Pulled agents from DB")
    return agents


# TODO: uninstall agent too upon deletion
async def delete_agent(agent_id: int, db_session: AsyncSession) -> Agent:
    """
    Delete agent specified by ID from DB.
    :param agent_id: ID of an agent
    :param db_session: Async database session
    :return: deleted Agent object.
    """
    logger.debug("Deleting agent", id=agent_id)
    agent = (await db_session.execute(select(Agent).where(Agent.id == agent_id))).scalar_one()
    await db_session.delete(agent)
    await db_session.commit()

    logger.info("Agent deleted", id=agent.id, name=agent.name)
    return agent
