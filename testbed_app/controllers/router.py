from sqlalchemy.orm import joinedload

from testbed_app.database import session_factory

from testbed_app.models import Interface, Router
from sqlalchemy import select


async def get_infra_routers(infrastructure_id: int) -> list[Router]:
    """
    "Get all routers belonging to the Infrastructure specified by ID"
    :param infrastructure_id: Infrastructure ID
    :return: list of Router objects
    """
    async with session_factory() as session:
        routers = (
            (
                await session.scalars(
                    select(Router)
                    .where(Router.infrastructure_id == infrastructure_id)
                    .options(joinedload(Router.interfaces).subqueryload(Interface.network))
                )
            )
            .unique()
            .all()
        )
    return routers
