from fastapi import APIRouter
from sqlalchemy.exc import NoResultFound

from testbed_app.controllers.infrastructure import InfrastructureController
from testbed_app.controllers import template as template_controller
from pydantic import BaseModel


router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    responses={404: {"description": "Not found"}},
)


class Template(BaseModel):
    name: str
    description: str


@router.post("/create/")
async def create_template(template: Template):
    """
    responses:
      200:
        description: Builds docker infrastructure
    """

    await template_controller.create_template(template.name, template.description)
    return {"message": f"Template {template.name} has been created"}


@router.get("/delete/{run_id}")
async def delete_template(template_id: int):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    try:
        await template_controller.delete_template(template_id)
    except NoResultFound:
        return {"message": f"Run with id {template_id} ID doesn't exist!"}

    return {"message": f"Template {template_id} has been deleted"}


@router.get("/")
async def list_templates():
    templates = await template_controller.list_templates()
    if templates:
        response = {"message": []}
        for template in templates:
            response["message"].append({"name": template.name, "id": template.id})
        return response
    else:
        return {"message": "No templates have been created yet"}
