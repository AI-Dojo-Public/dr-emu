from typing import Annotated

from dr_emu.database_config import get_db_session
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
