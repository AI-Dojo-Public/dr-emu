from __future__ import annotations

import contextlib
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncConnection,
    AsyncEngine,
)
from sqlalchemy.orm import declarative_base

from dr_emu.settings import settings

BASE_DIR = Path(__file__).parent.parent.parent

async_engine = create_async_engine(
    url=f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.db_host}/"
    f"{settings.postgres_db}",
    future=True,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=5,
    max_overflow=2,
    echo=False,
)

# Source: https://praciano.com.br/fastapi-and-async-sqlalchemy-20-with-pytest-done-right.html
Base = declarative_base()


class DatabaseSessionManager:
    def __init__(self, engine=None):
        self._engine: AsyncEngine | None = engine
        self._sessionmaker: async_sessionmaker = async_sessionmaker(
            autocommit=False, bind=self._engine, expire_on_commit=False
        )

    # For testing
    def init(self, config: dict):
        self._engine = create_async_engine(**config)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine, expire_on_commit=False)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Used for testing
    @staticmethod
    async def create_all(connection: AsyncConnection):
        await connection.run_sync(Base.metadata.create_all)

    @staticmethod
    async def drop_all(connection: AsyncConnection):
        await connection.run_sync(Base.metadata.drop_all)


sessionmanager = DatabaseSessionManager(async_engine)


async def get_db_session():
    async with sessionmanager.session() as session:
        yield session
