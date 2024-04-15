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
)  # , PortConfig

from cyst.api.environment.configuration import ServiceParameter
from cyst.api.logic.access import (
    AccessLevel,
    AuthenticationProviderType,
    AuthenticationTokenType,
    AuthenticationTokenSecurity,
)
from cyst.api.network.firewall import FirewallPolicy, FirewallChainType, FirewallRule


# -----------------------------------------------------------------------------
# Scripted attacker
# - used for scenarios 2 and 3
# - represents Cryton's scripting functionality
# -----------------------------------------------------------------------------
scripted_attacker = NodeConfig(
    active_services=[
        ActiveServiceConfig(
            "scripted_actor",
            "scripted_attacker",
            "attacker",
            AccessLevel.LIMITED
        )
    ],
    passive_services=[
        PassiveServiceConfig(
            type="jtr",
            owner="jtr",
            version="1.9.0",
            local=True,
            access_level=AccessLevel.LIMITED
        ),
        # PassiveServiceConfig(
        #     type="empire",
        #     owner="empire",
        #     version="4.10.0",
        #     local=True,
        #     access_level=AccessLevel.LIMITED
        # ),
        PassiveServiceConfig(
            type="metasploit",
            owner="msf",
            version="0.1.0",
            local=True,
            access_level=AccessLevel.LIMITED
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.4.10"), IPNetwork("192.168.4.0/24"))],
    shell="",
    id="attacker_node",
)

# -----------------------------------------------------------------------------
# Local password authentication template
# -----------------------------------------------------------------------------
local_password_auth = AuthenticationProviderConfig(
    provider_type=AuthenticationProviderType.LOCAL,
    token_type=AuthenticationTokenType.PASSWORD,
    token_security=AuthenticationTokenSecurity.SEALED,
    timeout=30,
)

# -----------------------------------------------------------------------------
# Wordpress server
# - used for scenarios 2, 3, and 4
# -----------------------------------------------------------------------------
wordpress_srv = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="wordpress",
            owner="wordpress",
            version="6.1.1",
            local=False,
            access_level=AccessLevel.LIMITED,
            authentication_providers=[local_password_auth("wordpress_pwd")],
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
    interfaces=[InterfaceConfig(IPAddress("192.168.3.11"), IPNetwork("192.168.3.0/24"))],
    shell="",
    id="wordpress_node",
)

wordpress_db = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="mysql",
            owner="mysql",
            version="8.0.31",
            local=False,
            access_level=AccessLevel.LIMITED
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.3.10"), IPNetwork("192.168.3.0/24"))],
    shell="",
    id="wordpress_db_node",
)

# -----------------------------------------------------------------------------
# vFTP server
# - used for scenarios 2, 3, and 4
# -----------------------------------------------------------------------------
vsftpd_srv = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="vsftpd",
            owner="vsftpd",
            version="2.3.4",
            local=False,
            access_level=AccessLevel.LIMITED
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.3.20"), IPNetwork("192.168.3.0/24"))],
    shell="",
    id="vsftpd_node",
)

# -----------------------------------------------------------------------------
# PostgreSQL DB server
# - used for scenarios 2, 3, and 4
# -----------------------------------------------------------------------------
postgres_srv = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="postgres",
            owner="postgres",
            version="10.5.0",
            local=False,
            private_data=[DataConfig(owner="dbuser", description="secret data for exfiltration")],
            access_level=AccessLevel.LIMITED,
            authentication_providers=[local_password_auth("postgres_pwd")],
            access_schemes=[
                AccessSchemeConfig(
                    authentication_providers=["postgres_pwd"],
                    authorization_domain=AuthorizationDomainConfig(
                        type=AuthorizationDomainType.LOCAL,
                        authorizations=[AuthorizationConfig("dbuser", AccessLevel.ELEVATED)],
                    ),
                )
            ],
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.3.21"), IPNetwork("192.168.3.0/24"))],
    shell="",
    id="postgres_node",
)

# -----------------------------------------------------------------------------
# Haraka server
# -----------------------------------------------------------------------------
haraka_srv = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="haraka",
            owner="haraka",
            version="2.3.4",
            local=False,
            access_level=AccessLevel.LIMITED
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.3.22"), IPNetwork("192.168.3.0/24"))],
    shell="",
    id="haraka_node",
)


# -----------------------------------------------------------------------------
# Chat server
# -----------------------------------------------------------------------------

