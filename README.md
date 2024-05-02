# AI-dojo Docker testbed
This project serves as a demonstration of semi-realistic network topology generation using a docker for AI-DOJO.

## Requirements
- [Python](https://www.python.org/) >= 3.11
- [Docker](https://docs.docker.com/engine/install/)

## Installation
Clone the repo:
```shell
git clone git@gitlab.ics.muni.cz:ai-dojo/docker-testbed.git
cd docker-testbed
git clone git@gitlab.ics.muni.cz:cyst/cyst-core.git
```

### Deploy dr-emu:

```shell
docker compose up -d
```

**IMPORTANT: The application uses host's Docker socket.**

### Private Repository
If the docker images that should be downloaded for the infrastructure are in **private repository** please edit 
**$DOCKER_TOKEN** and **$REGISTRY_URL** Environmental variables.

In **/docker-testbed/.env** change the value of: 
-   **$DOCKER_TOKEN** - access token for your private repository 
-   **$REGISTRY_URL** - url of repository's docker container registry (eg. `registry.gitlab.ics.muni.cz:443`).

## REST API
For REST API documentation, see `http://127.0.0.1:8000/docs`.

## CLI
Application also has a command line interface. CLI is accessible from application docker container. To access CLI, make sure that the application is deployed via
`docker compose` and run the following commands. 

```
docker exec -it aidojo-app /bin/sh
```
```
dr-emu --help
```
## Start Run prerequisites
**Be sure to have Management network containing Cryton deployed before starting Run!**

Edit `MANAGEMENT_NETWORK_NAME` environment variable in `docker-testbed/.env` file with the name of the 
management network containing Cryton.


## E2E Tests
Tests are using statically configured ipaddresses from `docker-testbed/tests/e2e/test_infrastructure.py`, so make sure 
that the ip addresses are available on the system or correctly change them in the infrastructure file.

Testing script will take care of the infrastructure deployment, checking the correctness of the deployment and 
automatic clean up of the infrastructure.

### Run e2e test
Make sure you are in a project folder and the run following commands:

#### Windows
```shell
python .\tests\e2e\deployment_checker.py
```

#### Linux
```bash
python3.11 tests/e2e/deployment_checker.py
```