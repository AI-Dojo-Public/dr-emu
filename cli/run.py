from cli import UTyper
import typer
from typing_extensions import Annotated
from typing import List

from testbed_app.controllers import run as run_controller


run_typer = UTyper()


@run_typer.command("create")
async def create_run(
    name: Annotated[
        str,
        typer.Argument(help="Name of the Run"),
    ],
    prefab_id: Annotated[
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
    :return:
    """
    run = await run_controller.create_run(name=name, agent_ids=agent_ids, template_id=prefab_id)

    print(f"Run with name: {run.name} and id: {run.id} has been created")


@run_typer.command("list")
async def list_runs():
    """
    List all Runs.
    :return:
    """
    runs = await run_controller.list_runs()

    if runs:
        for run in runs:
            print(
                f"name: {run.name}, id: {run.id}, template_id: {run.template_id}",
            )
    else:
        print("No runs have been created yet")


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
    print(f"Run with name: {run.name} and id: {run.id} has been deleted")
