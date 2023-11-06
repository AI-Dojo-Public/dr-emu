from sqlalchemy.exc import NoResultFound
from rich import print
import requests
from giturlparse import parse
from dr_emu.cli import UTyper
import typer
from typing_extensions import Annotated

from dr_emu.lib.util import AgentRole
from dr_emu.models import AgentPypi, AgentGit, AgentLocal
from dr_emu.lib import exceptions
from dr_emu.controllers import agent as agent_controller
from dr_emu.lib.logger import logger

agent_typer = UTyper()
source_typer = UTyper()
agent_typer.add_typer(source_typer, name="create", help="Select source for Agent installation")


async def create_agent(name, role, source):
    """
    Create Agent.
    """

    try:
        agent = await agent_controller.create_agent(name, role.value, source)
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
        print(f"[bold red]Agent couldn't be installed![/bold red]")


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


@source_typer.command("git")
async def git_source(
    agent_name: Annotated[
        str,
        typer.Option("--name", "-n", help="agent name", prompt="Agent name"),
    ],
    role: Annotated[
        AgentRole,
        typer.Option("--role", "-r", help="Agent role", prompt="Agent role"),
    ],
    package_name: Annotated[
        str,
        typer.Option("--package", "-p", help="Python package name", prompt="Python package name"),
    ],
    url: Annotated[
        str,
        typer.Option(
            "--url",
            "-l",
            help="Clone with HTTPS repository url",
            prompt="Clone with HTTPS repository url",
        ),
    ],
    token: Annotated[
        str,
        typer.Option(
            "--token",
            "-t",
            help="Git access token",
            prompt="Personal/Repository access token (hidden input)",
            hide_input=True,
        ),
    ],
    username: Annotated[
        str,
        typer.Option(
            "--username",
            "-u",
            help="Git username",
        ),
    ] = "oauth2",
):
    if (parsed_url := parse(url, check_domain=False)).valid is False:
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

    await create_agent(agent_name, role, installation_type)


@source_typer.command("pypi")
async def git_source(
    agent_name: Annotated[
        str,
        typer.Option("--name", "-n", help="agent name", prompt="Agent name"),
    ],
    role: Annotated[
        AgentRole,
        typer.Option("--role", "-r", help="Agent role", prompt="Agent role"),
    ],
    package_name: Annotated[
        str,
        typer.Option("--package", "-p", help="Python package name", prompt="Python package name"),
    ],
):
    installation_type = AgentPypi(package_name=package_name)
    await create_agent(agent_name, role, installation_type)


@source_typer.command("local")
async def git_source(
    agent_name: Annotated[
        str,
        typer.Option("--name", "-n", help="agent name", prompt="Agent name"),
    ],
    role: Annotated[
        AgentRole,
        typer.Option("--role", "-r", help="Agent role", prompt="Agent role"),
    ],
    package_name: Annotated[
        str,
        typer.Option("--package", "-p", help="Python package name", prompt="Python package name"),
    ],
    path: Annotated[
        str,
        typer.Option(
            help="Path to the Agent project in CYST container",
            prompt="Path to the Agent project in CYST container",
        ),
    ],
):
    installation_type = AgentLocal(path=path, package_name=package_name)
    await create_agent(agent_name, role, installation_type)
