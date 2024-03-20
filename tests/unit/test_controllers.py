import pytest
from unittest.mock import AsyncMock, Mock, call
from dr_emu.controllers.infrastructure import InfrastructureController

import asyncio


@pytest.mark.asyncio
class TestInfrastructureController:
    path = "dr_emu.controllers.infrastructure.InfrastructureController"

    @pytest.fixture(autouse=True)
    def controller(self, mocker):
        mocker.patch("dr_emu.controllers.infrastructure.docker.from_env")
        self.controller = InfrastructureController(infrastructure=Mock(name="test_infra"))

    async def test_start(self, mocker):
        asyncio_gather_spy = mocker.spy(asyncio, "gather")
        create_networks_mock = mocker.patch(f"{self.path}.create_networks")
        create_nodes_mock = mocker.patch(f"{self.path}.create_nodes")
        start_nodes_mock = mocker.patch(f"{self.path}.start_nodes")
        start_routers_mock = mocker.patch(f"{self.path}.start_routers")
        configure_appliances_mock = mocker.patch(f"{self.path}.configure_appliances")

        await self.controller.start()

        create_networks_mock.assert_awaited_once()
        create_nodes_mock.assert_awaited_once()
        start_routers_mock.assert_awaited_once()
        start_nodes_mock.assert_awaited_once()
        configure_appliances_mock.assert_awaited_once()
        assert asyncio_gather_spy.call_count == 4

    async def test_stop(self, mocker):

        asyncio_gather_spy = mocker.spy(asyncio, "gather")
        mocker.patch(f"{self.path}.delete_nodes", return_value=set(AsyncMock()))
        mocker.patch(f"{self.path}.delete_routers", return_value=set(AsyncMock()))
        mocker.patch(f"{self.path}.delete_networks", return_value=set(AsyncMock()))

        await self.controller.stop()

        assert asyncio_gather_spy.call_count == 2
