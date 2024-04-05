import pytest
from pytest_mock import MockerFixture
from unittest.mock import AsyncMock, Mock, call
from parser.cyst_parser import CYSTParser
from parser.lib.simple_models import Network, Node, Service
from cyst.api.configuration import NodeConfig, RouterConfig
from netaddr import IPAddress, IPNetwork
from parser.util import constants
from parser.lib import containers


@pytest.fixture()
def network():
    return Mock(spec=Network, ip_address=IPNetwork("127.0.0.0/24"))


@pytest.fixture()
def node():
    return Mock(spec=NodeConfig)


@pytest.fixture()
def perimeter_router():
    return Mock(
        spec=RouterConfig,
        id="perimeter_router",
        interfaces=[Mock(net=IPNetwork("127.0.0.0/24"), ip=IPAddress("127.0.0.1"))],
        traffic_processors=[
            Mock(
                chains=[
                    Mock(
                        policy="DENY",
                        rules=[
                            # Enable traffic flow between the three networks
                            Mock(
                                src_net=IPNetwork("127.0.0.0/24"),
                                dst_net=IPNetwork("127.0.1.0/24"),
                                service="*",
                                policy=Mock(name="ALLOW"),
                            )
                        ],
                    )
                ]
            )
        ],
    )


@pytest.fixture()
def internal_router():
    return Mock(
        spec=RouterConfig,
        id="internal_router",
        interfaces=[Mock(net=IPNetwork("127.0.1.0/24"), ip=IPAddress("127.0.1.1"))],
        traffic_processors=[
            Mock(
                chains=[
                    Mock(
                        policy="DENY",
                        rules=[
                            # Enable traffic flow between the three networks
                            Mock(
                                src_net=IPNetwork("127.0.1.0/24"),
                                dst_net=IPNetwork("127.0.0.0/24"),
                                service="*",
                                policy=Mock(name="ALLOW"),
                            )
                        ],
                    )
                ]
            )
        ],
    )


@pytest.mark.asyncio
class TestCYSTParser:
    path = "parser.cyst_parser"

    @pytest.fixture(autouse=True)
    def parser(self, mocker):
        mocker.patch("parser.cyst_parser.CYSTParser._load_infrastructure_description")
        self.parser = CYSTParser("")

    async def test_find_network(self, network):
        self.parser.networks.append(network)
        found_network = await self.parser._find_network(IPNetwork("127.0.0.0/24"))
        assert found_network == network

    async def test_get_service_configuration(self):
        pass

    async def test_parse_networks(self, mocker, perimeter_router, internal_router):
        network_names = ["test1", "test2"]
        mocker.patch(f"{self.path}.randomname.generate", side_effect=network_names)
        cyst_routers = [
            perimeter_router,
            internal_router,
        ]

        await self.parser._parse_networks(cyst_routers)

        assert self.parser.networks[0].type == constants.NETWORK_TYPE_PUBLIC
        assert self.parser.networks[1].type == constants.NETWORK_TYPE_INTERNAL
        for i in range(len(cyst_routers)):
            assert self.parser.networks[i].ip_address == cyst_routers[i].interfaces[0].net
            assert self.parser.networks[i].gateway == cyst_routers[i].interfaces[0].ip
            assert self.parser.networks[i].name == network_names[i]

    async def test_parse_nodes(self, mocker: MockerFixture):
        mocker.patch(f"{self.path}.CYSTParser._parse_services", side_effect=AsyncMock(return_value=[]))
        mock_interface = mocker.patch(f"{self.path}.Interface", return_value=Mock())
        find_network_mock = mocker.patch(f"{self.path}.CYSTParser._find_network")

        cyst_nodes = [
            Mock(
                id="node",
                interfaces=[Mock(net=IPNetwork("127.0.0.0/24"), ip=IPAddress("127.0.0.1"))],
                active_services=[],
                passive_services=[],
            )
        ]

        await self.parser._parse_nodes(cyst_nodes)

        for i in range(len(cyst_nodes)):
            assert self.parser.nodes[i].interfaces[0].network == mock_interface.return_value.network
            assert self.parser.nodes[i].interfaces[0].ip_address == mock_interface.return_value.ip_address
            assert self.parser.nodes[i].name == cyst_nodes[i].id
            assert self.parser.nodes[i].services == []

        assert isinstance(self.parser.nodes[0], Node)
        find_network_mock.assert_awaited_with(IPNetwork("127.0.0.0/24"))

    async def test_parse_services(self, mocker: MockerFixture):
        mock_uuid1 = mocker.patch(f"{self.path}.uuid1", return_value="uuid")
        service = Mock(id="service", type="wordpress")
        node_services = [service]

        services = await self.parser._parse_services(node_services)

        assert services[0].name == mock_uuid1.return_value
        assert services[0].container.image == containers.DEFAULT.image
        assert services[0].container.command == []
        assert services[0].container.healthcheck == {}

        assert isinstance(services[0], Service)

    @pytest.mark.parametrize(
        "router, router_type",
        [("internal_router", "internal"), ("perimeter_router", "perimeter")],
    )
    async def test_parse_routers(self, mocker: MockerFixture, router, router_type, request):
        fw_rule = mocker.patch(f"{self.path}.FirewallRule")
        interface = mocker.patch(f"{self.path}.Interface")
        find_network_mock = mocker.patch(f"{self.path}.CYSTParser._find_network")
        router = request.getfixturevalue(router)
        cyst_routers = [router]

        await self.parser._parse_routers(cyst_routers)

        assert self.parser.routers[0].type == router_type
        assert self.parser.routers[0].interfaces[0] == interface.return_value
        assert self.parser.routers[0].firewall_rules[0] == fw_rule.return_value
        calls = [
            call(router.interfaces[0].net),
            call(router.traffic_processors[0].chains[0].rules[0].dst_net),
            call(router.traffic_processors[0].chains[0].rules[0].src_net),
        ]
        find_network_mock.assert_has_awaits(calls)

    async def test_parse(self, mocker: MockerFixture, internal_router, perimeter_router, node):
        parse_networks_mock = mocker.patch(f"{self.path}.CYSTParser._parse_networks")
        parse_routers_mock = mocker.patch(f"{self.path}.CYSTParser._parse_routers")
        parse_nodes_mock = mocker.patch(f"{self.path}.CYSTParser._parse_nodes")

        routers = [internal_router, perimeter_router]
        nodes = [node]

        self.parser.infrastructure = routers + nodes
        await self.parser.parse()

        parse_networks_mock.assert_awaited_once_with(routers)
        parse_routers_mock.assert_awaited_once_with(routers)
        parse_nodes_mock.assert_awaited_once_with(nodes)