chat_srv = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="tchat",
            owner="chat",
            version="2.3.4",
            local=False,
            access_level=AccessLevel.LIMITED
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.3.23"), IPNetwork("192.168.3.0/24"))],
    shell="",
    id="chat_node",
)


# -----------------------------------------------------------------------------
# User PC server
# - used for scenarios 2, 3, and 4
# -----------------------------------------------------------------------------

developer = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="ssh",
            owner="ssh",
            version="5.1.4",
            local=False,
            access_level=AccessLevel.ELEVATED,
            parameters=[
                (ServiceParameter.ENABLE_SESSION, True),
                (ServiceParameter.SESSION_ACCESS_LEVEL, AccessLevel.LIMITED),
            ],
            authentication_providers=[local_password_auth("user_pc_pwd")],
            access_schemes=[
                AccessSchemeConfig(
                    authentication_providers=["user_pc_pwd"],
                    authorization_domain=AuthorizationDomainConfig(
                        type=AuthorizationDomainType.LOCAL,
                        authorizations=[AuthorizationConfig("user", AccessLevel.ELEVATED)],
                    ),
                )
            ],
        ),
        PassiveServiceConfig(
            type="bash",
            owner="bash",
            version="8.1.0",
            local=True,
            access_level=AccessLevel.ELEVATED,
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.2.10"), IPNetwork("192.168.2.0/24"))],
    shell="",
    id="developer",
)


client3 = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="bash",
            owner="bash",
            version="8.1.0",
            local=True,
            access_level=AccessLevel.ELEVATED
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.2.12"), IPNetwork("192.168.2.0/24"))],
    shell="",
    id="client3",
)

client4 = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="bash",
            owner="bash",
            version="8.1.0",
            local=True,
            access_level=AccessLevel.ELEVATED
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.2.13"), IPNetwork("192.168.2.0/24"))],
    shell="",
    id="client4",
)

client5 = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="bash",
            owner="bash",
            version="8.1.0",
            local=True,
            access_level=AccessLevel.ELEVATED
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.2.14"), IPNetwork("192.168.2.0/24"))],
    shell="",
    id="client5",
)

wifi_client1 = NodeConfig(
    active_services=[],
    passive_services=[],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.1.10"), IPNetwork("192.168.1.0/24"))],
    shell="",
    id="wifi_client1"
)

wifi_client2 = NodeConfig(
    active_services=[],
    passive_services=[],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.1.11"), IPNetwork("192.168.1.0/24"))],
    shell="",
    id="wifi_client2"
)

wifi_client3 = NodeConfig(
    active_services=[],
    passive_services=[],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.1.12"), IPNetwork("192.168.1.0/24"))],
    shell="",
    id="wifi_client3"
)


wifi_client4 = NodeConfig(
    active_services=[],
    passive_services=[],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.1.13"), IPNetwork("192.168.1.0/24"))],
    shell="",
    id="wifi_client4"
)

wifi_client5 = NodeConfig(
    active_services=[],
    passive_services=[],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.1.14"), IPNetwork("192.168.1.0/24"))],
    shell="",
    id="wifi_client5"
)


# -----------------------------------------------------------------------------
# Router between the Outside and the DMZ
# -----------------------------------------------------------------------------
perimeter_router = RouterConfig(
    interfaces=[
        # PortConfig(index=0),  # Future port or internal router (not implemented yet)
    ],
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.DENY,
            chains=[
                FirewallChainConfig(
                    type=FirewallChainType.FORWARD,
                    policy=FirewallPolicy.DENY,
                    # Enable free flow of packets between outside and DMZ
                    rules=[],
                )
            ],
        )
    ],
    id="perimeter_router",
)

