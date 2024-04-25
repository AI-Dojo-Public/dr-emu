from fastapi import APIRouter, status, Response, HTTPException
from sqlalchemy.exc import NoResultFound

from shared import constants
from dr_emu.api.dependencies.core import DBSession
from dr_emu.api.helpers import nonexistent_object_msg
from dr_emu.controllers import template as template_controller
from dr_emu.schemas.template import TemplateSchema, TemplateOut

router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    responses={404: {"description": "Not found"}},
)


template_create_description = """
Create infrastructure template

## Subnet mask restriction
Individual networks in infrastructure configuration have to have their subnet mask greater than 16 so that total number 
of networks in infrastructure can be fitted in **10.x.0.0/16** subnet.

eg. Infrastructure configuration can have maximum of 256 networks with subnet mask of 24 
**(10.0.0.0/24 - 10.0.255.0/24)**
"""


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    description=template_create_description,
    responses={201: {"description": "Object successfully created"}},
    response_model=TemplateOut,
)
async def create_template(template: TemplateSchema, session: DBSession):
    """
    responses:
      201:
        description: Template was created
    """

    template = await template_controller.create_template(template.name, template.description, session)
    return TemplateOut(id=template.id, name=template.name, description=template.description)


@router.delete(
    "/delete/{template_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Object successfully deleted"}},
)
async def delete_template(template_id: int, session: DBSession, response: Response):
    """
    responses:
      204:
        description: Template was deleted
      404:
        description: Template with specified id does not exist
    """
    try:
        await template_controller.delete_template(template_id, session)
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.TEMPLATE, template_id)
        )


@router.get("/", response_model=list[TemplateOut])
async def list_templates(session: DBSession):
    """
    responses:
      200:
        description: List templates
    """
    templates = await template_controller.list_templates(session)

    response = []
    for template in templates:
        response.append(TemplateOut(name=template.name, id=template.id, description=template.description))

    return response
