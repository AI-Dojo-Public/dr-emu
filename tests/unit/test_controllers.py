from unittest.mock import call, Mock, MagicMock
import pytest
from unittest.mock import AsyncMock, Mock, call, patch

from shared import constants
from dr_emu.controllers.infrastructure import InfrastructureController
from netaddr import IPNetwork, IPAddress

import asyncio

from dr_emu.models import Infrastructure, Network, Interface, Router


@pytest.mark.asyncio
class TestInfrastructureController:
    file_path = "dr_emu.controllers.infrastructure"
    controller_path = f"{file_path}.InfrastructureController"

    @pytest.fixture()
    def interface(self):
        interface = Mock(spec=Interface)
        interface.configure_mock(networks=Mock(), appliance=Mock(type="router"))
        return interface

    @pytest.fixture()
    def network(self, interface):
        network = Mock(spec=Network)
        network.configure_mock(
            interfaces=[interface], router_gateway=IPAddress("127.0.0.1"), ipaddress=IPNetwork("127.0.0.0/24")
        )
        interface.network = network
        return network

    @pytest.fixture()
    def infrastructure(self, network):
        infra = Mock(spec=Infrastructure)
        infra.configure_mock(name="test_infra", networks=[network])
        return infra

    @pytest.fixture(autouse=True)
    def controller(self, mocker, infrastructure):
        mocker.patch(f"{self.file_path}.docker.from_env")
        self.controller = InfrastructureController(infrastructure=infrastructure)

    async def test_start(self, mocker):
        asyncio_gather_spy = mocker.spy(asyncio, "gather")
        create_networks_mock = mocker.patch(f"{self.controller_path}.create_networks")
        create_nodes_mock = mocker.patch(f"{self.controller_path}.create_nodes")
        start_nodes_mock = mocker.patch(f"{self.controller_path}.start_nodes")
        start_routers_mock = mocker.patch(f"{self.controller_path}.start_routers")
        configure_appliances_mock = mocker.patch(f"{self.controller_path}.configure_appliances")

        await self.controller.start()

        create_networks_mock.assert_awaited_once()
        create_nodes_mock.assert_awaited_once()
        start_routers_mock.assert_awaited_once()
        start_nodes_mock.assert_awaited_once()
        configure_appliances_mock.assert_awaited_once()
        assert asyncio_gather_spy.call_count == 4

    async def test_stop(self, mocker):
        asyncio_gather_spy = mocker.spy(asyncio, "gather")
        mocker.patch(f"{self.controller_path}.delete_nodes", return_value=set(AsyncMock()))
        mocker.patch(f"{self.controller_path}.delete_routers", return_value=set(AsyncMock()))
        mocker.patch(f"{self.controller_path}.delete_networks", return_value=set(AsyncMock()))

        await self.controller.stop()

        assert asyncio_gather_spy.call_count == 2

    async def test_change_ipaddresses(self, infrastructure, network):
        network.name = "testing"
        await self.controller.change_ipaddresses([IPNetwork("127.0.1.0/24")])
        interface = network.interfaces[0]
        assert network.ipaddress == IPNetwork("127.0.1.0/24")
        assert interface.ipaddress == IPAddress("127.0.1.1")
        assert network.router_gateway == IPAddress("127.0.1.1")

    async def test_create_management_network(self, mocker):
        network_ip = IPNetwork("127.0.0.0/24")
        perimeter_router_mock = Mock(router_type=constants.ROUTER_TYPE_PERIMETER, interfaces=[])
        internal_router_mock = Mock(router_type=constants.ROUTER_TYPE_INTERNAL, interfaces=[])
        self.controller.infrastructure.routers = [perimeter_router_mock, internal_router_mock]

        get_network_names_mock = mocker.patch(f"{self.file_path}.util.get_network_names")
        mocker.patch(f"{self.file_path}.randomname.generate", return_value="network_name")

        network = Mock(spec=Network)
        network.configure_mock(ipaddress=network_ip)
        network_mock = mocker.patch(f"{self.file_path}.Network", return_value=network)

        interface_mock: Mock = mocker.patch(f"{self.file_path}.Interface")

        await self.controller.create_management_network(network_ip)

        get_network_names_mock.assert_awaited_once()
        network_mock.assert_called_once_with(
            ipaddress=network_ip,
            router_gateway=IPAddress("127.0.0.1"),
            name="network_name",
            network_type="management",
        )

        calls = [
            call(ipaddress=network.router_gateway, network=network),
            call(ipaddress=network_ip[3], network=network),
        ]
        interface_mock.assert_has_calls(calls)
        assert network in self.controller.infrastructure.networks
        assert len(perimeter_router_mock.interfaces) == 1
        assert len(internal_router_mock.interfaces) == 1

    async def test_prepare_controller_for_infra_creation(self, infrastructure, mocker, network):
        available_networks = [IPNetwork("127.0.1.0/24")]
        infra_controller_mock = mocker.patch(self.controller_path, return_value=AsyncMock()).return_value
        infrastructure.networks = [network]
        infra_controller_mock.infrastructure = infrastructure

        create_management_network_mock = mocker.patch.object(infra_controller_mock, "create_management_network")
        change_ipaddresses_mock = mocker.patch.object(infra_controller_mock, "change_ipaddresses")
        infra_controller = await InfrastructureController.prepare_controller_for_infra_creation(
            infrastructure=infrastructure, available_networks=available_networks
        )

        change_ipaddresses_mock.assert_awaited_once_with(available_networks)
        create_management_network_mock.assert_awaited_once_with(IPNetwork("127.0.1.0/24"))
        assert infra_controller == infra_controller_mock

    async def test_create_controller(self, mocker):
        cyst_parser_mock = AsyncMock()
        networks = [Mock()]
        routers = [Mock()]
        nodes = [Mock()]
        bake_models_mock = mocker.patch.object(cyst_parser_mock, "bake_models", return_value=(networks, routers, nodes))
        generate_infrastructure_subnets_mock = mocker.patch(
            f"{self.file_path}.util.generate_infrastructure_subnets"
        )

        infrastructure_mock = mocker.patch(f"{self.file_path}.Infrastructure")
        controller_mock = AsyncMock()
        prepare_controller_mock = mocker.patch(
            f"{self.controller_path}.prepare_controller_for_infra_creation",
            return_value=controller_mock,
        )
        change_names_mock = mocker.patch.object(controller_mock, "change_names")

        infrastructure_supernet = IPNetwork("127.0.0.0/16")
        docker_container_names = {"container_name"}
        docker_network_names = {"network_name"}
        infra_name = "test_infra"

        controller_result = await InfrastructureController.create_controller(
            infrastructure_supernet,
            cyst_parser_mock,
            docker_container_names,
            docker_network_names,
            infra_name,
        )
        bake_models_mock.assert_awaited_once()
        infrastructure_mock.assert_called_once_with(
            routers=routers,
            nodes=nodes,
            networks=networks,
            name=infra_name,
            supernet=IPNetwork("127.0.0.0/16")
        )
        prepare_controller_mock.assert_called_once_with(
            available_networks=generate_infrastructure_subnets_mock.return_value,
            infrastructure=infrastructure_mock.return_value,
        )
        change_names_mock.assert_awaited_once_with(
            container_names=docker_container_names, network_names=docker_network_names
        )
        generate_infrastructure_subnets_mock.assert_awaited_once_with(
            infrastructure_supernet, list(cyst_parser_mock.network_ips)
        )
        assert controller_result == controller_mock

    async def test_build_infras(self, mocker):
        available_infra_supernets = [
            IPNetwork("127.1.0.0/16"),
            IPNetwork("127.2.1.0/16"),
        ]
        db_session = AsyncMock()
        run_mock = AsyncMock()
        mocker.patch(f"{self.file_path}.template_controller.get_template")
        docker_client_mock = mocker.patch(f"{self.file_path}.docker.from_env").return_value
        get_container_names_mock = mocker.patch(f"{self.file_path}.util.get_container_names")
        get_network_names_mock = mocker.patch(f"{self.file_path}.util.get_network_names")
        get_available_networks_for_infras_mock = mocker.patch(
            f"{self.file_path}.util.get_available_networks_for_infras",
            return_value=available_infra_supernets,
        )
        pull_images_mock = mocker.patch(f"{self.file_path}.util.pull_images")

        controller_mock = AsyncMock()
        create_controller_mock = mocker.patch(f"{self.controller_path}.create_controller", return_value=controller_mock)


        cyst_parser_mock = mocker.patch(f"{self.file_path}.CYSTParser", return_value=AsyncMock(networks_ips=["test"]))

        mocker.patch.object(cyst_parser_mock, "parse")
        scalar_mock = MagicMock()
        mocker.patch.object(db_session, "scalars", return_value=scalar_mock)
        mocker.patch.object(scalar_mock, "all", return_value=[])
        mocker.patch(f"{self.file_path}.randomname.generate", side_effect=["first_infra", "second_infra"])

        await self.controller.build_infras(2, run_mock, db_session)

        get_container_names_mock.assert_awaited_once_with(docker_client_mock)
        get_network_names_mock.assert_awaited_once_with(docker_client_mock)
        get_available_networks_for_infras_mock.assert_awaited_once_with(
            docker_client_mock, 2, set()
        )
        pull_images_mock.assert_awaited_once_with(docker_client_mock, cyst_parser_mock.return_value.docker_images)
        # get_template_mock.assert_awaited_once_with(run_mock.template_id, db_session)

        calls = [
            call(
                available_infra_supernets[0],
                cyst_parser_mock.return_value,
                get_container_names_mock.return_value,
                get_network_names_mock.return_value,
                "first_infra",
            ),
            call(
                available_infra_supernets[1],
                cyst_parser_mock.return_value,
                get_container_names_mock.return_value,
                get_network_names_mock.return_value,
                "second_infra",
            ),
        ]
        create_controller_mock.assert_has_calls(calls)

    async def test_build_infrastructure_exception(self, mocker, infrastructure):
        instance_mock = mocker.patch(f"{self.file_path}.Instance")
        run_mock = Mock()
        start_mock = mocker.patch.object(self.controller, "start", side_effect=Exception)
        stop_mock = mocker.patch.object(self.controller, "stop")

        with pytest.raises(Exception):
            await self.controller.build_infrastructure(run_mock)

        instance_mock.assert_called_once_with(
            run=run_mock, infrastructure=infrastructure
        )
        start_mock.assert_called_once()
        stop_mock.assert_called_once()
