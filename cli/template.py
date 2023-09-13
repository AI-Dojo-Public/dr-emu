from cli import UTyper
import typer
from typing_extensions import Annotated

from testbed_app.controllers import template as template_controller

template_typer = UTyper()


@template_typer.command("create")
async def create_template(
    name: Annotated[
        str,
        typer.Argument(help="Name of the prefabricated infrastructure description"),
    ],
    infra_description: Annotated[
        str,
        typer.Argument(help="Path to a file with cyst infrastructure description"),
    ],
):
    """
    Create Template.
    """
    prefab = await template_controller.create_template(name, infra_description)
    print(f"Infrastructure description with name: {prefab.name} and id: {prefab.id} has been created")


@template_typer.command("list")
async def list_templates():
    """
    List all Templates.
    """
    templates = await template_controller.list_templates()

    if templates:
        for template in templates:
            print(
                f"name: {template.name}, id: {template.id}, run id:",
            )
    else:
        print("No templates have been created yet")


@template_typer.command("delete")
async def delete_template(
    template_id: Annotated[
        int,
        typer.Argument(help="Id of an prefab that should be deleted"),
    ],
):
    """
    Delete Template based on the provided ID.
    """
    template = await template_controller.delete_template(template_id)
    print(f"Template with name: {template.name} and id: {template.id} has been deleted")
