from sqlalchemy import select

from testbed_app.database import session_factory
from testbed_app.models import Template


async def create_template(name: str, infra_description: str) -> Template:
    """
    Create Template and save it to DB.
    :param name: Template name
    :param infra_description: Infrastructure description (serialized cyst infra description)
    :return: created Template
    """
    async with session_factory() as session:
        template = Template(name=name, description=infra_description)
        session.add(template)
        await session.commit()

    return template


async def list_templates() -> list[Template]:
    """
    List all Templates saved in DB.
    :return: list of Templates
    """
    async with session_factory() as session:
        templates = (await session.scalars(select(Template))).all()

    return templates


async def delete_template(template_id: int) -> Template:
    """
    Delete Template specified by ID from DB.
    :param template_id: Template ID
    :return: deleted Template object.
    """
    async with session_factory() as session:
        template = (await session.execute(select(Template).where(Template.id == template_id))).scalar_one()
        await session.delete(template)
        await session.commit()

    return template
