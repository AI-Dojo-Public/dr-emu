from typing import List

import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Annotated

from cli.config.config import clm
from cli.config.endpoints import Run
from dr_emu.schemas.run import Run as RunSchema

run_typer = typer.Typer()


@run_typer.command("create")
def create_run(
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
    response = clm.api_post(
        Run.create,
        data=RunSchema(name=name, template_id=template_id, agent_ids=agent_ids).model_dump_json(),
    )
    if response.status_code == 201:
        print(f"[bold green]Run created successfully[/bold green]")
        print(response.json())
    else:
        print(f"[bold red]{response.text}[/bold red]")


@run_typer.command("list")
def list_runs():
    """
    List all Runs.
    """
    return clm.api_get_data(Run.list)


@run_typer.command("delete")
def delete_run(
    run_id: Annotated[
        int,
        typer.Argument(help="Id of Run that should be deleted"),
    ],
):
    """
    Delete Run based on the provided ID.
    """
    response = clm.api_delete(Run.delete, run_id)
    if response.status_code == 204:
        print(f"Run {run_id} deleted successfully")
    else:
        print(f"[bold red]{response.text}[/bold red]")


@run_typer.command("start")
def start_run(
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
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Building Infrastructures", total=None)
        response = clm.api_post(
            Run.start, run_id, {"instances": number_of_instances}, timeout=number_of_instances * 300.0
        )
        if response.status_code == 200:
            print(f"[bold green]{number_of_instances} Run instances has started[/bold green]")
        else:
            print(f"[bold red]{response.text}![/bold red]")


@run_typer.command("stop")
def stop_run(
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
        response = clm.api_post(Run.stop, run_id, timeout=120.0)
        if response.status_code == 200:
            print(f"[bold green]All Run instances stopped[/bold green]")
        else:
            print(f"[bold red]Run with id {run_id} ID doesn't exist![/bold red]")
