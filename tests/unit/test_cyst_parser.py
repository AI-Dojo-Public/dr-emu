import pytest
from unittest.mock import AsyncMock, Mock, call
from parser.cyst_parser import CYSTParser
from dr_emu.models import (
    Network,
    Service,
    Router,
    Interface,
    Node,
    Attacker,
    FirewallRule,
)
from netaddr import IPAddress, IPNetwork
from parser.util import constants


@pytest.fixture()
def network():
    return Mock(spec=Network, ipaddress=IPNetwork("127.0.0.0/24"))


@pytest.fixture()
def node():
    return Mock(spec=Node)


@pytest.fixture()
def perimeter_router():
    return Mock(
        spec=Router,
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
        spec=Router,
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


@pytest.fixture()
def attacker():
    return Mock(spec=Attacker)


@pytest.mark.asyncio
class TestCYSTParser:
    @pytest.fixture(autouse=True)
    def parser(self):
        self.parser = CYSTParser(client=Mock())

    async def test_find_network(self, network):
        self.parser.networks.append(network)
        found_network = await self.parser.find_network(IPNetwork("127.0.0.0/24"))
        assert found_network == network

    async def test_get_service_configuration(self):
        pass

    async def test_parse_networks(self, mocker, perimeter_router, internal_router):
        network_names = ["blue_test", "purple_test"]
        mocker.patch("randomname.get_name", side_effect=network_names)
        cyst_routers = [
            perimeter_router,
            internal_router,
        ]

        await self.parser.parse_networks(cyst_routers)

        assert self.parser.networks[0].network_type == constants.NETWORK_TYPE_PUBLIC
        assert self.parser.networks[1].network_type == constants.NETWORK_TYPE_INTERNAL
        for i in range(len(cyst_routers)):
            assert self.parser.networks[i].ipaddress == cyst_routers[i].interfaces[0].net
            assert self.parser.networks[i].router_gateway == cyst_routers[i].interfaces[0].ip
            assert self.parser.networks[i].name == network_names[i]

    async def test_parse_nodes(self, mocker):
        mocker.patch("parser.cyst_parser.CYSTParser.parse_services", side_effect=AsyncMock(return_value=[]))
        interface = mocker.patch("parser.cyst_parser.Interface").return_value
        find_network_mock = mocker.patch("parser.cyst_parser.CYSTParser.find_network")

        attacker = Mock(
            id="attacker",
            interfaces=[Mock(net=IPNetwork("127.0.0.0/24"), ip=IPAddress("127.0.0.2"))],
            active_services=[],
            passive_services=[],
        )
        cyst_nodes = [
            Mock(
                id="node",
                interfaces=[Mock(net=IPNetwork("127.0.0.0/24"), ip=IPAddress("127.0.0.1"))],
                active_services=[],
                passive_services=[],
            ),
            attacker,
        ]

        await self.parser.parse_nodes(cyst_nodes, attacker)

        for i in range(len(cyst_nodes)):
            assert self.parser.nodes[i].interfaces[0].network == interface.network
            assert self.parser.nodes[i].interfaces[0].ipaddress == interface.ipaddress
            assert self.parser.nodes[i].name == cyst_nodes[i].id
            assert self.parser.nodes[i].services == []

        assert isinstance(self.parser.nodes[0], Node)
        assert isinstance(self.parser.nodes[1], Attacker)
        find_network_mock.assert_awaited_with(IPNetwork("127.0.0.0/24"))

    async def test_parse_services(self, mocker):
        get_config_mock = mocker.patch("parser.cyst_parser.CYSTParser.get_service_configuration")
        service = Mock(id="service", type="wordpress")
        node_services = [service]

        services = await self.parser.parse_services(node_services)

        assert services[0].name == service.type
        assert services[0].image == constants.IMAGE_NODE
        assert services[0].command == []
        assert services[0].healthcheck == dict()

        assert isinstance(services[0], Service)

        get_config_mock.assert_awaited_with(service.type)

    @pytest.mark.parametrize(
        "router, router_type",
        [("internal_router", "internal"), ("perimeter_router", "perimeter")],
    )
    async def test_parse_routers(self, mocker, router, router_type, request):
        fw_rule = mocker.patch("parser.cyst_parser.FirewallRule")
        interface = mocker.patch("parser.cyst_parser.Interface")
        find_network_mock = mocker.patch("parser.cyst_parser.CYSTParser.find_network")
        router = request.getfixturevalue(router)
        cyst_routers = [router]

        await self.parser.parse_routers(cyst_routers)

        assert self.parser.routers[0].router_type == router_type
        assert self.parser.routers[0].interfaces[0] == interface.return_value
        assert self.parser.routers[0].firewall_rules[0] == fw_rule.return_value
        calls = [
            call(router.interfaces[0].net),
            call(router.traffic_processors[0].chains[0].rules[0].dst_net),
            call(router.traffic_processors[0].chains[0].rules[0].src_net),
        ]
        find_network_mock.assert_has_awaits(calls)

    async def test_parse(self, mocker, internal_router, perimeter_router, node, attacker):
        parse_networks_mock = mocker.patch("parser.cyst_parser.CYSTParser.parse_networks")
        parse_routers_mock = mocker.patch("parser.cyst_parser.CYSTParser.parse_routers")
        parse_nodes_mock = mocker.patch("parser.cyst_parser.CYSTParser.parse_nodes")
        parse_images_mock = mocker.patch("parser.cyst_parser.CYSTParser.parse_images")

        routers = [internal_router, perimeter_router]
        nodes = [node, attacker]
        await self.parser.parse(routers, nodes, attacker)

        parse_networks_mock.assert_awaited_once_with(routers)
        parse_routers_mock.assert_awaited_once_with(routers)
        parse_nodes_mock.assert_awaited_once_with(nodes, attacker)
        parse_images_mock.assert_awaited_once()
