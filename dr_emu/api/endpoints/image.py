from fastapi import APIRouter, status, Response, HTTPException
from sqlalchemy.exc import NoResultFound

from shared import constants
from dr_emu.api.dependencies.core import DBSession
from dr_emu.api.helpers import nonexistent_object_msg
from dr_emu.controllers import image as image_controller
from dr_emu.schemas.image import ImageSchema, ImageOut, Service

router = APIRouter(
    prefix="/images",
    tags=["images"],
    responses={404: {"description": "Not found"}},
)


image_create_description = """
Create docker image
"""


@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    description=image_create_description,
    responses={201: {"description": "Object successfully created"}},
    response_model=ImageOut,
)
async def create_image(image_schema: ImageSchema, session: DBSession):
    """
    responses:
      201:
        description: image was created
    """

    image = await image_controller.create_image(image_schema.name, [dict(service) for service in image_schema.services], session)
    return ImageOut(id=image.id, name=image.name, services=image.services)


@router.delete(
    "/delete/{image_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Object successfully deleted"}},
)
async def delete_image(image_id: int, session: DBSession, response: Response):
    """
    responses:
      204:
        description: image was deleted
      404:
        description: image with specified id does not exist
    """
    try:
        await image_controller.delete_image(image_id, session)
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=nonexistent_object_msg(constants.IMAGE, image_id)
        )


@router.get("/", response_model=list[ImageOut])
async def list_images(session: DBSession):
    """
    responses:
      200:
        description: List images
    """

    images = await image_controller.list_images(session)
    image_data = []
    for image in images:
        image_dict = ImageOut(
            name=image.name,
            id=image.id,
            pull=image.pull,
            services=[
                Service(
                    type=service.type,
                    version=service.version,
                    cves=service.cves,
                )
                for service in image.services
            ],
            packages=image.packages
        )
        image_data.append(image_dict)

    return image_data
