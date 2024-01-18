from fastapi import APIRouter, Response, status
from giturlparse import parse
from sqlalchemy.exc import NoResultFound

from dr_emu.api.dependencies.core import DBSession
from dr_emu.api.helpers import nonexistent_object_msg
from dr_emu.controllers import agent as agent_controller
from dr_emu.lib import exceptions
from dr_emu.models import AgentPypi, AgentGit, AgentLocal
from dr_emu.schemas.agent import (
    AgentGitSchema,
    AgentPypiSchema,
    AgentLocalSchema,
    AgentOut,
)

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)


async def create_agent(agent, session, installation_type, response: Response):
    try:
        agent = await agent_controller.create_agent(agent.name, agent.role.value, installation_type, session)
        return AgentOut(id=agent.id, name=agent.name, role=agent.role, type=agent.install_method.type)
    except (
        exceptions.ContainerNotRunning,
        RuntimeError,
        TypeError,
    ) as ex:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"exception": ex}


@router.post(
    "/create/git/",
    responses={201: {"description": "Object successfully created"}},
    response_model=AgentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_git_agent(response: Response, agent: AgentGitSchema, session: DBSession):
    if (parsed_url := parse(agent.git_project_url)).valid is False:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return {"message": "Invalid repository url!"}

    installation_type = AgentGit(
        access_token=agent.access_token,
        username=agent.username,
        package_name=agent.package_name,
        host=parsed_url.host,
        owner=parsed_url.owner,
        repo_name=parsed_url.repo,
    )

    return await create_agent(agent, session, installation_type, response)


@router.post(
    "/create/local/",
    responses={201: {"description": "Object successfully created"}},
    response_model=AgentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_local_agent(*, agent: AgentLocalSchema, session: DBSession, response: Response):
    installation_type = AgentLocal(package_name=agent.package_name, path=agent.path)
    return await create_agent(agent, session, installation_type, response)


@router.post(
    "/create/pypi/",
    responses={201: {"description": "Object successfully created"}},
    response_model=AgentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_pypi_agent(*, agent: AgentPypiSchema, session: DBSession, response: Response):
    installation_type = AgentPypi(package_name=agent.package_name)
    return await create_agent(agent, session, installation_type, response)


@router.delete(
    "/delete/{agent_id}/",
    responses={204: {"description": "Object successfully deleted"}},
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_agent(agent_id: int, session: DBSession):
    try:
        await agent_controller.delete_agent(agent_id, session)
    except NoResultFound:
        return nonexistent_object_msg("Agent", agent_id)

    return {"message": f"Agent {agent_id} has been deleted"}


@router.get("/update/{agent_id}/")
async def update_agent(agent_id: int, session: DBSession, response: Response):
    try:
        await agent_controller.update_agent(agent_id, session)
    except NoResultFound:
        return nonexistent_object_msg("Agent", agent_id)
    except Exception as ex:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"message": str(ex)}


@router.get("/", response_model=list[AgentOut])
async def list_agents(session: DBSession):
    agents = await agent_controller.list_agents(session)

    response = []
    for agent in agents:
        response.append(AgentOut(name=agent.name, id=agent.id, role=agent.role, type=agent.install_method.type))

    return response
