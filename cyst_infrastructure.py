from netaddr import IPAddress, IPNetwork
from cyst.api.configuration import (
    AuthenticationProviderConfig,
    PassiveServiceConfig,
    AccessSchemeConfig,
    AuthorizationDomainConfig,
    AuthorizationDomainType,
    AuthorizationConfig,
    NodeConfig,
    InterfaceConfig,
    ActiveServiceConfig,
    RouterConfig,
    ConnectionConfig,
    FirewallConfig,
    FirewallChainConfig,
    ExploitConfig,
    ExploitCategory,
    ExploitLocality,
    VulnerableServiceConfig,
    DataConfig,
    RouteConfig,
)
from cyst.api.environment.configuration import ServiceParameter
from cyst.api.logic.access import (
    AccessLevel,
    AuthenticationProviderType,
    AuthenticationTokenType,
    AuthenticationTokenSecurity,
)
from cyst.api.network.firewall import FirewallPolicy, FirewallChainType, FirewallRule

from pathlib import Path

with open(f"{Path(__file__).parent}/phishing.py") as f:
    phishing_file = f.read()

# -----------------------------------------------------------------------------
# Network definitions
# -----------------------------------------------------------------------------
network_internal = IPNetwork("192.168.1.0/24")
network_wifi = IPNetwork("192.168.2.0/24")
network_server = IPNetwork("192.168.3.0/24")
network_outside = IPNetwork("192.168.4.0/24")

# -----------------------------------------------------------------------------
# Local password authentication template
# -----------------------------------------------------------------------------
auth_local_password = AuthenticationProviderConfig(
    provider_type=AuthenticationProviderType.LOCAL,
    token_type=AuthenticationTokenType.PASSWORD,
    token_security=AuthenticationTokenSecurity.SEALED,
    timeout=30,
)

# -----------------------------------------------------------------------------
# Node definitions
# -----------------------------------------------------------------------------
node_attacker = NodeConfig(
    active_services=[ActiveServiceConfig("scripted_actor", "scripted_attacker", "attacker", AccessLevel.LIMITED)],
    passive_services=[
        # PassiveServiceConfig(
        #     type="empire", owner="empire", version="4.10.0", access_level=AccessLevel.LIMITED
        # ),
        PassiveServiceConfig(
            name="metasploit", owner="msf", version="0.1.0", local=True, access_level=AccessLevel.LIMITED
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_outside.first + 10), network_outside)],
    shell="",
    id="node_attacker",
)

node_dns = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            name="coredns",
            owner="coredns",
            version="1.11.1",
            local=False,
            access_level=AccessLevel.LIMITED,
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_outside.first + 2), network_outside)],
    shell="",
    id="node_dns",
)

node_wordpress = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            name="wordpress",
            owner="wordpress",
            version="6.1.1",
            local=False,
            access_level=AccessLevel.LIMITED,
            authentication_providers=[auth_local_password("wordpress_pwd")],
            access_schemes=[
                AccessSchemeConfig(
                    authentication_providers=["wordpress_pwd"],
                    authorization_domain=AuthorizationDomainConfig(
                        type=AuthorizationDomainType.LOCAL,
                        authorizations=[AuthorizationConfig("wordpress", AccessLevel.ELEVATED)],
                    ),
                )
            ],
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_server.first + 10), network_server)],
    shell="",
    id="node_wordpress",
)

node_database = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            name="mysql",
            owner="mysql",
            version="8.0.31",
            local=False,
            private_data=[DataConfig(owner="mysql", description="secret data for exfiltration", id="db")],
            access_level=AccessLevel.LIMITED,
            authentication_providers=[auth_local_password("mysql_pwd")],
            access_schemes=[
                AccessSchemeConfig(
                    authentication_providers=["mysql_pwd"],
                    authorization_domain=AuthorizationDomainConfig(
                        type=AuthorizationDomainType.LOCAL,
                        authorizations=[AuthorizationConfig("mysql", AccessLevel.ELEVATED)],
                    ),
                )
            ],
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_server.first + 11), network_server)],
    shell="",
    id="node_wordpress_database",
)

node_vsftpd = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            name="vsftpd", owner="vsftpd", version="2.3.4", local=False, access_level=AccessLevel.LIMITED
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_server.first + 12), network_server)],
    shell="",
    id="node_vsftpd",
)

node_mail = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            name="dovecot-imapd", owner="haraka", version="2.3.4", local=False, access_level=AccessLevel.LIMITED
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_server.first + 13), network_server)],
    shell="",
    id="node_haraka",
)

node_chat = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(name="tchat", owner="chat", version="2.3.4", local=False, access_level=AccessLevel.LIMITED)
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_server.first + 14), network_server)],
    shell="",
    id="node_chat",
)

