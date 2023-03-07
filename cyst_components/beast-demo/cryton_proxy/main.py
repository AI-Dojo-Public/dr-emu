# Python modules to use this Proxy must be installed via pip
import cyst.api.logic.action
import requests as requests
from importlib_metadata import entry_points
from typing import Optional, Any, Union
from netaddr import IPAddress
from copy import deepcopy

from cyst.api.logic.exploit import Exploit, VulnerableService, ExploitLocality, ExploitCategory, ExploitParameter, ExploitParameterType
from cyst.core.logic.exploit import VulnerableServiceImpl, ExploitParameterImpl, ExploitImpl

from cyst.api.environment.environment import Environment
from cyst.api.environment.message import Request, Status, Message, Response, MessageType, StatusValue, Status, StatusOrigin, StatusDetail
from cyst.api.environment.messaging import EnvironmentMessaging
from cyst.api.environment.resources import EnvironmentResources, ActionStore, ExploitStore, Clock, Statistics
from cyst.api.host.service import ActiveService
from cyst.api.logic.access import Authorization, AuthenticationTarget, AuthenticationToken
from cyst.api.logic.action import Action, ActionParameter, ActionParameterType
from cyst.api.network.session import Session

from cyst.core.network.session import SessionImpl
from cyst_services.scripted_actor.main import ScriptedActorControl

from cyst.api.logic.access import AuthenticationTokenType, AuthenticationTokenSecurity
from cyst.core.logic.access import AuthenticationTokenImpl

from cyst.core.environment.message import MessageImpl
from cyst.core.network.elements import Endpoint, Hop

import requests
import yaml
import time
import uuid

from cryton_proxy.action_database import CrytonAction, MvScan, MvBruteforce, MvCreateSession, MvCredentialsExtraction, MvDataExfiltration, CystProxyAction

import cryton_proxy.action_database as action_database


TEMPLATE = {
    "plan": {
        "name": "Dynamic plan equivalent",
        "owner": "Cryton AI",
        "dynamic": True,
        "stages": [
            {
                "name": "Global stage",
                "trigger_type": "delta",
                "trigger_args": {
                    "seconds": 0
                },
                "steps": []
            }
        ]
    }
}

def get_request(api_url: str, parameters: dict = None) -> requests.Response:
    try:
        response = requests.get(api_url, json=parameters)
    except requests.exceptions.ConnectionError:
        return RuntimeError
    except requests.exceptions.HTTPError:
        return RuntimeError
    except requests.exceptions.Timeout:
        return RuntimeError
    
    print(response.json())
    return response


def post_request(api_url: str, parameters: dict = None, files: dict = None, data: dict = None) -> requests.Response:
    try:
        response = requests.post(api_url, data=data, files=files)
    except requests.exceptions.ConnectionError:
        raise RuntimeError
    except requests.exceptions.HTTPError:
        raise RuntimeError
    except requests.exceptions.Timeout:
        raise RuntimeError
    
    print(response.json())
    return response

def activate_worker(url: str, name: str, description: str) -> list:
    ids = []
    api_response = get_request(api_url=url + 'workers/')

    for worker in api_response.json():
        if 'state' not in worker:
            # worker not yet created
            break
            
        if worker['name'] == name and worker['state'] == 'UP':
            # If the desired worker already exists, there is no need to create it again
            ids.append(worker['id'])
            return ids
    
        elif worker['name'] == name and worker['state'] == 'DOWN':
            # If the desired worker already exists, but in DOWN state, it may be a state after a connection loss and error
            # right after creating the worker in the last run.
            
            # Healthcheck worker ("wake-up" message)
            api_response = post_request(api_url=url + f"workers/{worker['id']}/healthcheck/")
            if api_response.json()['state'] == 'UP':
                # The worker was able to wake up
                ids.append(worker['id'])
                return ids
            
            # Worker cannot wake up, (Cryton may be incorrectly installed)
            return []

    print('creating worker')

    worker_json = {"name": Proxy.cryton_worker_name, "description": Proxy.cryton_worker_description}
    
    api_response = requests.post(url=Proxy.api_root + 'workers/', data=worker_json)

    worker_id = api_response.json()['id']
    # Healthcheck worker (Worker will be DOWN otherwise)
    api_response = post_request(api_url=Proxy.api_root + f"workers/{worker_id}/healthcheck/")

    ids.append(worker_id)
    return ids


