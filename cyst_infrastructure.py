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
            AccessLevel.LIMITED,
            id="attacker_service",
        )
    ],
    passive_services=[
        PassiveServiceConfig(
            type="jtr",
            owner="jtr",
            version="1.9.0",
            local=True,
            access_level=AccessLevel.LIMITED,
            id="jtr_service",
        ),
        PassiveServiceConfig(
            type="empire",
            owner="empire",
            version="4.10.0",
            local=True,
            access_level=AccessLevel.LIMITED,
            id="empire_service",
        ),
        PassiveServiceConfig(
            type="msf",
            owner="msf",
            version="0",
            local=True,
            access_level=AccessLevel.LIMITED,
            id="msf_service",
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.90.30"), IPNetwork("192.168.90.0/24"))],
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
            type="wordpress_app",
            owner="wordpress",
            version="6.1.1",
            local=False,
            access_level=AccessLevel.LIMITED,
            id="wordpress_app",
            authentication_providers=[local_password_auth("wordpress_app_pwd")],
            access_schemes=[
                AccessSchemeConfig(
                    authentication_providers=["wordpress_app_pwd"],
                    authorization_domain=AuthorizationDomainConfig(
                        type=AuthorizationDomainType.LOCAL,
                        authorizations=[AuthorizationConfig("wordpress", AccessLevel.ELEVATED)],
                    ),
                )
            ],
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.93.11"), IPNetwork("192.168.93.0/24"))],
    shell="",
    id="wordpress_app_node",
)

wordpress_db = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            type="wordpress_db",
            owner="mysql",
            version="8.0.31",
            local=False,
            access_level=AccessLevel.LIMITED,
            id="wordpress_db",
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.93.10"), IPNetwork("192.168.93.0/24"))],
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
            access_level=AccessLevel.LIMITED,
            id="vsftpd_service",
        )
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.92.20"), IPNetwork("192.168.92.0/24"))],
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
            id="postgres_service",
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
    interfaces=[InterfaceConfig(IPAddress("192.168.92.21"), IPNetwork("192.168.92.0/24"))],
    shell="",
    id="postgres_node",
)

# -----------------------------------------------------------------------------
# User PC server
# - used for scenarios 2, 3, and 4
# -----------------------------------------------------------------------------
user_pc = NodeConfig(
    active_services=[],
    passive_services=[
        PassiveServiceConfig(
            id="ssh_service",
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
            id="bash_service",
        ),
    ],
    traffic_processors=[],
    interfaces=[InterfaceConfig(IPAddress("192.168.91.20"), IPNetwork("192.168.91.0/24"))],
    shell="",
    id="user_node",
)

# -----------------------------------------------------------------------------
# Router between the Outside and the DMZ
# -----------------------------------------------------------------------------
perimeter_router = RouterConfig(
    interfaces=[
        # PortConfig(index=0),  # Future port or internal router (not implemented yet)
        InterfaceConfig(IPAddress("192.168.90.1"), IPNetwork("192.168.90.0/24"), index=1),
        InterfaceConfig(IPAddress("192.168.93.1"), IPNetwork("192.168.93.0/24"), index=2),
    ],
    traffic_processors=[
        FirewallConfig(
            default_policy=FirewallPolicy.DENY,
            chains=[
                FirewallChainConfig(
                    type=FirewallChainType.FORWARD,
                    policy=FirewallPolicy.DENY,
                    # Enable free flow of packets between outside and DMZ
                    rules=[
                        FirewallRule(
                            src_net=IPNetwork("192.168.90.0/24"),
                            dst_net=IPNetwork("192.168.93.0/24"),
                            service="*",
                            policy=FirewallPolicy.ALLOW,
                        ),
                        FirewallRule(
                            src_net=IPNetwork("192.168.93.0/24"),
                            dst_net=IPNetwork("192.168.90.0/24"),
                            service="*",
                            policy=FirewallPolicy.ALLOW,
                        ),
                    ],
                )
            ],
        )
    ],
    id="perimeter_router",
)

perimeter_connections = [
    ConnectionConfig("attacker_node", 0, "perimeter_router", 0),
    ConnectionConfig("wordpress_node", 1, "perimeter_router", 1),
]

# -----------------------------------------------------------------------------
# Internal router
# -----------------------------------------------------------------------------
internal_router = RouterConfig(
    interfaces=[
        # PortConfig(index=0),  # Future port for perimeter router (not implemented yet)
        InterfaceConfig(IPAddress("192.168.91.1"), IPNetwork("192.168.91.0/24"), index=1),
        InterfaceConfig(IPAddress("192.168.92.1"), IPNetwork("192.168.92.0/24"), index=2),
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
                            src_net=IPNetwork("192.168.91.0/24"),
                            dst_net=IPNetwork("192.168.92.0/24"),
                            service="*",
                            policy=FirewallPolicy.ALLOW,
                        ),
                        FirewallRule(
                            src_net=IPNetwork("192.168.92.0/24"),
                            dst_net=IPNetwork("192.168.91.0/24"),
                            service="*",
                            policy=FirewallPolicy.ALLOW,
                        ),
                    ],
                )
            ],
        )
    ],
    id="internal_router",
)

inside_connections = [
    ConnectionConfig("vsftpd_node", 0, "internal_router", 2),
    ConnectionConfig("postgres_node", 0, "internal_router", 2),
    ConnectionConfig("user_node", 0, "internal_router", 1),
]

router_connections = [ConnectionConfig("perimeter_router", 0, "internal_router", 0)]

# Exploits
vsftpd_exploit = ExploitConfig(
    [VulnerableServiceConfig("vsftpd", "2.3.4")],
    ExploitLocality.REMOTE,
    ExploitCategory.CODE_EXECUTION,
)

nodes = [wordpress_srv, vsftpd_srv, postgres_srv, user_pc, scripted_attacker]
attacker = scripted_attacker
routers = [perimeter_router, internal_router]
connections = [*perimeter_connections, *inside_connections]
exploits = [vsftpd_exploit]
all_config_items = [*nodes, *routers, *connections, *exploits]