node_client_developer = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            name="ssh",
            owner="ssh",
            version="5.1.4",
            local=False,
            access_level=AccessLevel.ELEVATED,
            parameters=[
                (ServiceParameter.ENABLE_SESSION, True),
                (ServiceParameter.SESSION_ACCESS_LEVEL, AccessLevel.ELEVATED),
            ],
            authentication_providers=[auth_local_password("user_pc_pwd")],
            access_schemes=[
                AccessSchemeConfig(
                    authentication_providers=["user_pc_pwd"],
                    authorization_domain=AuthorizationDomainConfig(
                        type=AuthorizationDomainType.LOCAL,
                        authorizations=[AuthorizationConfig("user", AccessLevel.ELEVATED)],
                    ),
                ),
            ],
            private_data=[
                DataConfig(
                    id="~/.bash_history",
                    description=f"mysqldump -u user -h {node_database.interfaces[0].ip} --password=pass --no-tablespaces table",
                    owner="user",
                )
            ],
        ),
        PassiveServiceConfig(
            name="mysql-client",
            owner="user",
            version="8.1.0",
            local=True,
            access_level=AccessLevel.ELEVATED,
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_internal.first + 10), network_internal)],
    shell="",
    id="node_developer",
)

node_client_1 = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            name="python3",
            owner="user",
            version="3.11.1",
            local=True,
            access_level=AccessLevel.ELEVATED,
            private_data=[
                DataConfig(
                    id="/entrypoints/phishing.py",
                    description=phishing_file,
                    owner="user",
                )
            ]
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_internal.first + 11), network_internal)],
    shell="",
    id="node_client1",
)

node_client_2 = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(name="inetutils-ping", owner="user", version="8.1.0", local=True, access_level=AccessLevel.ELEVATED),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_internal.first + 12), network_internal)],
    shell="",
    id="node_client2",
)

node_client_3 = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(name="inetutils-ping", owner="user", version="8.1.0", local=True, access_level=AccessLevel.ELEVATED),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_internal.first + 13), network_internal)],
    shell="",
    id="node_client3",
)

node_client_4 = NodeConfig(
    active_services=[],
    passive_services=[PassiveServiceConfig(name="inetutils-ping", owner="user", version="8.1.0", local=True, access_level=AccessLevel.ELEVATED),],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_wifi.first + 10), network_wifi)],
    shell="",
    id="node_client4",
)

node_client_5 = NodeConfig(
    active_services=[],
    passive_services=[PassiveServiceConfig(name="inetutils-ping", owner="user", version="8.1.0", local=True, access_level=AccessLevel.ELEVATED),],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_wifi.first + 11), network_wifi)],
    shell="",
    id="node_client5",
)

node_client_6 = NodeConfig(
    active_services=[],
    passive_services=[PassiveServiceConfig(name="inetutils-ping", owner="user", version="8.1.0", local=True, access_level=AccessLevel.ELEVATED),],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress(network_wifi.first + 12), network_wifi)],
    shell="",
    id="node_client6",
)

# -----------------------------------------------------------------------------
# Router definitions
# -----------------------------------------------------------------------------
router_perimeter = RouterConfig(
    interfaces=[
        InterfaceConfig(IPAddress(network_internal.first + 1), network_internal, index=0),
        InterfaceConfig(IPAddress(network_internal.first + 1), network_internal, index=1),
        InterfaceConfig(IPAddress(network_internal.first + 1), network_internal, index=2),
        InterfaceConfig(IPAddress(network_internal.first + 1), network_internal, index=3),
        InterfaceConfig(IPAddress(network_internal.first + 1), network_internal, index=4),
        InterfaceConfig(IPAddress(network_outside.first + 1), network_outside, index=5),
        InterfaceConfig(IPAddress(network_outside.first + 1), network_outside, index=6),
        InterfaceConfig(IPAddress(network_wifi.first + 1), network_wifi, index=7),
        InterfaceConfig(IPAddress(network_server.first + 1), network_server, index=8),
    ],
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.DENY,
            chains=[
                FirewallChainConfig(
                    type=FirewallChainType.FORWARD,
                    policy=FirewallPolicy.DENY,
                    rules=[
                        FirewallRule(
                            src_net=network_internal, dst_net=network_internal, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_outside, dst_net=network_outside, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_internal, dst_net=network_outside, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(  # TODO: shouldn't be necessary, probably because of direct action
                            src_net=network_outside, dst_net=network_internal, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_internal, dst_net=network_server, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_server, dst_net=network_internal, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_internal, dst_net=network_wifi, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_wifi, dst_net=network_internal, service="*", policy=FirewallPolicy.ALLOW
                        ),
                    ],
                )
            ],
        )
    ],
    routing_table=[RouteConfig(network_wifi, 7), RouteConfig(network_server, 8)],
    id="perimeter_router",
)