class Proxy(EnvironmentMessaging, EnvironmentResources):

    cryton_worker_id = []
    cryton_worker_name = 'attacker'
    cryton_worker_description = ''

    # ActionStore, which is promoted to agents
    cryton_action_store = []
    proxy_exploit_store = []

    cryton_ip = 'cryton-app'
    cryton_port = 8000
    api_root = f'http://{cryton_ip}:{cryton_port}/api/'

    def open_session(self, request: Request):
        pass

    def add_session(self, session: dict):
        self.sessions.append(session)
    
    def get_cyst_session(self, session_name: str):
        for session in self.sessions:
            if session['name'] == session_name:
                return session['cyst_session']

    def register_service(self, node_name, service_name, attacker_service):
        self.agents.append({'node_name': node_name, 'service_name': service_name, 'attacker_service': attacker_service})

    def __init__(self, messaging: EnvironmentMessaging, resources: EnvironmentResources):
        self._messaging = messaging
        self._resources = resources

        vsftpd_exploit = ExploitImpl('vsftpd', [VulnerableServiceImpl("vsftpd", "2.3.4", "2.3.4")], ExploitLocality.REMOTE, ExploitCategory.CODE_EXECUTION)
        self._resources.exploit_store.add_exploit(vsftpd_exploit)

        self.agents = []
        self.sessions = []

        self.run_id = 0
        self.plan_id = 0
        self.stage_id = 0
        self.cyst_actions_count = 0 # used to construct a unique Stage name
        self.unfinished_cyst_actions = []

        # filter actions (only those actions which are possible to execute in Cryton should be added into the cryton action store)
        all_actions = self._resources.action_store.get_prefixed('')

        for action in all_actions:
            if action in action_database.action_ids_to_propagate:
                self.cryton_action_store.append(action)


        Proxy.cryton_worker_id = activate_worker(url=Proxy.api_root, name=Proxy.cryton_worker_name, description=Proxy.cryton_worker_description)
        if not Proxy.cryton_worker_id:
            # Cryton is running, but worker is not able to start
            raise RuntimeError
        
        api_root = Proxy.api_root

        # 1. Create a template
        r_create_template = requests.post(f"{api_root}templates/", files={"file": yaml.dump(TEMPLATE)})
        template_id = r_create_template.json()['id']
        print(f"Template id: {template_id}")

        # 2. Create a Plan
        r_create_plan = requests.post(f"{api_root}plans/", data={'template_id': template_id})
        self.plan_id = r_create_plan.json()['id']
        print(f"Plan id: {self.plan_id}")

        # 3. Get Stage ID
        self.stage_id = requests.get(f"{api_root}stages/", {"plan_model_id": self.plan_id}).json()[0]['id']
        # print(self.stage_id)

        # 4. Create a new Run
        r_create_run = requests.post(f"{api_root}runs/", data={'plan_id': self.plan_id, "worker_ids": [self.cryton_worker_id]})
        self.run_id = r_create_run.json()["id"]
        print(f"Run id: {self.run_id}")

        # 5. Get Stage execution ID
        self.stage_ex_id = requests.get(f"{api_root}runs/{self.run_id}/report/") \
        .json()["detail"]["plan_executions"][0]["stage_executions"][0]["id"]

        # 6. Execute the Run
        r_execute_run = requests.post(f"{api_root}runs/{self.run_id}/execute/", data={'run_id': self.run_id})
        print(f"Run response: {r_execute_run.text}")
        
        # Stages are not used in this demo
        # # create empty (dynamic) Plan
        # # 1. create Plan Template
        # template = {'file': yaml.dump(Proxy.plan)}
        # api_response = post_request(api_url=Proxy.api_root + 'templates/', files=template)

        # template_id = api_response.json()['id']

        # # Create stage
        # cyst_action.cryton_stage_id = self.create_stage(cyst_action)

        # # 2. Create Plan instance
        # api_response = post_request(api_url=Proxy.api_root + 'plans/', data={'template_id': template_id})

        # self.plan_id = api_response.json()['id']

        # api_response = requests.post(url=Proxy.api_root + 'runs/',
        #                                     json={'plan_id': self.plan_id, 'worker_ids': Proxy.cryton_worker_id})

        # self.run_id = api_response.json()['id']

        # # Execute Run (in this case of Dynamic Runs, the Run must be started before Stages and Steps are added to it)
        # api_response = post_request(api_url=Proxy.api_root + f'runs/{self.run_id}/execute/')

    def create_step(self, step: dict) -> int:
        r_create_step = requests.post(f"{Proxy.api_root}steps/", data={'stage_id': self.stage_id}, files={"file": yaml.dump(step)})
        print(r_create_step.json())
        step_id = r_create_step.json()['id']
        print(f"Step id: {step_id}")

        return step_id

    def execute_step(self, step_id: int, stage_execution_id: int) -> int:
        r_execute_step = requests.post(f"{Proxy.api_root}steps/{step_id}/execute/",
                                    data={'stage_execution_id': stage_execution_id})
        print(f"Step execution started: {r_execute_step.text}")
        return r_execute_step.json()["execution_id"]


    def wait_for_step(self, step_execution_id: int):
        while requests.get(f"{Proxy.api_root}step_executions/{step_execution_id}/").json()["state"] != "FINISHED":
            time.sleep(3)
        print("Step execution finished.")

    # Stages are  not used in this demo

    # def create_stage(self, cyst_action: CystProxyAction) -> int:
    #     # Files needed for stage creation
    #     files = {
    #         'file': Proxy.stage_template,
    #         'inventory_file': yaml.dump({'name': f'{cyst_action.request.action.id} {self.cyst_actions_count}', 'delay': cyst_action.delay})
    #         }
        
    #     # Create new Stage under Plan
    #     api_response = post_request(api_url=Proxy.api_root + 'stages/', data={'plan_id': self.plan_id},
    #                                 files=files)

    #     return api_response.json()['id']
    
    # def add_step_to_stage(self, cryton_action: CrytonAction, stage_id: int, template = dict):
    
    #     # Create Steps (based on cyst action) under Stage
    #     files = {'file': yaml.dump(template)}        
    #     api_response = post_request(api_url=Proxy.api_root + 'steps/', data={'stage_id': stage_id}, files=files)
        
    #     cryton_action.cryton_step_id = api_response.json()['id']
    
    def send_message(self, message: Message, delay: int = 0) -> None:
        request = message.cast_to(Request)
        
        MessageImpl.cast_from(message).set_origin(Endpoint(id='id', port=0, ip=IPAddress('192.168.0.2')))
        
        print('\n-------------------------------------------------------')
        print(f'Attacker executed action {request.action.id} on target {request.dst_ip}')
        print()

        # Each CYST actions will init. all Cryton actions they need
        if request.action.id == 'mv:scan':
            cyst_action = MvScan(message)
        elif request.action.id == 'mv:bruteforce':
            cyst_action = MvBruteforce(message)
        elif request.action.id == 'mv:create_session':
            cyst_action = MvCreateSession(message)
        elif request.action.id == 'mv:credentials_extraction':
            cyst_action = MvCredentialsExtraction(message)
        elif request.action.id == 'mv:data_exfiltration':
            cyst_action = MvDataExfiltration(message)
        
        print('Executing Cryton actions: ', end="")
        for i, cryton_action in enumerate(cyst_action.cryton_actions):
            if i:
                print(', ', end="")
            print(cryton_action.cryton_action_name, end="")
        print()

        # cyst_action.message = message
        cyst_action.delay = delay
        self.cyst_actions_count += 1

        # # Create stage
        # cyst_action.cryton_stage_id = self.create_stage(cyst_action)

        # Add all Cryton actions associated with CYST action into the dynamic plan
        for i, cryton_action in enumerate(cyst_action.cryton_actions):
            template = deepcopy(cryton_action.action_template)

            cryton_action.cryton_step_id = self.create_step(template)
            
            execution_id = self.execute_step(cryton_action.cryton_step_id, self.stage_ex_id)
            cryton_action.cryton_step_ex_id = execution_id
            
            self.wait_for_step(execution_id)
            
            # self.add_step_to_stage(cryton_action, stage_id=cyst_action.cryton_stage_id, template=template)

        # # Execute Stage
        # api_response = post_request(api_url=Proxy.api_root + f'stages/{cyst_action.cryton_stage_id}/start_trigger/', data={'plan_execution_id': self.run_id})

        # self.unfinished_cyst_actions.append(cyst_action)

        # So far, the response processing is busy-waiting, but can process multiple actions
        response = self.cryton_responses_processing(cyst_action)
        
        print('CYST action finished.')
        
        for agent in self.agents:
            agent['attacker_service'].process_message(response)

    def create_request(self, dst_ip: Union[str, IPAddress], dst_service: str = "", action: Optional[Action] = None,
                       session: Optional[Session] = None,
                       auth: Optional[Union[Authorization, AuthenticationToken]] = None) -> Request:

        if action.id not in action_database.action_ids_to_propagate:
            raise NotImplementedError
        
        return self._messaging.create_request(dst_ip, dst_service, action, session, auth)

    def process_mv_scan(self, cyst_action: CystProxyAction):
        cryton_action = cyst_action.cryton_actions[0]
        
        # each scan has its own implementation of get_output()
        # content = cryton_action.get_content()

        content = []

        # for the purpose of demo
        if cryton_action.cryton_action_name == 'scan-dmz':
            content = None

        elif cryton_action.cryton_action_name == 'scan-user-machine':
            content = [('ssh', '5.1.4')]
        
        elif cryton_action.cryton_action_name == 'scan-wordpress-site':
            content = [('wordpress_app', ('6.1.1'))]
        
        elif cryton_action.cryton_action_name == 'scan-database-server':
            content = [('postgres', '10.5.0')]
        
        elif cryton_action.cryton_action_name == 'scan-ftp-server':
            content = [('vsftpd', '2.3.4')]
    
        return self.create_response(cyst_action.request, Status(StatusOrigin.NETWORK, StatusValue.SUCCESS),
             session=cyst_action.message.session, auth=cyst_action.message.auth, content=content)
    
    def process_mv_bruteforce(self, cyst_action: CystProxyAction):
        
        # bruteforcing to user machine or bruteforce the server?

        # universal method based on CrytonAction classes method
        # token_content = cyst_action.cryton_actions[0].get_output()
        # identity = token_content[0]
        # content = token_content[1]

        # # for demo purpose
        # if cyst_action.cryton_actions[0].cryton_action_name == 'get-wordpress-credentials':
        #     token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, identity="user", is_local=False)
        if cyst_action.cryton_actions[0].cryton_action_name == 'bruteforce-user':
            token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN,
             identity='beast-user', is_local=True)._set_content(uuid.uuid4())
            
            hop = Hop(Endpoint('1', 0), Endpoint('2', 0))

            session_to_user = {'name': 'session-to-user', 'id': 3, 'cyst_session': SessionImpl(owner='attacker', parent=None, path=[hop])}
            self.add_session(session_to_user)
        

        if cyst_action.cryton_actions[0].cryton_action_name == 'get-wordpress-credentials':
            token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN,
             identity='beast-user', is_local=True)._set_content(uuid.uuid4())
        

        return self.create_response(cyst_action.request, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
             session=cyst_action.message.session, auth=cyst_action.message.auth, content=token)
    
    def process_mv_create_session(self, cyst_action: CystProxyAction):
    
        # create session to user - session already created when bruteforcing user
        if not cyst_action.cryton_actions:
            return self.create_response(request=cyst_action.request, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                session=self.get_cyst_session('session-to-user'), auth=cyst_action.message.auth)

        # session to worpress
        cryton_action = cyst_action.cryton_actions[0]

        if cryton_action.cryton_action_name == 'upload-php-shell':
            hop = Hop(Endpoint('1', 0), Endpoint('2', 0))
            session = {'name': cryton_action.get_msf_session_name(), 'id': cryton_action.get_msf_session_id(), 'cyst_session': SessionImpl(owner='attacker', parent=None, path=[hop])}
            self.add_session(session)
        
        else: # exploit-ftp-server
            hop = Hop(Endpoint('1', 0), Endpoint('2', 0))
            session = {'name': cryton_action.get_msf_session_name(), 'id': cryton_action.get_msf_session_id(), 'cyst_session': SessionImpl(owner='attacker', parent=None, path=[hop])}
            self.add_session(session)
        
        return self.create_response(request=cyst_action.request, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                session=session['cyst_session'], auth=cyst_action.message.auth)

    def process_mv_credentials_extraction(self, cyst_action: CystProxyAction):
        cryton_action_name = cyst_action.cryton_actions[0].cryton_action_name


        # from wordpress
        if cryton_action_name == 'get-wordpress-credentials':
            session = SessionImpl(owner='attacker', parent=None, path=[Endpoint(IPAddress('127.0.0.1')), Endpoint(id='id', port=0, ip=IPAddress('127.0.0.1'))])
            # session = self._configuration.network.create_session_from_message(cyst_action.message)

            return self.create_response(request=cyst_action.request, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                    session=session, auth=cyst_action.message.auth)

        # from database
        elif cryton_action_name == 'read-ftp-logs':
            
            # for demo purpose
            identity = 'beast-user'
            token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, identity=identity, is_local=True)
    
            return self.create_response(request=cyst_action.request, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                    session=cyst_action.message.session, auth=cyst_action.message.auth, content=[token])


        # from user
        elif cryton_action_name == 'check-user-bash-history': 
            
            # for demo purpose
            identity = 'beastdb'
            token = AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, AuthenticationTokenSecurity.OPEN, identity=identity, is_local=True)
    
            return self.create_response(request=cyst_action.request, status=Status(StatusOrigin.SERVICE, StatusValue.SUCCESS),
                    session=cyst_action.message.session, auth=cyst_action.message.auth, content=[token])
            

    def process_mv_data_exfiltration(self, cyst_action: CystProxyAction):
        # get-data-from-database

        content = cyst_action.cryton_actions[0].get_content()
        return self.create_response(cyst_action.request, Status(StatusOrigin.SERVICE, StatusValue.SUCCESS), 
            session=cyst_action.message.session, auth=cyst_action.message.auth, content=[content])


    def cryton_responses_processing(self, cyst_action: CystProxyAction):

        # while requests.get(f"{Proxy.api_root}stage_executions/{cyst_action.cryton_stage_id}").json()["state"] != "FINISHED":
        #     time.sleep(1)

        # Test that all cryton_actions asociated with cyst action ended successfuly
        success = True
        for cryton_action in cyst_action.cryton_actions:

            cryton_action.report = get_request(api_url=f"{Proxy.api_root}step_executions/{cryton_action.cryton_step_ex_id}/report/").json()
            print()

            # implementation of is_success differs between actions
            if not cryton_action.is_success():
                success = False

        if not success:
            if cyst_action.outcome['origin'] == 'NETWORK':
                response = self.create_response(cyst_action.request,
                    Status(StatusOrigin.NETWORK, StatusValue.FAILURE), session=cyst_action.message.session, auth=cyst_action.message.auth)
            elif cyst_action.outcome['origin'] == 'SERVICE':
                response = self.create_response(cyst_action.request,
                    Status(StatusOrigin.SERVICE, StatusValue.FAILURE), session=cyst_action.message.session, auth=cyst_action.message.auth)

            return response


        # process success actions
        cyst_action_id = cyst_action.cyst_action_id

        if cyst_action_id == 'mv:scan':
            response = self.process_mv_scan(cyst_action)
            
        elif cyst_action_id == 'mv:bruteforce':
            response = self.process_mv_bruteforce(cyst_action)

        elif cyst_action_id == 'mv:create_session':
            response = self.process_mv_create_session(cyst_action)

        elif cyst_action_id == 'mv:credentials_extraction':
            response = self.process_mv_credentials_extraction(cyst_action)

        elif cyst_action_id == 'mv:data_exfiltration':
            response = self.process_mv_data_exfiltration(cyst_action)

        return response
        
    def create_response(self, request: Request, status: Status, content: Optional[Any] = None,
                        session: Optional[Session] = None,
                        auth: Optional[Union[Authorization, AuthenticationTarget]] = None) -> Response:
        
        return self._messaging.create_response(request, status, content, session, auth)

    def get_ref(self, id: str = "") -> Optional[Action]:
        if id in self.cryton_action_store:
            return self.cryton_action_store[id]
        return None

    def get(self, id: str = "") -> Optional[Action]:
        return self._resources.action_store.get(id)

    def get_prefixed(self, id: str = ""):
        result = []
        for action in self.cryton_action_store:
            if action.id.startwith(id):
                result.append(deepcopy(action))

        return result

    def add(self, action: cyst.api.logic.action.Action):
        self.cryton_action_store.append(action)

    @property
    def action_store(self) -> ActionStore:
        return self.action_store

    @property
    def exploit_store(self) -> ExploitStore:
        return self._resources.exploit_store

    @property
    def clock(self) -> Clock:
        return self._resources.clock

    @property
    def statistics(self) -> Statistics:
        return self._resources.statistics
