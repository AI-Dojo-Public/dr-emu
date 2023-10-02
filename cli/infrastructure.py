import json
import typer
import asyncio
from typing_extensions import Annotated
from typing import List, Optional

from testbed_app.controllers.infrastructure import InfrastructureController
from rich.progress import Progress, SpinnerColumn, TextColumn

from cli import UTyper

infras_typer = UTyper()


@infras_typer.command("delete")
async def delete(
    infrastructure_ids: Annotated[
        Optional[List[int]],
        typer.Argument(help="IDs of infrastructures to be deleted. eg. 1 2 3"),
    ] = None
):
    """
    When no infrastructure ids are specified, all infrastructures will be deleted.
    """
    infrastructure_ids = (
        infrastructure_ids if infrastructure_ids else list(await InfrastructureController.list_infrastructures().keys())
    )
    delete_tasks = set()

    for infra_id in infrastructure_ids:
        infra = await InfrastructureController.get_infra(infra_id)
        delete_tasks.add(asyncio.create_task(InfrastructureController.stop_infra(infra)))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Deleting Infrastructures", total=None)
        await asyncio.gather(*delete_tasks)

    print("All Infrastructures deleted.")


@infras_typer.command("list")
async def list_ids():
    """
    List infrastructures id:name key values.
    """
    print({"infrastructures": await InfrastructureController.list_infrastructures()})


@infras_typer.command("get")
async def get(
    infrastructure_ids: Annotated[
        Optional[List[int]],
        typer.Argument(help="Get details about infrastructures specified by id. eg. 1 2 3"),
    ] = None
):
    """
    Get infrastructure details.
    When no infrastructure ids are specified, details about all infrastructures will be displayed.
    """
    get_tasks = set()

    infrastructure_ids = (
        infrastructure_ids if infrastructure_ids else await InfrastructureController.list_infrastructures()
    )

    for infra_id in infrastructure_ids:
        get_tasks.add(asyncio.create_task(InfrastructureController.get_infra_info(infra_id)))
        print(json.dumps(await asyncio.gather(*get_tasks), indent=4))
