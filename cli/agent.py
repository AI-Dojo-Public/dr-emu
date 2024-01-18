import typer
from giturlparse import parse
from rich import print
from typing_extensions import Annotated

from cli.config.config import clm
from cli.config.endpoints import Agent
from dr_emu.lib.util import AgentRole
from dr_emu.schemas.agent import (
    AgentLocalSchema,
    AgentPypiSchema,
    AgentGitSchema,
)

agent_typer = typer.Typer()
source_typer = typer.Typer()
agent_typer.add_typer(source_typer, name="create", help="Select source for Agent installation")


def create_agent(agent_schema: AgentPypiSchema | AgentGitSchema | AgentLocalSchema, endpoint):
    """
    Create Agent.
    """

    response = clm.api_post(endpoint, data=agent_schema.model_dump_json())
    if response.status_code == 201:
        print("[bold green]Agent created[/bold green]")
        print(response.json())


@agent_typer.command("list")
def list_agents():
    """
    List all Agents.
    """
    print(clm.api_get_data(Agent.list))


@agent_typer.command("update")
def update_agent(
    agent_id: Annotated[
        int,
        typer.Argument(help="Id of an agent that should be updated"),
    ]
):
    """
    Update agent package
    """
    response = clm.api_get(Agent.update, agent_id)
    if response == 200:
        print(f"Agent with id: {agent_id} has been updated")
    else:
        print(response.text)


@agent_typer.command("delete")
def delete_agent(
    agent_id: Annotated[
        int,
        typer.Argument(help="Id of an agent that should be deleted"),
    ],
):
    """
    Delete Agent based on the provided ID.
    """
    response = clm.api_delete(Agent.delete, agent_id)
    if response.status_code == 204:
        print(f"Agent with id: {agent_id} has been deleted")
    else:
        print(response.text)


@source_typer.command("git")
def git_source(
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
    if parse(url, check_domain=False).valid is False:
        print("[bold red]Invalid repository url![/bold red]")
        return

    agent = AgentGitSchema(
        name=agent_name,
        role=role,
        access_token=token,
        username=username,
        package_name=package_name,
        git_project_url=url,
    )

    create_agent(agent, Agent.create_git)


@source_typer.command("pypi")
def pypi_source(
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
    agent = AgentPypiSchema(
        name=agent_name,
        role=role,
        package_name=package_name,
    )
    create_agent(agent, Agent.create_pypi)


@source_typer.command("local")
def local_source(
    agent_name: Annotated[
        str,
        typer.Option("--name", "-n", help="agent name", prompt="Agent name"),
    ],
    role: Annotated[
        AgentRole,
        typer.Option("--role", "-r", help="Agent role", prompt="Agent role"),
    ],
    path: Annotated[
        str,
        typer.Option(
            help="Path to the Agent project in CYST container",
            prompt="Path to the Agent project in CYST container",
        ),
    ],
    package_name: Annotated[
        str,
        typer.Option("--package", "-p", help="Python package name", prompt="Python package name"),
    ],
):
    agent = AgentLocalSchema(name=agent_name, role=role, path=path, package_name=package_name)
    create_agent(agent, Agent.create_local)
