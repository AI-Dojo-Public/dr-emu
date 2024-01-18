from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dr_emu.lib.logger import logger
from dr_emu.models import Template
from dr_emu.schemas.template import TemplateOut


async def create_template(name: str, infra_description: str, db_session: AsyncSession) -> Template:
    """
    Create Template and save it to DB.
    :param name: Template name
    :param db_session: Async database session
    :param infra_description: Infrastructure description (serialized cyst infra description)
    :return: created Template
    """
    logger.debug("Creating template", name=name)
    template = Template(name=name, description=infra_description)
    db_session.add(template)
    await db_session.commit()

    logger.info("Template created", id=template.id, name=template.name)
    return template


async def list_templates(db_session: AsyncSession) -> Sequence[Template]:
    """
    List all Templates saved in DB.
    :param db_session: Async database session
    :return: list of Templates
    """
    logger.debug("Listing templates")

    templates = (await db_session.scalars(select(Template))).all()

    return templates


async def delete_template(template_id: int, db_session: AsyncSession) -> Template:
    """
    Delete Template specified by ID from DB.
    :param template_id: Template ID
    :param db_session: Async database session
    :return: deleted Template object.
    :raises: sqlalchemy.exc.NoResultFound
    """
    logger.debug("Deleting template", id=template_id)

    template = (await db_session.execute(select(Template).where(Template.id == template_id))).scalar_one()
    await db_session.delete(template)
    await db_session.commit()

    logger.debug("Template deleted", id=template.id, name=template.name)
    return template
