import json
from functools import wraps

import typer
import asyncio
import inspect

from overrides import override
from typing_extensions import Annotated
from typing import List, Optional

from testbed_app import infrastructure_util
from rich.progress import Progress, SpinnerColumn, TextColumn


class UTyper(typer.Typer):
    # https://github.com/tiangolo/typer/issues/88
    @override
    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)

        def add_runner(f):
            if inspect.iscoroutinefunction(f):

                @wraps(f)
                def runner(*args, **kwargs):
                    return asyncio.run(f(*args, **kwargs))

                decorator(runner)
            else:
                decorator(f)
            return f

        return add_runner


app = UTyper()
infras_typer = UTyper()
app.add_typer(infras_typer, name="infrastructures")


@infras_typer.command("create")
async def infrastructures_create(
    number_of_infrastructures: Annotated[
        int,
        typer.Argument(help="Number of infrastructure copies that should be created"),
    ]
):
    """
    Create the specified number of infrastructures.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Building Infrastructures", total=None)
        await infrastructure_util.build_infras(number_of_infrastructures)
    print("Infrastructures created")


@infras_typer.command("delete")
async def infrastructures_delete(
    infrastructure_ids: Annotated[
        Optional[List[int]],
        typer.Argument(help="Delete infrastructures specified by id. eg. 1 2 3"),
    ] = None
):
    """
    When no infrastructure ids are specified, all infrastructures will be deleted.
    """
    infrastructure_ids = (
        infrastructure_ids
        if infrastructure_ids
        else await infrastructure_util.get_infra_ids()
    )
    delete_tasks = set()

    for infra_id in infrastructure_ids:
        delete_tasks.add(
            asyncio.create_task(infrastructure_util.destroy_infra(infra_id))
        )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Deleting Infrastructures", total=None)
        await asyncio.gather(*delete_tasks)

    print("All Infrastructures deleted.")


@infras_typer.command("list")
async def infrastructures_list_ids():
    """
    List infrastructure IDs.
    """
    print({"infrastructure_ids": await infrastructure_util.get_infra_ids()})


@infras_typer.command("get")
async def infrastructures_info(
    infrastructure_ids: Annotated[
        Optional[List[int]],
        typer.Argument(
            help="Get details about infrastructures specified by id. eg. 1 2 3"
        ),
    ] = None
):
    """
    Get infrastructure details.
    When no infrastructure ids are specified, details about all infrastructures will be displayed.
    """
    get_tasks = set()

    infrastructure_ids = (
        infrastructure_ids
        if infrastructure_ids
        else await infrastructure_util.get_infra_ids()
    )

    for infra_id in infrastructure_ids:
        get_tasks.add(asyncio.create_task(infrastructure_util.get_infra(infra_id)))

        print(json.dumps(await asyncio.gather(*get_tasks), indent=4))


if __name__ == "__main__":
    app()
