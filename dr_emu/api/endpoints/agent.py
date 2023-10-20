from typing import Annotated

from fastapi import APIRouter
import requests
from sqlalchemy.exc import NoResultFound
from dr_emu.controllers import agent as agent_controller
from pydantic import BaseModel
from fastapi import Body
from giturlparse import parse
from dr_emu.lib.util import AgentRole


from dr_emu.models import AgentPypi, AgentGit, AgentLocal

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)


class Agent(BaseModel):
    name: str
    role: AgentRole


class AgentLocalSchema(Agent):
    path: str


class AgentPypiSchema(Agent):
    name: str
    role: AgentRole
    package_name: str


class AgentGitSchema(AgentPypiSchema):
    access_token: str
    username: str
    git_project_url: str


@router.post("/create/")
async def create_agent(
    *,
    agent: Annotated[
        AgentPypiSchema | AgentGitSchema | AgentLocalSchema,
        Body(
            openapi_examples={
                "git": {
                    "summary": "Agent installation from GIT",
                    "value": {
                        "name": "Foo",
                        "role": AgentRole.attacker,
                        "package_name": "ai-agent",
                        "username": "git_user",
                        "access_token": "git_token",
                        "git_project_url": "https://{git_host}/{owner}/{repo_name}.git",
                    },
                },
                "pypi": {
                    "summary": "Agent installation from PYPI",
                    "value": {
                        "name": "Foo",
                        "role": AgentRole.attacker,
                        "package_name": "ai-agent",
                    },
                },
                "local": {
                    "summary": "Agent installation local directory",
                    "description": "For installation with Agent repository present within the CYST docker container.",
                    "value": {
                        "name": "Foo",
                        "role": AgentRole.attacker,
                        "package_name": "ai-agent",
                        "path": "path/to/agent/package",
                    },
                },
            },
        ),
    ],
):
    """
    responses:
      200:
        description: Builds docker infrastructure
    """

    if agent == AgentGitSchema:
        if (parsed_url := parse(AgentGitSchema.git_project_url)).valid is False:
            print("[bold red]Invalid repository url![/bold red]")
            return

        installation_type = AgentGit(
            access_token=AgentGitSchema.access_token,
            username=AgentGitSchema.username,
            package_name=AgentGitSchema.package_name,
            host=parsed_url.host,
            owner=parsed_url.owner,
            repo_name=parsed_url.repo,
        )
    elif agent == AgentPypiSchema:
        installation_type = AgentPypi(package_name=AgentPypiSchema.package_name)
    else:
        installation_type = AgentLocal(package_name=AgentLocalSchema.package_name, path=AgentLocalSchema.path)

    try:
        await agent_controller.create_agent(agent.name, agent.role.value, installation_type)
    except requests.ConnectionError as ex:
        return {"message": f"Invalid url({agent.git_url}) for Agent", "exception": ex}

    return {"message": f"Agent {agent.name} has been created"}


@router.get("/delete/{agent_id}")
async def delete_agent(agent_id: int):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    try:
        await agent_controller.delete_agent(agent_id)
    except NoResultFound:
        return {"message": f"Run with id {agent_id} ID doesn't exist!"}

    return {"message": f"Agent {agent_id} has been deleted"}


@router.get("/")
async def list_agent():
    agents = await agent_controller.list_agents()
    if agents:
        response = {"message": []}
        for agent in agents:
            response["message"].append({"name": agent.name, "id": agent.id})
        return response
    else:
        return {"message": "No agents have been created yet"}
