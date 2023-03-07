import random
from typing import Tuple, Callable

from cyst.api.environment.configuration import EnvironmentConfiguration
from cyst.api.environment.interpreter import ActionInterpreter, ActionInterpreterDescription
from cyst.api.environment.message import Request, Response, Status, StatusOrigin, StatusValue
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.policy import EnvironmentPolicy
from cyst.api.environment.resources import EnvironmentResources
from cyst.api.logic.access import AccessLevel, AuthenticationToken
from cyst.api.logic.action import ActionDescription, ActionToken, ActionParameterType, ActionParameterDomain, ActionParameterDomainType, ActionParameter
from cyst.api.logic.exploit import ExploitCategory
from cyst.api.network.node import Node


class MVModel(ActionInterpreter):
    def __init__(self, configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                 policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> None:

        self._configuration = configuration
        self._action_store = resources.action_store
        self._exploit_store = resources.exploit_store
        self._policy = policy
        self._messaging = messaging

        self._action_store.add(ActionDescription("mv:scan",
                                                 "Execution of a scan that reveals also service details",
                                                 [],
                                                 [(ActionToken.NONE, ActionToken.NONE)]))

        self._action_store.add(ActionDescription("mv:bruteforce",
                                                 "Execution of a password bruteforce",
                                                 [ActionParameter(ActionParameterType.IDENTITY, "username", configuration.action.create_action_parameter_domain_any())],
                                                 [(ActionToken.NONE, ActionToken.NONE)]))

        self._action_store.add(ActionDescription("mv:create_session",
                                                 "Upload a reverse shell and initiate a connection",
                                                 [],
                                                 [(ActionToken.NONE, ActionToken.NONE)]))

        self._action_store.add(ActionDescription("mv:credentials_extraction",
                                                 "Exfiltrate data from target service",
                                                 [],
                                                 [(ActionToken.NONE, ActionToken.NONE)]))

        self._action_store.add(ActionDescription("mv:data_exfiltration",
                                                 "Exfiltrate data from target service",
                                                 [],
                                                 [(ActionToken.NONE, ActionToken.NONE)]))

    def evaluate(self, message: Request, node: Node) -> Tuple[int, Response]:
        if not message.action:
            raise ValueError("Action not provided")

        action_name = "_".join(message.action.fragments)
        fn: Callable[[Request, Node], Tuple[int, Response]] = getattr(self, "process_" + action_name, self.process_default)
        return fn(message, node)

    def process_default(self, message: Request, node: Node) -> Tuple[int, Response]:
        print("Could not evaluate message. Tag in `mv` namespace unknown. " + str(message))
        return 0, self._messaging.create_response(message, status=Status(StatusOrigin.SYSTEM, StatusValue.ERROR), session=message.session)

    def process_scan(self, message: Request, node: Node) -> Tuple[int, Response]:
        services = []
        for service in node.services.values():
            if service.passive_service:
                services.append((service.name, service.passive_service.version))
        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=message.session, auth=message.auth, content=services)

    def process_bruteforce(self, message: Request, node: Node) -> Tuple[int, Response]:
        # Bruteforce is modelled here to always succeed. The time it takes is a random number
        time = random.randint(1, 20)
        # Sanity check
        error = ""
        if message.dst_service not in node.services:
            error = f"Service {message.dst_service} not present at a node"
        elif node.services[message.dst_service].passive_service.local:
            error = f"Service {message.dst_service} is local."

        if error:
            return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.ERROR),
                                                      session=message.session, auth=message.auth, content=error)

        # returns only the first authorization (for DEMO purposes only)
        auths = self._policy.get_authorizations(node, message.dst_service)
        return time, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                     session=message.session, auth=auths[0])

    def process_create_session(self, message: Request, node: Node) -> Tuple[int, Response]:
        error = ""
        if not message.auth and not message.action.exploit:
            error = f"Neither authorization or exploit set"
        elif message.auth and not self._policy.decide(node, message.dst_service, AccessLevel.LIMITED, message.auth):
            error = "No valid authorization provided"
        elif message.action.exploit and message.action.exploit.category != ExploitCategory.CODE_EXECUTION:
            error = "Wrong exploit type used"
        elif message.action.exploit and not self._exploit_store.evaluate_exploit(message.action.exploit, message, node):
            error = "Exploit not applicable"

        if error:
            return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.ERROR),
                                                      session=message.session, auth=message.auth, content=error)

        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=self._configuration.network.create_session_from_message(message), auth=message.auth)

    def process_credentials_extraction(self, message: Request, node: Node) -> Tuple[int, Response]:
        error = ""
        if not message.dst_service:
            error = "Target service not specified"

        if error:
            return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.ERROR),
                                                      session=message.session, auth=message.auth, content=error)

        result = []
        for d in self._configuration.service.private_data(node.services[message.dst_service].passive_service):
            if issubclass(type(d), AuthenticationToken):
                result.append(d)

        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=self._configuration.network.create_session_from_message(message),
                                                  auth=message.auth, content=result)

    def process_data_exfiltration(self, message: Request, node: Node) -> Tuple[int, Response]:
        error = ""
        if not message.auth:
            error = "Failed to provide authentication"
        elif not self._policy.decide(node, message.dst_service, AccessLevel.LIMITED, message.auth):
            error = "Provided authentication is not enough to get the data"

        if error:
            return 1, self._messaging.create_response(message, status=Status(StatusOrigin.NODE, StatusValue.ERROR),
                                                      session=message.session, auth=message.auth, content=error)

        result = []
        for d in self._configuration.service.private_data(node.services[message.dst_service].passive_service):
            if d.owner == message.auth.identity:
                result.append(d)

        return 1, self._messaging.create_response(message, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                                                  session=self._configuration.network.create_session_from_message(message),
                                                  auth=message.auth, content=result)


def create_mv_model(configuration: EnvironmentConfiguration, resources: EnvironmentResources,
                    policy: EnvironmentPolicy, messaging: EnvironmentMessaging) -> ActionInterpreter:
    model = MVModel(configuration, resources, policy, messaging)
    return model


action_interpreter_description = ActionInterpreterDescription(
    "mv",
    "Behavioral model tailored for the demo of BEAST project",
    create_mv_model
)