# -----------------------------------------------------------------------------
# Internal router
# -----------------------------------------------------------------------------
internal_router = RouterConfig(
    interfaces=[
        InterfaceConfig(IPAddress("192.168.2.1"), IPNetwork("192.168.2.0/24"), index=0),
        InterfaceConfig(IPAddress("192.168.2.1"), IPNetwork("192.168.2.0/24"), index=1),
        InterfaceConfig(IPAddress("192.168.2.1"), IPNetwork("192.168.2.0/24"), index=2),
        InterfaceConfig(IPAddress("192.168.2.1"), IPNetwork("192.168.2.0/24"), index=3),
        InterfaceConfig(IPAddress("192.168.2.1"), IPNetwork("192.168.2.0/24"), index=4),
        InterfaceConfig(IPAddress("192.168.3.1"), IPNetwork("192.168.3.0/24"), index=5),
        InterfaceConfig(IPAddress("192.168.3.1"), IPNetwork("192.168.3.0/24"), index=6),
        InterfaceConfig(IPAddress("192.168.3.1"), IPNetwork("192.168.3.0/24"), index=7),
        InterfaceConfig(IPAddress("192.168.3.1"), IPNetwork("192.168.3.0/24"), index=8),
        InterfaceConfig(IPAddress("192.168.3.1"), IPNetwork("192.168.3.0/24"), index=9),
    ],
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.DENY,
            chains=[
                FirewallChainConfig(
                    type=FirewallChainType.FORWARD,
                    policy=FirewallPolicy.DENY,
                    rules=[
                        # Enable traffic flow between the three networks
                        FirewallRule(
                            src_net=IPNetwork("192.168.2.0/24"),
                            dst_net=IPNetwork("192.168.3.0/24"),
                            service="*",
                            policy=FirewallPolicy.ALLOW,
                        ),
                        FirewallRule(
                            src_net=IPNetwork("192.168.3.0/24"),
                            dst_net=IPNetwork("192.168.2.0/24"),
                            service="*",
                            policy=FirewallPolicy.ALLOW,
                        ),
                        FirewallRule(
                            src_net=IPNetwork("192.168.1.0/24"),
                            dst_net=IPNetwork("192.168.2.0/24"),
                            service="*",
                            policy=FirewallPolicy.DENY,
                        ),
                        FirewallRule(
                            src_net=IPNetwork("192.168.1.0/24"),
                            dst_net=IPNetwork("192.168.3.0/24"),
                            service="*",
                            policy=FirewallPolicy.DENY,
                        ),
                    ],
                )
            ]
        )
    ],
    id="internal_router",
)

wifi_router = RouterConfig(
    interfaces=[
        # PortConfig(index=0),  # Future port for perimeter router (not implemented yet)
        InterfaceConfig(IPAddress("192.168.1.1"), IPNetwork("192.168.1.0/24"), index=1),
    ],
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.DENY,
            chains=[FirewallChainConfig(type=FirewallChainType.FORWARD, policy=FirewallPolicy.DENY, rules=[])],
        )
    ],
    id="wifi_router",
)

inside_connections = [
    ConnectionConfig("wordpress_node", 0, "internal_router", 5),
    ConnectionConfig("wordpress_db_node", 0, "internal_router", 6),
    ConnectionConfig("haraka_node", 0, "internal_router", 7),
    ConnectionConfig("postgres_node", 0, "internal_router", 8),
    ConnectionConfig("chat_node", 0, "internal_router", 9),
    ConnectionConfig("developer", 0, "internal_router", 0),
    ConnectionConfig("client3", 0, "internal_router", 1),
    ConnectionConfig("client4", 0, "internal_router", 2),
    ConnectionConfig("client5", 0, "internal_router", 3),
    ConnectionConfig("wifi_client1", 0, "wifi_router", -1),
    ConnectionConfig("wifi_client2", 0, "wifi_router", -1),
    ConnectionConfig("wifi_client3", 0, "wifi_router", -1),
    ConnectionConfig("wifi_client4", 0, "wifi_router", -1),
    ConnectionConfig("wifi_client5", 0, "wifi_router", -1),
]

# router_connections = [
#     ConnectionConfig("perimeter_router", -1, "internal_router", -1),
#     ConnectionConfig("perimeter_router", -1, "wifi_router", -1),
# ]

perimeter_connections = [
    ConnectionConfig("attacker_node", 0, "perimeter_router", -1),
]

# Exploits
vsftpd_exploit = ExploitConfig(
    [VulnerableServiceConfig("vsftpd", "2.3.4")],
    ExploitLocality.REMOTE,
    ExploitCategory.CODE_EXECUTION,
)

nodes = [
    scripted_attacker,
    wordpress_srv,
    wordpress_db,
    vsftpd_srv,
    postgres_srv,
    chat_srv,
    haraka_srv,
    developer,
    client3,
    client4,
    client5,
    wifi_client1,
    wifi_client2,
    wifi_client3,
    wifi_client4,
    wifi_client5,
]
routers = [perimeter_router, internal_router, wifi_router]
attacker = scripted_attacker
connections = [*perimeter_connections, *inside_connections]
exploits = [vsftpd_exploit]
all_config_items = [*nodes, *routers, *connections, *exploits]
