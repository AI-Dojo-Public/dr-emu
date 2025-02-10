import pytest
from frozendict import frozendict
from pytest_mock import MockerFixture
from unittest.mock import AsyncMock, Mock, call, MagicMock

from shared import constants
from parser.cyst_parser import CYSTParser
from parser.lib.simple_models import Network, Node, Service, ServiceContainer, NodeType
from cyst.api.configuration import NodeConfig, RouterConfig, PassiveServiceConfig
from netaddr import IPAddress, IPNetwork
from parser.lib import containers


@pytest.fixture()
def network():
    return Mock(spec=Network, subnet=IPNetwork("127.0.0.0/24"))


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
        routing_table=[Mock()]
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
        routing_table=[Mock()]
    )


@pytest.mark.asyncio
class TestCYSTParser:
    path = "parser.cyst_parser"

    @pytest.fixture(autouse=True)
    def parser(self, mocker: MockerFixture):
        mocker.patch("parser.cyst_parser.CYSTParser._load_infrastructure_description")
        self.parser = CYSTParser("")

    async def test_find_network(self, network: Mock):
        self.parser.networks.append(network)
        found_network = await self.parser._find_network(IPNetwork("127.0.0.0/24"))
        assert found_network == network

    async def test_get_service_configuration(self):
        pass

    async def test_parse_networks(self, mocker: MockerFixture, perimeter_router: Mock, internal_router):
        network_names = ["test1", "test2"]
        mocker.patch(f"{self.path}.randomname.generate", side_effect=network_names)
        cyst_routers: list[Mock] = [
            perimeter_router,
            internal_router,
        ]

        await self.parser._parse_networks(cyst_routers)

        assert self.parser.networks[0].type == constants.NETWORK_TYPE_PUBLIC
        assert self.parser.networks[1].type == constants.NETWORK_TYPE_INTERNAL
        for i in range(len(cyst_routers)):
            assert self.parser.networks[i].subnet == cyst_routers[i].interfaces[0].net
            assert self.parser.networks[i].gateway == cyst_routers[i].interfaces[0].ip
            assert self.parser.networks[i].name == network_names[i]

    async def test_parse_nodes(self, mocker: MockerFixture):
        # Create parser mock and setup attributes
        self.parser._find_network = AsyncMock(return_value=Mock())
        services_mock = [Mock(spec=Service), Mock(spec=Service)]
        self.parser._parse_services = AsyncMock(return_value=services_mock)
        self.parser.create_image = AsyncMock(return_value="image_id")

        # Sample cyst_nodes and exploits
        cyst_nodes = [
            Mock(
                id="node1",
                interfaces=[Mock(ip="192.168.1.1", net="net1")],
                active_services=[Mock(name="service1")],
                passive_services=[Mock(name="service2")]
            ),
            Mock(
                id="node2",
                interfaces=[Mock(ip="192.168.1.2", net="net2")],
                active_services=[],
                passive_services=[Mock(name="service3")]
            ),
        ]

        exploits = [
            Mock(services=[MagicMock(service="vuln_service"), MagicMock(service="bash")]),
            Mock(services=[MagicMock(service="service2")])
        ]

        for exploit in exploits:
            for service in exploit.services:
                service.name = service._mock_name  # Ensures name is a direct string

        predefined_node = Mock(image="existing_image", service_containers=[Mock(image="service_image")])
        mocker.patch.dict("parser.lib.containers.NODES", {"node1": predefined_node})
        mocker.patch(f"{self.path}.copy.deepcopy", return_value=predefined_node)
        mocker.patch(f"{self.path}.cif.available_services", return_value=[["service1"]])
        # Run the function
        await self.parser._parse_nodes(cyst_nodes, exploits)

        # Assertions for existing node
        assert self.parser._find_network.await_count == len(cyst_nodes[0].interfaces) + len(cyst_nodes[1].interfaces)
        assert predefined_node in self.parser.nodes
        assert "existing_image" in self.parser.docker_images
        assert "service_image" in self.parser.docker_images

        # Check if services and images were processed for the new node (node2)
        self.parser._parse_services.assert_awaited_once_with(
            cyst_nodes[1].active_services + cyst_nodes[1].passive_services, {"vuln_service", "service2", "bash"}, []
        )
        self.parser.create_image.assert_awaited_once_with(services=services_mock, data_configurations=[],
                                                          available_cif_services=["service1"])

        # Assertions for new node creation and addition
        assert len(self.parser.nodes) == 2
        assert self.parser.nodes[1].name == "node2"
        assert self.parser.nodes[1].image == "image_id"
        assert self.parser.nodes[1].type == NodeType.DEFAULT

    async def test_parse_services(self, mocker: MockerFixture):
        exploits = {"test_type", "vuln_service2"}
        data_type_config_mock = "test_type"
        data_configs = []
        cs1 = Mock(id="service", version="test", spec=PassiveServiceConfig,
             private_data=[data_type_config_mock])
        cs1.name = "test_type"
        cs2 = Mock(id="ssh", spec=PassiveServiceConfig, private_data=[])
        cs2.name = "ssh"
        cyst_services = [cs1, cs2]
        predefined_services = {
            "ssh": Service(type="ssh", variable_override=frozendict(SSH_PORT=22, SSH_HOST="0.0.0.0"), cves="")
        }
        mocker.patch.dict('parser.lib.containers.SERVICES', predefined_services)
        mocker.patch('parser.lib.containers.EXPLOITS', exploits)
        services = await self.parser._parse_services(cyst_services, exploits, data_configs)

        assert services == [
            Service(type="test_type", version="test", cves="cve_placeholder;"),
            Service(type="ssh", variable_override=frozendict(SSH_PORT=22, SSH_HOST="0.0.0.0"), cves="")
        ]
        assert data_type_config_mock in data_configs

    @pytest.mark.parametrize(
        "router, router_type",
        [("internal_router", "internal"), ("perimeter_router", "perimeter")],
    )
    async def test_parse_routers(self, mocker: MockerFixture, router: Mock, router_type: Mock, request):
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

    async def test_parse(self, mocker: MockerFixture, internal_router: Mock, perimeter_router: Mock, node: Mock):
        parse_networks_mock = mocker.patch(f"{self.path}.CYSTParser._parse_networks")
        parse_routers_mock = mocker.patch(f"{self.path}.CYSTParser._parse_routers")
        parse_nodes_mock = mocker.patch(f"{self.path}.CYSTParser._parse_nodes")

        routers = [internal_router, perimeter_router]
        nodes = [node]

        self.parser.infrastructure = routers + nodes
        await self.parser.parse()

        parse_networks_mock.assert_awaited_once_with(routers)
        parse_routers_mock.assert_awaited_once_with(routers)
        parse_nodes_mock.assert_awaited_once_with(nodes, [])

# @pytest.mark.asyncio
# class TestContainers:
#     async def test_match_exact_node(self):
#         mock_container_a = containers.NodeContainer("",
#                                                     services=[Service("x"), Service("y")])
#         mock_container_b = containers.NodeContainer("", services=[Service("x")])
#         containers.CONTAINER_DB = [mock_container_a, mock_container_b]
#         match_rules = [Service("x")]
#
#         result = await containers.match_node_container(match_rules)
#
#         assert result == mock_container_b

# async def test_match_closest_node(self):
#     mock_container_a = containers.NodeContainer(
#         "", services=[Service("x"), Service("y"), Service("z")]
#     )
#     mock_container_b = containers.NodeContainer("",
#                                                 services=[Service("x"), Service("y")])
#     containers.CONTAINER_DB = [mock_container_a, mock_container_b]
#     match_rules = [Service("x")]
#
#     result = await containers.match_node_container(match_rules)
#
#     assert result == mock_container_b
