import typer
from rich import print
from rich.console import Console
from typer import Typer
from typing_extensions import Annotated

from cli.config.config import clm
from cli.config.endpoints import Template
from dr_emu.schemas.template import TemplateSchema

template_typer = Typer()
console = Console()


@template_typer.command("create")
def create_template(
    name: Annotated[
        str,
        typer.Argument(help="Name of the prefabricated infrastructure description"),
    ],
    infra_description: Annotated[
        str,
        typer.Argument(help="Path to a file with cyst infrastructure description"),
    ],
):
    r = clm.api_post(
        endpoint_url=Template.create, data=TemplateSchema(name=name, description=infra_description).model_dump_json()
    )
    if r.status_code == 201:
        print(f"Template created successfully")
        print(r.json())
    else:
        print(r.text)


@template_typer.command("list")
def list_templates():
    """
    List all Templates.
    """
    result = clm.api_get_data(endpoint_url=Template.list)
    console.print(result)


@template_typer.command("delete")
def delete_template(
    template_id: Annotated[
        int,
        typer.Argument(help="Id of an prefab that should be deleted"),
    ],
):
    """
    Delete Template based on the provided ID.
    """

    response = clm.api_delete(endpoint_url=Template.list, object_id=template_id)
    if response.status_code == 204:
        print(f"Template with id: {template_id} has been deleted")
    else:
        print(response.text)
