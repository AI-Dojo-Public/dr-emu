from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from testbed_app.database_config import session_factory
from testbed_app.lib.logger import logger

from testbed_app.models import Interface, Router
from sqlalchemy import select


async def get_infra_routers(infrastructure_id: int, db_session: Optional[AsyncSession] = None) -> list[Router]:
    """
    "Get all routers belonging to the Infrastructure specified by ID"
    :param db_session: SQLAlchemy async db session
    :param infrastructure_id: Infrastructure ID
    :return: list of Router objects
    """
    logger.debug("Pulling routers from DB", infrastructure_id=infrastructure_id)
    if db_session:
        routers = (
            (
                await db_session.scalars(
                    select(Router)
                    .where(Router.infrastructure_id == infrastructure_id)
                    .options(joinedload(Router.interfaces).subqueryload(Interface.network))
                )
            )
            .unique()
            .all()
        )
    else:
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
