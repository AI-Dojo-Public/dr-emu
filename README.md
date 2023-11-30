# AI-dojo Docker testbed
This project serves as a demonstration of semi-realistic network topology generation using a docker for AI-DOJO.

## Requirements
- [Python](https://www.python.org/) >= 3.9, < 3.12
- [Docker](https://docs.docker.com/engine/install/)

## Installation
Clone the repo:
```shell
git clone git@gitlab.ics.muni.cz:ai-dojo/docker-testbed.git
cd docker-testbed
```

## Build the infrastructure

Make sure the necessary images exist:
```shell
docker build -t base --target base .
docker build -t router --target router .
docker build -t node --target node .
```

### Private Repository
If the docker images that should be downloaded for the infrastructure are in **private repository** please edit 
**$DOCKER_TOKEN** and **$REGISTRY_URL** Environmental variables.

In **/docker-testbed/.env** change the value of: 
-   **$DOCKER_TOKEN** - access token for your private repository 
-   **$REGISTRY_URL** - url of repository's docker container registry (eg. `registry.gitlab.ics.muni.cz:443`).

Run deployment:
```shell
docker compose up -d
```

**IMPORTANT: Web application uses docker on host via mounted docker socket.**

## REST API
For REST API documentation, see `http://127.0.0.1:8000/docs`.

## CLI
Application also has a command line interface. Use the following command to invoke the app: 
```
dr-emu --help
```

### Agent creation
Agent can be installed from pypi, git repository or local folder present on CYST docker container. For private 
repositories, you'll need access token.

For agent creation see:
```
❯ dr-emu agents create --help
                                                                                                                                                                                                                                    
 Usage: dr-emu agents create [OPTIONS] NAME [ROLE]:[attacker|defender]                                                                                                                                                              
                             [SOURCE]:[git|pypi|local]                                                                                                                                                                              
                                                                                                                                                                                                                                    
 Create Agent.                                                                                                                                                                                                                      
                                                                                                                                                                                                                                    
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    name        TEXT                        agent name [default: None] [required]                                                                                                                                               │
│      role        [ROLE]:[attacker|defender]  Agent role [default: attacker]                                                                                                                                                      │
│      source      [SOURCE]:[git|pypi|local]   type of source from which should be agent installed.(This will trigger a prompt) [default: git]                                                                                     │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


```
After specifying the `source` argument and confirmation, you will see prompt matching the selected `source`.

#### Agent from git
**TIP: agent in subdirectory?**
If your Agent package is in subdirectory of git repository, use this format for GIT URL:
```
https://{host}/{owner}/project.git@{version}#subdirectory={subdirectory_name}
```

#### Agent in local folder
To install an Agent from local folder, you need a running docker container with CYST (part of **dr-emu** docker compose) and 
have the package with Agent present in there.

Then upon Agent creation you just specify `source` argument as `local` and give the path to the Agent package in a 
container when prompted for it.

**example:**

Agent package `agent-dummy` has been git cloned into the root folder of `CYST` docker container.
```
02951eff2fd3:/# ls
agent-dummy  dev          home         media        opt          root         sbin         sys          usr
bin          etc          lib          mnt          proc         run          srv          tmp          var
```

Agent creation would look like this:
```
❯ dr-emu agents create testagent attacker local
Package name: aidojo-agent
Path to agent: agent-dummy/

Agent with name: testagent and id: 1 has been created and installed

```