from netaddr import IPAddress, IPNetwork

PERIMETER_ROUTER = "perimeter_router"
MANAGEMENT_NETWORK_IP = IPNetwork("192.168.50.0/29")
MANAGEMENT_NETWORK_BRIDGE_IP = MANAGEMENT_NETWORK_IP[-2]
MANAGEMENT_NETWORK_NAME = "management_network"

IMAGE = "image"
COMMAND = "command"

TESTBED_INFO = {"wordpress_node": {IMAGE: "wordpress:6.1.1-apache", COMMAND: None}, "vsftpd_node": {IMAGE:"uexpl0it/vulnerable-packages:backdoored-vsftpd-2.3.4", COMMAND: None}, "postgres_node": {IMAGE: "postgres:10.5", COMMAND: None},
                "user_node": {IMAGE: "registry.gitlab.ics.muni.cz:443/ai-dojo/docker-testbed:vuln-user", COMMAND: ["sh", "-c", "service ssh start && tail -f /dev/null"]}, "attacker_node": {IMAGE: "nicolaka/netshoot", COMMAND: None}}
