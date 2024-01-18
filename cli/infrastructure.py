import typer
from typing_extensions import Annotated

from rich.progress import Progress, SpinnerColumn, TextColumn
from cli.config.config import clm
from cli.config.endpoints import Infrastructure

infras_typer = typer.Typer()


@infras_typer.command("delete")
def delete(
    infrastructure_id: Annotated[
        int,
        typer.Argument(help="ID of the infrastructure to be deleted."),
    ] = None
):
    """
    When no infrastructure ids are specified, all infrastructures will be deleted.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Deleting Instances", total=None)
        response = clm.api_delete(Infrastructure.delete, infrastructure_id, timeout=120.0)
        if response.status_code == 204:
            print(f"[bold green]Infrastructure with id: {infrastructure_id} has been deleted[/bold green]")
        else:
            print(f"[bold red]{response.text}[/bold red]")

    print("All Infrastructures deleted.")


@infras_typer.command("list")
def list_infras():
    """
    List infrastructures id:name key values.
    """
    print(clm.api_get_data(Infrastructure.list))


@infras_typer.command("get")
async def get(
    infrastructure_id: Annotated[
        int,
        typer.Argument(help="Get details about infrastructure specified by id"),
    ] = None
):
    """
    Get infrastructure details.
    When no infrastructure ids are specified, details about all infrastructures will be displayed.
    """

    print(clm.api_get(Infrastructure.get, infrastructure_id))
