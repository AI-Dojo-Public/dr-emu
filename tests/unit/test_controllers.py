import asyncio
from unittest.mock import AsyncMock, Mock, call
from unittest.mock import MagicMock

import pytest
from netaddr import IPNetwork, IPAddress
from pytest_mock import MockerFixture

from dr_emu.controllers.infrastructure import InfrastructureController
from dr_emu.models import Infrastructure, Network, Interface, ImageState
from shared import constants


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
    def network(self, interface: Mock):
        network = Mock(spec=Network)
        network.configure_mock(
            interfaces=[interface], router_gateway=IPAddress("127.0.0.1"), ipaddress=IPNetwork("127.0.0.0/24")
        )
        interface.network = network
        return network

    @pytest.fixture()
    def infrastructure(self, network: Mock):
        infra = Mock(spec=Infrastructure)
        infra.configure_mock(name="test_infra", networks=[network], volumes={AsyncMock()})
        return infra

    @pytest.fixture(autouse=True)
    def controller(self, mocker: MockerFixture, infrastructure: Mock):
        mocker.patch(f"{self.file_path}.docker.from_env")
        self.controller = InfrastructureController(infrastructure=infrastructure)

    async def test_start(self, mocker: MockerFixture):
        asyncio_gather_spy = mocker.spy(asyncio, "gather")
        create_networks_mock = mocker.patch(f"{self.controller_path}.create_networks")
        create_nodes_mock = mocker.patch(f"{self.controller_path}.create_nodes")
        create_volumes_mock = mocker.patch(f"{self.controller_path}.create_volumes")
        start_nodes_mock = mocker.patch(f"{self.controller_path}.start_nodes")
        start_routers_mock = mocker.patch(f"{self.controller_path}.start_routers")
        configure_appliances_mock = mocker.patch(f"{self.controller_path}.configure_appliances")

        await self.controller.start()

        create_networks_mock.assert_awaited_once()
        create_nodes_mock.assert_awaited_once()
        start_routers_mock.assert_awaited_once()
        create_volumes_mock.assert_awaited_once()
        start_nodes_mock.assert_awaited_once()
        configure_appliances_mock.assert_awaited_once()
        assert asyncio_gather_spy.call_count == 5

    async def test_stop(self, mocker: MockerFixture):
        asyncio_gather_spy = mocker.spy(asyncio, "gather")
        mocker.patch(f"{self.controller_path}.delete_nodes", return_value=set(AsyncMock()))
        mocker.patch(f"{self.controller_path}.delete_volumes", return_value=set(AsyncMock()))
        mocker.patch(f"{self.controller_path}.delete_routers", return_value=set(AsyncMock()))
        mocker.patch(f"{self.controller_path}.delete_networks", return_value=set(AsyncMock()))

        await self.controller.stop()

        assert asyncio_gather_spy.call_count == 3

    async def test_change_ipaddresses(self, infrastructure: Mock, network: Mock):
        network.name = "testing"
        await self.controller.change_ipaddresses([IPNetwork("127.0.1.0/24")])
        interface = network.interfaces[0]
        assert network.ipaddress == IPNetwork("127.0.1.0/24")
        assert interface.ipaddress == IPAddress("127.0.1.1")
        assert network.router_gateway == IPAddress("127.0.1.1")

    async def test_create_management_network(self, mocker: MockerFixture):
        network_ip = IPNetwork("127.0.0.0/24")
        perimeter_router_mock = Mock(router_type=constants.ROUTER_TYPE_PERIMETER, interfaces=[])
        internal_router_mock = Mock(router_type=constants.ROUTER_TYPE_INTERNAL, interfaces=[])
        self.controller.infrastructure.routers = [perimeter_router_mock, internal_router_mock]

        get_network_names_mock = mocker.patch(f"{self.file_path}.util.get_network_names")

        network = Mock(spec=Network)
        network.configure_mock(ipaddress=network_ip)
        network_mock = mocker.patch(f"{self.file_path}.Network", return_value=network)

        interface_mock: Mock = mocker.patch(f"{self.file_path}.Interface")

        await self.controller.create_management_network(network_ip)

        get_network_names_mock.assert_awaited_once()
        network_mock.assert_called_once_with(
            ipaddress=network_ip,
            router_gateway=IPAddress("127.0.0.1"),
            name=f"{self.controller.infrastructure.name}-management",
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

    async def test_prepare_controller_for_infra_creation(self, infrastructure: Mock, mocker: MockerFixture, network):
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

    async def test_create_controller(self, mocker: MockerFixture):
        # Mocks for inputs
        parser_mock = AsyncMock()
        db_session_mock = AsyncMock()
        docker_client_mock = Mock()
        infrastructure_mock = Mock(supernet=IPNetwork("127.0.0.0/16"), name="test_infra")
        used_docker_networks = {Mock()}
        docker_container_names = {"container_name"}
        docker_network_names = {"network_name"}

        # Mocked return values for parser.bake_models
        networks = [Mock()]
        routers = [Mock()]
        nodes = [Mock(interfaces=[Mock(ipaddress="192.168.1.1")])]
        volumes = [Mock()]
        images = [Mock(id="image_1"), Mock(id="image_2"), Mock(id="image_3")]
        parser_mock.bake_models.return_value = (networks, routers, nodes, volumes, images)

        # Other mocks
        db_session_mock.delete = AsyncMock()
        db_session_mock.commit = AsyncMock()
        ensure_image_exists_mock = mocker.patch(
            f"{self.file_path}.InfrastructureController.ensure_image_exists", return_value=AsyncMock()
        )
        generate_subnets_mock = mocker.patch(
            f"{self.file_path}.util.generate_infrastructure_subnets", return_value=Mock()
        )
        prepare_controller_mock = mocker.patch(
            f"{self.controller_path}.prepare_controller_for_infra_creation", return_value=AsyncMock()
        )
        configure_dns_mock = mocker.patch.object(
            InfrastructureController, "configure_dns", return_value=AsyncMock()
        )
        change_names_mock = mocker.patch.object(
            prepare_controller_mock.return_value, "change_names"
        )
        logger_debug_mock = mocker.patch(f"{self.file_path}.logger.debug")

        # Execute the method
        result = await InfrastructureController.create_controller(
            infrastructure=infrastructure_mock,
            used_docker_networks=used_docker_networks,
            parser=parser_mock,
            docker_container_names=docker_container_names,
            docker_network_names=docker_network_names,
            db_session=db_session_mock,
            docker_client=docker_client_mock,
        )

        # Assertions
        parser_mock.bake_models.assert_awaited_once_with(db_session_mock, infrastructure_mock.name)

        # TaskGroup validation
        ensure_image_exists_mock.assert_has_calls(
            [call("image_1", docker_client_mock), call("image_2", docker_client_mock),
             call("image_3", docker_client_mock)]
        )

        # Validate deletion and commit upon exception (simulated as no exception occurs here)
        db_session_mock.delete.assert_not_awaited()

        generate_subnets_mock.assert_awaited_once_with(
            infrastructure_mock.supernet, list(parser_mock.networks_ips), used_docker_networks
        )
        prepare_controller_mock.assert_called_once_with(
            available_networks=generate_subnets_mock.return_value,
            infrastructure=infrastructure_mock,
        )
        configure_dns_mock.assert_awaited_once_with(nodes)
        change_names_mock.assert_awaited_once_with(
            container_names=docker_container_names, network_names=docker_network_names, volumes=volumes
        )

        # Validate logger debug call
        logger_debug_mock.assert_called_once_with(
            "Docker names changed",
            infrastructure_name=infrastructure_mock.name,
        )

        # Final result validation
        assert result == prepare_controller_mock.return_value

    @pytest.fixture
    def docker_client_mock(self):
        docker_client_mock = MagicMock()
        docker_client_mock.networks.list.return_value = [Mock()]
        docker_client_mock.networks.get.return_value = Mock(attrs={"IPAM": {"Config": [{"Subnet": "127.1.0.0/16"}]}})
        return docker_client_mock

    async def test_build_infras(self, mocker: MockerFixture, docker_client_mock: Mock):
        available_infra_supernets = [
            IPNetwork("127.2.0.0/16"),
            IPNetwork("127.3.0.0/16"),
        ]
        db_session = AsyncMock()
        run_mock = AsyncMock()
        used_docker_network_names_mock = Mock()
        used_docker_container_names_mock = Mock()
        mocker.patch(f"{self.file_path}.template_controller.get_template")
        mocker.patch(f"{self.file_path}.docker.from_env", return_value=docker_client_mock)

        get_container_names_mock = mocker.patch(f"{self.file_path}.util.get_container_names",
                     side_effect=AsyncMock(return_value=used_docker_container_names_mock))
        get_network_names_mock = mocker.patch(f"{self.file_path}.util.get_network_names",
                     side_effect=AsyncMock(return_value=used_docker_network_names_mock))

        get_available_networks_for_infras_mock = mocker.patch(
            f"{self.file_path}.util.get_available_networks_for_infras",
            return_value=available_infra_supernets,
        )
        used_docker_networks = {IPNetwork(
            docker_client_mock.networks.get.return_value.attrs["IPAM"]["Config"][0]["Subnet"]
        )}
        controller_mock = AsyncMock()
        infrastructures_mock = [AsyncMock(name="first_infra", supernet=available_infra_supernets[0]),
                                AsyncMock(name="second_infra", supernet=available_infra_supernets[1])]
        create_controller_mock = mocker.patch(f"{self.controller_path}.create_controller", return_value=controller_mock)

        cyst_parser_mock = mocker.patch(f"{self.file_path}.CYSTParser", return_value=AsyncMock(networks_ips=["test"]))
        infra_creation_mock = mocker.patch(f"{self.file_path}.Infrastructure", side_effect=infrastructures_mock)

        mocker.patch.object(cyst_parser_mock, "parse")
        scalar_mock = MagicMock()
        mocker.patch.object(db_session, "scalars", return_value=scalar_mock)
        mocker.patch(f"{self.file_path}.select")
        mocker.patch.object(scalar_mock, "all", return_value=[])
        mocker.patch(f"{self.file_path}.randomname.generate", side_effect=["first_infra", "second_infra"])

        await self.controller.build_infras(2, run_mock, db_session)

        get_container_names_mock.assert_awaited_once_with(docker_client_mock)
        get_network_names_mock.assert_awaited_once_with(docker_client_mock)
        get_available_networks_for_infras_mock.assert_awaited_once_with(used_docker_networks, 2, set())
        # get_template_mock.assert_awaited_once_with(run_mock.template_id, db_session)

        infrastructure_calls = [
            call(
                routers=[],
                nodes=[],
                networks=[],
                name="first_infra",
                supernet=available_infra_supernets[0],
            ),
            call(
                routers=[],
                nodes=[],
                networks=[],
                name="second_infra",
                supernet=available_infra_supernets[1],
            ),
        ]
        controller_calls = [
            call(
                infrastructures_mock[0],
                used_docker_networks,
                cyst_parser_mock.return_value,
                used_docker_container_names_mock,
                used_docker_network_names_mock,
                db_session,
                docker_client_mock
            ),
            call(
                infrastructures_mock[1],
                used_docker_networks,
                cyst_parser_mock.return_value,
                used_docker_container_names_mock,
                used_docker_network_names_mock,
                db_session,
                docker_client_mock

            ),
        ]
        infra_creation_mock.assert_has_calls(infrastructure_calls)
        create_controller_mock.assert_has_calls(controller_calls)

    async def test_build_infrastructure_exception(self, mocker: MockerFixture, infrastructure: Mock):
        instance_mock = mocker.patch(f"{self.file_path}.Instance")
        run_mock = Mock()
        db_session = AsyncMock()
        start_mock = mocker.patch.object(self.controller, "start", side_effect=Exception)
        stop_mock = mocker.patch.object(self.controller, "stop")

        with pytest.raises(Exception):
            await self.controller.build_infrastructure(run_mock, db_session)

        start_mock.assert_called_once()