router_server = RouterConfig(
    interfaces=[
        InterfaceConfig(IPAddress(network_internal.first + 1), network_internal, index=0),
        InterfaceConfig(IPAddress(network_server.first + 1), network_server, index=1),
        InterfaceConfig(IPAddress(network_server.first + 1), network_server, index=2),
        InterfaceConfig(IPAddress(network_server.first + 1), network_server, index=3),
        InterfaceConfig(IPAddress(network_server.first + 1), network_server, index=4),
        InterfaceConfig(IPAddress(network_server.first + 1), network_server, index=5),
    ],
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.DENY,
            chains=[
                FirewallChainConfig(
                    type=FirewallChainType.FORWARD,
                    policy=FirewallPolicy.DENY,
                    rules=[
                        FirewallRule(
                            src_net=network_server, dst_net=network_server, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_server, dst_net=network_internal, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_internal, dst_net=network_server, service="*", policy=FirewallPolicy.ALLOW
                        ),
                    ],
                )
            ],
        )
    ],
    routing_table=[
        RouteConfig(network_internal, 0),
    ],
    id="server_router",
)

router_wifi = RouterConfig(
    interfaces=[
        InterfaceConfig(IPAddress(network_internal.first + 1), network_internal, index=0),
        InterfaceConfig(IPAddress(network_wifi.first + 1), network_wifi, index=1),
        InterfaceConfig(IPAddress(network_wifi.first + 1), network_wifi, index=2),
        InterfaceConfig(IPAddress(network_wifi.first + 1), network_wifi, index=3),
    ],
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.DENY,
            chains=[
                FirewallChainConfig(
                    type=FirewallChainType.FORWARD,
                    policy=FirewallPolicy.DENY,
                    rules=[
                        FirewallRule(
                            src_net=network_wifi, dst_net=network_wifi, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_internal, dst_net=network_wifi, service="*", policy=FirewallPolicy.ALLOW
                        ),
                        FirewallRule(
                            src_net=network_wifi, dst_net=network_internal, service="*", policy=FirewallPolicy.ALLOW
                        ),
                    ],
                )
            ],
        )
    ],
    routing_table=[
        RouteConfig(network_internal, 0),
    ],
    id="wifi_router",
)

# -----------------------------------------------------------------------------
# Connection definitions
# -----------------------------------------------------------------------------
connections_perimeter_router = [
    ConnectionConfig(node_client_1, 0, router_perimeter, 1),
    ConnectionConfig(node_client_2, 0, router_perimeter, 2),
    ConnectionConfig(node_client_3, 0, router_perimeter, 3),
    ConnectionConfig(node_client_developer, 0, router_perimeter, 4),
    ConnectionConfig(node_attacker, 0, router_perimeter, 5),
    ConnectionConfig(node_dns, 0, router_perimeter, 6),
]

connections_server_router = [
    ConnectionConfig(node_wordpress, 0, router_server, 1),
    ConnectionConfig(node_database, 0, router_server, 2),
    ConnectionConfig(node_vsftpd, 0, router_server, 3),
    ConnectionConfig(node_chat, 0, router_server, 4),
    ConnectionConfig(node_mail, 0, router_server, 5),
]

connections_wifi_router = [
    ConnectionConfig(node_client_4, 0, router_wifi, 1),
    ConnectionConfig(node_client_5, 0, router_wifi, 2),
    ConnectionConfig(node_client_6, 0, router_wifi, 3),
]

connections_routes = [
    ConnectionConfig(router_perimeter, 7, router_wifi, 0),
    ConnectionConfig(router_perimeter, 8, router_server, 0),
]

# -----------------------------------------------------------------------------
# Exploit definitions
# -----------------------------------------------------------------------------
exploit_vsftpd = ExploitConfig(
    [VulnerableServiceConfig("vsftpd", "2.3.4")],
    ExploitLocality.REMOTE,
    ExploitCategory.CODE_EXECUTION,
)

exploit_phishing = ExploitConfig(
    services=[VulnerableServiceConfig(service="python3", min_version="3.11.1", max_version="3.11.1")],
    locality=ExploitLocality.REMOTE,
    category=ExploitCategory.CODE_EXECUTION,
    id="phishing_exploit",
)

exploit_bruteforce = ExploitConfig(
    services=[VulnerableServiceConfig(service="ssh", min_version="5.1.4", max_version="5.1.4")],
    locality=ExploitLocality.REMOTE,
    category=ExploitCategory.CODE_EXECUTION,
)

# -----------------------------------------------------------------------------
# Packaging it together
# -----------------------------------------------------------------------------
nodes = [
    node_attacker,
    node_dns,
    node_wordpress,
    node_database,
    node_vsftpd,
    node_chat,
    node_mail,
    node_client_developer,
    node_client_1,
    node_client_2,
    node_client_3,
    node_client_4,
    node_client_5,
    node_client_6,
]
routers = [router_perimeter, router_server, router_wifi]
connections = [*connections_server_router, *connections_perimeter_router, *connections_wifi_router, *connections_routes]
exploits = [exploit_vsftpd, exploit_phishing, exploit_bruteforce]
all_config_items = [*nodes, *routers, *connections, *exploits]
