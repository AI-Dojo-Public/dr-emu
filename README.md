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
Run deployment:
```shell
docker compose up -d
```

**IMPORTANT: Web application uses docker on host via mounted docker socket.**

## Usage
For REST API documentation, see `http://127.0.0.1:8000/docs`.

### CLI
Application also has a command line interface. Use the following command to invoke the app: 
```
dr-emu --help
```
