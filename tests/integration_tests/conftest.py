import asyncio
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient

from dr_emu.app import app as actual_app
from dr_emu.database_config import get_db_session, sessionmanager
from dr_emu.models import Base


@pytest.fixture(autouse=True)
def app():
    with ExitStack():
        yield actual_app


@pytest.fixture()
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def create_tables():
    sessionmanager.init({"url": "sqlite+aiosqlite:///test.db"})
    async with sessionmanager.connect() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    sessionmanager.close()


@pytest.fixture(scope="function", autouse=True)
async def session_override(app):
    async def get_db_override():
        async with sessionmanager.session() as session:
            yield session

    app.dependency_overrides[get_db_session] = get_db_override

