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
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.4.11"), IPNetwork("192.168.4.0/24"))],
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

wifi_client = NodeConfig(
    active_services=[],
    passive_services=[],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.1.10"), IPNetwork("192.168.1.0/24"))],
    shell="",
    id="wifi_client"
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
        InterfaceConfig(IPAddress("192.168.3.1"), IPNetwork("192.168.3.0/24"), index=1),
        InterfaceConfig(IPAddress("192.168.3.1"), IPNetwork("192.168.3.0/24"), index=2),

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
    ConnectionConfig("wordpress_node", 0, "internal_router", 1),
    ConnectionConfig("wordpress_db_node", 0, "internal_router", 2),
    ConnectionConfig("developer", 0, "internal_router", 0),
    ConnectionConfig("wifi_client", 0, "wifi_router", -1),

]

# router_connections = [
#     ConnectionConfig("perimeter_router", -1, "internal_router", -1),
#     ConnectionConfig("perimeter_router", -1, "wifi_router", -1),
# ]

perimeter_connections = [
    ConnectionConfig("attacker_node", 0, "perimeter_router", -1),
]

nodes = [
    scripted_attacker,
    wordpress_srv,
    wordpress_db,
    developer,
    wifi_client,
]
routers = [perimeter_router, internal_router, wifi_router]
attacker = scripted_attacker
connections = [*perimeter_connections, *inside_connections]
all_config_items = [*nodes, *routers, *connections]
