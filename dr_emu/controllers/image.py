import asyncio
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dr_emu.lib.logger import logger
from dr_emu.models import Image, ImageState

# TODO:
# async def create_image(name: str, services: list[dict[str, str]], db_session: AsyncSession) -> Image:
#     """
#     Create Image and save it to DB.
#     :param name: Image name
#     :param db_session: Async database session
#     :param services: Services installed in Docker Image
#     :return: created Image
#     """
# logger.debug("Creating image", name=name)
# image = Image(name=name, services=services)
# db_session.add(image)
# await db_session.commit()
#
# logger.info("Image created", id=image.id, name=image.name, services=image.services)
# return image
# return NotImplemented


async def list_images(db_session: AsyncSession) -> Sequence[Image]:
    """
    List all images saved in DB.
    :param db_session: Async database session
    :return: list of images
    """
    logger.debug("Listing images")

    images = (await db_session.scalars(select(Image).options(joinedload(Image.services)))).unique().all()

    return images


async def delete_image(image_id: int, db_session: AsyncSession) -> Image:
    """
    Delete Image specified by ID from DB.
    :param image_id: Image ID
    :param db_session: Async database session
    :return: deleted Image object.
    :raises: sqlalchemy.exc.NoResultFound
    """
    logger.debug("Deleting image", id=image_id)

    image = (await db_session.execute(select(Image).where(Image.id == image_id))).scalar_one()
    await db_session.delete(image)
    await db_session.commit()

    logger.debug("Image deleted", id=image.id, name=image.name)
    return image


async def get_image(image_id: int, db_session: AsyncSession) -> Image:
    """
    List all images saved in DB.
    :param db_session: Async database session
    :param image_id: Image ID
    :return: list of images
    """
    image = (await db_session.execute(
        select(Image).where(Image.id == image_id).options(joinedload(Image.services)))).unique().scalar_one()

    return image


async def wait_until_image_is_ready(image: Image, db_session: AsyncSession):
    while True:
        # Get the current in-memory value of the attribute
        logger.debug(f"Waiting for Image to be ready", id=image.id, current_state=image.state)
        await db_session.refresh(image)
        if image.state == ImageState.ready:
            break
        await asyncio.sleep(5)
