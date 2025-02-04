# Dr-emu
Application for building semi-realistic network topology via Docker based on python description for [CYST](https://cyst-public.gitlab-pages.ics.muni.cz/cyst-core/index.html). Primary use of this application is to create an emulation environments for AI Agents where they can test their abilities in a more realistic scenario. Dr-emu was developed within the [AI-DOJO](https://gitlab.ics.muni.cz/ai-dojo) project.

## Requirements

- [Docker Compose](https://docs.docker.com/engine/install/)

In case you don't want to run dr-emu using Docker:

- [Python](https://www.python.org/) >= 3.11

## Installation
Clone the repo:
```shell
git clone git@gitlab.ics.muni.cz:ai-dojo/dr-emu.git
cd dr-emu
```

Deploy dr-emu:
```shell
docker compose up -d
```

**IMPORTANT: The application uses host's Docker socket.**

### Private Repository
If the docker images that should be downloaded for the infrastructure are in **private repository** please edit 
**\$DOCKER_TOKEN** and **\$REGISTRY_URL** Environmental variables.

In **/dr-emu/.env** change the value of: 
-   **$DOCKER_TOKEN** - access token for your private repository 
-   **$REGISTRY_URL** - url of repository's docker container registry (eg. `registry.gitlab.ics.muni.cz:443`).

## DEMO
Create template and start run (emulated infrastructure):
```shell
docker exec -it dr-emu sh
.venv/bin/python3 deployment_script.py
```

Stop the run (emulated infrastructure):
```shell
docker exec -it dr-emu sh
dr-emu runs stop <run-id>
```

## REST API
For REST API documentation, see `http://127.0.0.1:8000/docs`.

## Start Run prerequisites
### Use without Cryton

Set `IGNORE_MANAGEMENT_NETWORK=true` variable in `dr-emu/.env` file.

### Use with Cryton
**Be sure to have Management network containing Cryton deployed before starting Run!**

Edit `MANAGEMENT_NETWORK_NAME` environment variable in `dr-emu/.env` file with the name of the 
management network containing Cryton.


## E2E Tests
Tests are using statically configured ipaddresses from `dr-emu/tests/e2e/test_infrastructure.py`, so make sure 
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

## Build Docker image
Build and push the image:
```shell
docker build --target dr_emu --tag registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/dr-emu:$(git rev-parse --short HEAD) --tag registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/dr-emu:latest .
docker push --all-tags registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/dr-emu
```
