import typer
from rich.console import Console
from typer import Typer
from typing_extensions import Annotated

from cli.config.config import clm
from shared import constants
from shared.endpoints import Template
from dr_emu.schemas.template import TemplateSchema

template_typer = Typer(no_args_is_help=True)
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
    response = clm.api_post(
        endpoint_url=Template.create, data=TemplateSchema(name=name, description=infra_description).model_dump_json()
    )
    clm.print_non_get_message(response, constants.TEMPLATE, 201)


@template_typer.command("list")
def list_templates():
    """
    List all Templates.
    """
    result = clm.api_get(endpoint_url=Template.list)
    clm.print_get_message(result)


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

    response = clm.api_delete(endpoint_url=Template.delete, object_id=template_id)
    clm.print_non_get_message(response, constants.TEMPLATE, 204, template_id)
