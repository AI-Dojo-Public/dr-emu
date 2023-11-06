from sqlalchemy.exc import NoResultFound
from docker.errors import ImageNotFound
from dr_emu.cli import UTyper
import typer
from typing_extensions import Annotated
from typing import List

from dr_emu.controllers import run as run_controller
from dr_emu.lib.exceptions import NoAgents

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print

run_typer = UTyper()


@run_typer.command("create")
async def create_run(
    name: Annotated[
        str,
        typer.Argument(help="Name of the Run"),
    ],
    template_id: Annotated[
        int,
        typer.Argument(help="ID of the created infrastructure description"),
    ],
    agent_ids: Annotated[
        List[int],
        typer.Argument(help="IDs of the created agents. eg. 1 2 3"),
    ],
):
    """
    Create Run.
    """
    try:
        run = await run_controller.create_run(name=name, agent_ids=agent_ids, template_id=template_id)
    except NoAgents:
        print(f"[bold red]No agent exists with the given IDs {agent_ids}![/bold red]")
    except NoResultFound:
        print(f"[bold red]Template with ID {template_id} doesn't exist![/bold red]")
    else:
        print(f"[bold green]Run with name: {run.name} and id: {run.id} has been created[/bold green]")


@run_typer.command("list")
async def list_runs():
    """
    List all Runs.
    """
    runs = await run_controller.list_runs()

    if runs:
        for run in runs:
            print(
                f"name: {run.name}, id: {run.id}, template_id: {run.template_id}",
            )
    else:
        print("[bold red]No runs have been created yet[/bold red]")


@run_typer.command("delete")
async def delete_run(
    run_id: Annotated[
        int,
        typer.Argument(help="Id of Run that should be deleted"),
    ],
):
    """
    Delete Run based on the provided ID.
    """
    run = await run_controller.delete_runs(run_id)
    print(f"[bold green]Run with name: {run.name} and id: {run.id} has been deleted[/bold green]")


@run_typer.command("start")
async def start_run(
    run_id: Annotated[
        int,
        typer.Argument(help="Id of Run that should be started"),
    ],
    number_of_instances: Annotated[
        int,
        typer.Argument(help="Number of instances(infrastructures) to run simultaneously"),
    ] = 1,
):
    """
    Start defined number of instances of created Run.
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Building Infrastructures", total=None)
            await run_controller.start_run(run_id, number_of_instances)
        print(f"[bold green]{number_of_instances} Run instances created[/bold green]")
    except NoResultFound:
        print(f"[bold red]Run with id {run_id} ID doesn't exist![/bold red]")
    except (ImageNotFound, RuntimeError, Exception) as ex:
        print(f"[bold red]{ex}[/bold red]")


@run_typer.command("stop")
async def stop_run(
    run_id: Annotated[
        int,
        typer.Argument(help="Id of Run that should be stopped"),
    ]
):
    """
    Start defined number of instances of created Run.
    """

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Deleting Instances", total=None)
        try:
            await run_controller.stop_run(run_id)
            print(f"[bold green]All Run instances stopped[/bold green]")
        except NoResultFound:
            print(f"[bold red]Run with id {run_id} ID doesn't exist![/bold red]")
