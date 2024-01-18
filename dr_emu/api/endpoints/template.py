from fastapi import APIRouter, status, Response
from sqlalchemy.exc import NoResultFound

from dr_emu.api.dependencies.core import DBSession
from dr_emu.api.helpers import nonexistent_object_msg
from dr_emu.controllers import template as template_controller
from dr_emu.schemas.template import TemplateSchema, TemplateOut

router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
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
        response.status_code = status.HTTP_404_NOT_FOUND
        return nonexistent_object_msg("Template", template_id)


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
