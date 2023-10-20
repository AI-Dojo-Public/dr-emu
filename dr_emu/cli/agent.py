from sqlalchemy.exc import NoResultFound
from rich import print
import requests
from giturlparse import parse
from dr_emu.cli import UTyper
import typer
from typing_extensions import Annotated

from dr_emu.lib.util import InstallChoice, AgentRole
from dr_emu.models import AgentPypi, AgentGit, AgentLocal
from dr_emu.lib import exceptions
from dr_emu.controllers import agent as agent_controller
from dr_emu.lib.logger import logger

agent_typer = UTyper()


@agent_typer.command("create")
async def create(
    name: Annotated[
        str,
        typer.Argument(help="agent name"),
    ],
    role: Annotated[
        AgentRole,
        typer.Argument(help="Agent role"),
    ] = AgentRole.attacker.value,
    source: Annotated[
        InstallChoice,
        typer.Argument(
            help="type of source from which should be agent installed.(This will trigger a prompt)",
        ),
    ] = InstallChoice.git.value,
):
    """
    Create Agent.
    """

    if source == InstallChoice.git:
        username = typer.prompt("Username", type=str, default="oauth2")
        token = typer.prompt("Personal/Repository access token (hidden input)", type=str, hide_input=True)
        package_name = typer.prompt("Python package name", type=str)
        git_project_url = typer.prompt("Clone with HTTPS repository url", type=str)

        if (parsed_url := parse(git_project_url, check_domain=False)).valid is False:
            print("[bold red]Invalid repository url![/bold red]")
            return

        installation_type = AgentGit(
            access_token=token,
            username=username,
            package_name=package_name,
            host=parsed_url.host,
            owner=parsed_url.owner,
            repo_name=parsed_url.repo,
        )
    elif source == InstallChoice.pypi:
        package_name = typer.prompt("Package name")
        installation_type = AgentPypi(package_name=package_name)
    else:
        package_name = typer.prompt("Package name")
        path_to_agent = typer.prompt("Path to agent")
        installation_type = AgentLocal(path=path_to_agent, package_name=package_name)

    try:
        agent = await agent_controller.create_agent(name, role.value, installation_type)
        print(
            f"[bold green]Agent with name: {agent.name} and id: {agent.id} has been created and installed[/bold green]"
        )
    except (
        requests.exceptions.ConnectionError,
        exceptions.ContainerNotRunning,
        RuntimeError,
        TypeError,
    ) as ex:
        logger.error("Agent couldn't be installed", exception=ex)
        print(f"[bold red]Agent couldn't be installed!.[/bold red]")


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


@agent_typer.command("update")
async def update_agent(
    agent_id: Annotated[
        int,
        typer.Argument(help="Id of an agent that should be updated"),
    ]
):
    """
    Update agent package
    """
    try:
        agent = await agent_controller.update_agent(agent_id)
        print(f"Agent with name: {agent.name} and id: {agent.id} has been updated")
    except NoResultFound:
        print(f"[bold red]Agent with ID: {agent_id} doesn't exist![/bold red]")


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
        print(f"Agent with name: {agent.name} and id: {agent.id} has been deleted")
    except NoResultFound:
        print(f"[bold red]Agent with ID: {agent_id} doesn't exist![/bold red]")
