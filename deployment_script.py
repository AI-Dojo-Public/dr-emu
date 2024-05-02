from argparse import ArgumentParser
import requests
import json
from cyst.api.environment.environment import Environment
from cyst_infrastructure import all_config_items


def create_configuration(config_items):
    env = Environment.create()
    env.configure(*config_items)
    return env.configuration.general.save_configuration(indent=1)


def create_template(config) -> dict:
    data = {"name": "demo", "description": str(config)}

    print("Creating Template")
    template = requests.post("http://127.0.0.1:8000/templates/create/", data=json.dumps(data))
    if template.status_code != 201:
        raise RuntimeError(f"message: {template.text}, code: {template.status_code}")
    else:
        print("Template created successfully")
        return template.json()


def create_run(template_id: int) -> dict:
    data = {"name": "demo", "template_id": template_id}

    print("Creating Run")
    run = requests.post("http://127.0.0.1:8000/runs/create/", data=json.dumps(data))
    if run.status_code != 201:
        raise RuntimeError(f"message: {run.text}, code: {run.status_code}")
    else:
        print("Run created successfully")
        return run.json()


def start_run(run_id: int, instances: int = 1):
    data = {"instances": instances, "supernet": "10.0.0.0/8", "subnets_mask": 24}
    run_start = requests.post(f"http://127.0.0.1:8000/runs/start/{run_id}/?instances={instances}", data=json.dumps(data))

    if run_start.status_code != 200:
        raise RuntimeError(f"message: {run_start.text}, code: {run_start.status_code}")
    else:
        print(f"Run {run_id} started successfully")
        return run_id


def main(config_items=all_config_items):
    config = create_configuration(config_items)
    template_id = create_template(config)["id"]
    run_id = create_run(template_id)["id"]
    start_run(run_id)
    return run_id


if __name__ == "__main__":
    main()
