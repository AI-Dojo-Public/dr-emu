from sqlalchemy.exc import NoResultFound
from rich import print

from cli import UTyper
import typer
from typing_extensions import Annotated
from testbed_app.controllers import agent as agent_controller

agent_typer = UTyper()


@agent_typer.command("create")
async def create(
    gitlab_url: Annotated[
        str,
        typer.Argument(help="gitlab link to the agent that should be downloaded"),
    ],
    name: Annotated[
        str,
        typer.Argument(help="agent name"),
    ],
    role: Annotated[
        str,
        typer.Argument(help="Agent role (def, attack)"),
    ],
):
    """
    Create Agent.
    """
    agent = await agent_controller.create_agent(name, role, gitlab_url)
    print(f"Agent with name: {agent.name} and id: {agent.id} has been created")


@agent_typer.command("list")
async def list_agents():
    """
    List all Agents.
    """
    agents = await agent_controller.list_agents()
    if agents:
        for agent in agents:
            print(
                f"name: {agent.name}, id: {agent.id}, type: {agent.role}",
            )
    else:
        print("No agents have been created yet")


@agent_typer.command("delete")
async def delete_agent(
    agent_id: Annotated[
        int,
        typer.Argument(help="Id of an agent that should be deleted"),
    ],
):
    """
    Delete Agent based on the provided ID.
    """
    try:
        agent = await agent_controller.delete_agent(agent_id)
    except NoResultFound:
        print("[bold red]Agent with provided ID doesn't exist![/bold red]")
    else:
        print(f"Agent with name: {agent.name} and id: {agent.id} has been deleted")
