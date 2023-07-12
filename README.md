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

**Notice: To be able to proceed with the installation, make sure you have set up [ssh keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) and have access to the [CYST Core](https://gitlab.ics.muni.cz/cyst/cyst-core) repository.**

Clone cyst core:
```shell
git clone git@gitlab.ics.muni.cz:cyst/cyst-core.git
```

## Build the infrastructure

Make sure the necessary images exist:
```shell
docker build -t base --target base .
docker build -t router --target router .
docker build -t node --target node .
```
Run deployment:
```shell
docker compose up -d
```

**IMPORTANT: Web application uses docker on host via mounted docker socket.**

To build the infrastructures use the following command with `infrastructures=<number-of-infrastructures>` parameter
```bash
curl localhost:8000/create-infra?infrastructures=2
```

To destroy infrastructures use following command with `id=<id-of-infrastructure>` parameter:
```bash
curl localhost:8000/destroy-infra?id=1&id=2
```
