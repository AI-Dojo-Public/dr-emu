# AI-dojo docker testbed
This project serves as a demonstration of semi-realistic network topology generation using a docker for AI-DOJO.

## TODO: Update cyst infrastructure.py

## Requirements
- python 3.11

## Build the infrastructure
First, we clone the demo itself (if you haven't already):
```bash
git clone git@gitlab.ics.muni.cz:ai-dojo/docker-testbed.git
cd docker-testbed
git clone git@gitlab.ics.muni.cz:cyst/cyst-core.git
```

Then run docker compose and python script for network configuration on containers.
```bash
poetry shell
poetry install
pip install -e cyst-core
docker compose up -d
python3 setup-containers.py
```

## Run scenario
```bash
docker exec -it cryton-cli bash
./app/run_scenario_1.sh
```