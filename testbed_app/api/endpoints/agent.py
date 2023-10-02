from fastapi import APIRouter
from sqlalchemy.exc import NoResultFound
from enum import Enum
from testbed_app.controllers import agent as agent_controller
from pydantic import BaseModel


router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)


class AgentRoles(Enum):
    attacker: "attacker"
    defender: "defender"


class Agent(BaseModel):
    name: str
    role: str
    url: str


@router.post("/create/")
async def create_agent(agent: Agent):
    """
    responses:
      200:
        description: Builds docker infrastructure
    """
    await agent_controller.create_agent(agent.name, agent.role, agent.url)
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
