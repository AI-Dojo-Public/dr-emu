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
Make sure the necessary images exist:
```shell
docker build -t base --target base .
docker build -t router --target router .
docker build -t node --target node .
```

To build the infrastructure use:
```bash
poetry run python docker_testbed/main.py
```
