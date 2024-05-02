from typing import List

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Annotated

from cli.config.config import clm
from shared.endpoints import Run
from shared import constants
from dr_emu.schemas.run import Run as RunSchema


run_typer = typer.Typer(no_args_is_help=True)


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
):
    """
    Create Run.
    """
    response = clm.api_post(
        Run.create,
        data=RunSchema(name=name, template_id=template_id).model_dump_json(),
    )
    clm.print_non_get_message(response, constants.RUN, 201)


@run_typer.command("list")
def list_runs():
    """
    List all Runs.
    """
    response = clm.api_get(Run.list)
    clm.print_get_message(response)


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
    clm.print_non_get_message(response, constants.RUN, 204, run_id)


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
    clm.print_non_get_message(response, constants.RUN, 200, run_id, "started")


@run_typer.command("stop")
def stop_run(
    run_id: Annotated[
        int,
        typer.Argument(help="Id of Run that should be stopped"),
    ]
):
    """
    Stop all running instances of specified Run.
    """

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Deleting Instances", total=None)
        response = clm.api_post(Run.stop, run_id, timeout=120.0)
    clm.print_non_get_message(response, constants.RUN, 200, run_id, "stopped")
