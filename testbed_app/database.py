from __future__ import annotations

from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from os import getenv
from pathlib import Path

from testbed_app.models import Base

BASE_DIR = Path(__file__).parent.parent.parent

DB_USER = getenv("POSTGRES_USER", "postgres")
DB_PASS = getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = getenv("DB_HOST", "localhost")
DB_NAME = getenv("POSTGRES_DB", "postgres")

async_engine = create_async_engine(
    url=f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}",
    future=True,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=5,
    max_overflow=2,
    echo=False,
)

session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


async def create_db():
    """
    Create database tables
    :return: None
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def destroy_db():
    """
    Drop database tables
    :return:
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
