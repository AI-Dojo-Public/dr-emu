import uuid

from infrastructure import all_config_items
from netaddr import IPAddress, IPNetwork

from cyst.api.host.service import Service
from cyst.api.environment.environment import Environment
from cyst.api.environment.message import Status, StatusOrigin, StatusValue
from cyst.api.logic.access import AuthenticationTokenType, AuthenticationTokenSecurity
from cyst.api.logic.exploit import ExploitCategory

from cyst.core.logic.access import AuthenticationTokenImpl

from cyst_services.scripted_actor.main import ScriptedActorControl

# -----------------------------------------------------------------------------
# Environment configuration
# -----------------------------------------------------------------------------
env = Environment.create().configure(*all_config_items)
env.control.init()

action_list = env.resources.action_store.get_prefixed("mv")
actions = {}
for action in action_list:
    print(action.id)
    actions[action.id] = action

# Inject authentication tokens
# It complains and rightfully so, but for the purpose of the demo, this is ok
token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, identity="user", is_local=False)
env.configuration.service.private_data(env.configuration.general.get_object_by_id("vsftpd_service", Service).passive_service).append(token)

token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, identity="dbuser", is_local=True)._set_content(uuid.uuid4())
env.configuration.service.private_data(env.configuration.general.get_object_by_id("bash_service", Service).passive_service).append(token)

# -----------------------------------------------------------------------------
# Attacker preparation
# -----------------------------------------------------------------------------
attacker_service = env.configuration.general.get_object_by_id("attacker_service", Service)
assert attacker_service is not None
attacker: ScriptedActorControl = env.configuration.service.get_service_interface(attacker_service.active_service, ScriptedActorControl)

env.control.add_pause_on_response("attacker_node.scripted_attacker")
# -----------------------------------------------------------------------------
# Attack stages
# -----------------------------------------------------------------------------
current_ip = ""
current_service = ""
auth = None
session = None

# -----------------------------------------------------------------------------
# Wordpress
# -----------------------------------------------------------------------------

# DMZ scanning
for ip in IPNetwork("192.168.93.0/24").iter_hosts():
    a = actions["mv:scan"]
    attacker.execute_action(str(ip), "", a)
    env.control.run()
    response = attacker.get_last_response()
    if response.status != Status(StatusOrigin.NETWORK, StatusValue.FAILURE):
        print(response)
        current_service = response.content[0][0]
        current_ip = str(ip)
        break

# Bruteforcing the way through
a = actions["mv:bruteforce"]
attacker.execute_action(current_ip, current_service, a)
env.control.run()
response = attacker.get_last_response()
if response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS):
    print(response)
    auth = response.auth
else:
    raise RuntimeError("Failed to bruteforce the password")

# Opening a session to the wordpress
a = actions["mv:create_session"]
attacker.execute_action(current_ip, current_service, a, auth=auth)
env.control.run()
response = attacker.get_last_response()
if response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS):
    print(response)
    session = response.session
else:
    raise RuntimeError("Failed to open the session")


# -----------------------------------------------------------------------------
# FTP + DB
# -----------------------------------------------------------------------------
# Scan the server sector
ips = []
services = []
versions = []
auth_token = None

for ip in IPNetwork("192.168.92.0/24").iter_hosts():
    a = actions["mv:scan"]
    attacker.execute_action(str(ip), "", a, session)
    env.control.run()
    response = attacker.get_last_response()
    if response.status != Status(StatusOrigin.NETWORK, StatusValue.FAILURE):
        print(response)
        services.append(response.content[0][0])
        versions.append(response.content[0][1])
        ips.append(ip)

# Get the exploit for vsftpd
e = env.resources.exploit_store.get_exploit(service=services[0], category=ExploitCategory.CODE_EXECUTION)
if not e:
    raise RuntimeError(f"Failed to get exploit for service {services[0]}")

e = e[0]
# Opening a session to the FTP using an exploit
a = actions["mv:create_session"]
a.set_exploit(e)
attacker.execute_action(ips[0], services[0], a, session=session)
env.control.run()
response = attacker.get_last_response()
if response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS):
    print(response)
    session = response.session
else:
    raise RuntimeError("Failed to open the session")

# Get the authentication info from the FTP
a = actions["mv:credentials_extraction"]
attacker.execute_action(ips[0], services[0], a, session=session)
env.control.run()
response = attacker.get_last_response()
if response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS):
    print(response)
    auth_token = response.content[0]
else:
    raise RuntimeError("Failed to extract credentials")

# -----------------------------------------------------------------------------
# User machine
# -----------------------------------------------------------------------------
for ip in IPNetwork("192.168.94.0/24").iter_hosts():
    a = actions["mv:scan"]
    attacker.execute_action(str(ip), "", a, session)
    env.control.run()
    response = attacker.get_last_response()
    if response.status != Status(StatusOrigin.NETWORK, StatusValue.FAILURE):
        print(response)
        services.append(response.content[0][0])
        versions.append(response.content[0][1])
        ips.append(str(ip))

a = actions["mv:bruteforce"]
a.parameters["username"] = auth_token.identity
attacker.execute_action(ips[-1], services[-1], a, session=session)
env.control.run()
response = attacker.get_last_response()
if response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS):
    print(response)
    auth = response.auth
else:
    raise RuntimeError("Failed to bruteforce user machine")

# Opening a session to the user using obtained credentials
a = actions["mv:create_session"]
a.set_exploit(e)
attacker.execute_action(ips[-1], services[-1], a, session=session)
env.control.run()
response = attacker.get_last_response()
if response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS):
    print(response)
    session = response.session
else:
    raise RuntimeError("Failed to open the session")

# Get the authentication info from the user machine
a = actions["mv:credentials_extraction"]
attacker.execute_action(ips[-1], "bash", a, session=session)
env.control.run()
response = attacker.get_last_response()
if response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS):
    print(response)
    auth_token = response.content[0]
else:
    raise RuntimeError("Failed to extract credentials")

# -----------------------------------------------------------------------------
# DB
# -----------------------------------------------------------------------------
# Extract data from database
a = actions["mv:data_exfiltration"]
attacker.execute_action(ips[1], services[1], a, auth=auth_token, session=session)
env.control.run()
response = attacker.get_last_response()
if response.status == Status(StatusOrigin.SERVICE, StatusValue.SUCCESS):
    print(response)
    data = response.content[0]
else:
    raise RuntimeError("Failed to exfiltrate data")

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------
env.control.commit()

print(env.resources.statistics)