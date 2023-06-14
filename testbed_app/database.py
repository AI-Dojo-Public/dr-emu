from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from os import getenv
from pathlib import Path
from netaddr import IPAddress, IPNetwork

from testbed_app.models import Base
from testbed_app.models import Network, Router, Service, Interface, Node
from docker_testbed.util import constants

BASE_DIR = Path(__file__).parent.parent.parent

DB_USER = getenv("POSTGRES_USER", "postgres")
DB_PASS = getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = getenv("POSTGRES_HOST", "localhost")
DB_NAME = getenv("POSTGRES_DB", "postgres")

async_engine = create_async_engine(
    f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
)

session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


async def create_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def destroy_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
