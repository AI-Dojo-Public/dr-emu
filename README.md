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

Install the application:
```shell
poetry install
```

## Build the infrastructure
Run postgresql container
```shell
docker run --rm --name postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres -p 127.0.0.1:5432:5432 postgres:15
```

Make sure the necessary images exist:
```shell
docker build -t base --target base .
docker build -t router --target router .
docker build -t node --target node .
```
Run application:
```shell
poetry run uvicorn testbed_app.app:app --reload
```
To build the infrastructure use:
```bash
curl localhost:8000/create-infra
```

To destroy infrastructure use:
```bash
curl localhost:8000/destroy-infra
```
