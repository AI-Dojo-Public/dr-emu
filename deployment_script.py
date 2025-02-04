import asyncio
from argparse import ArgumentParser
import httpx
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
    template = httpx.post("http://127.0.0.1:8000/templates/create/", data=json.dumps(data))
    if template.status_code != 201:
        raise RuntimeError(f"message: {template.text}, code: {template.status_code}")
    else:
        print("Template created successfully")
        return template.json()


def create_run(template_id: int) -> dict:
    data = {"name": "demo", "template_id": template_id}

    print("Creating Run")
    run = httpx.post("http://127.0.0.1:8000/runs/create/", data=json.dumps(data))
    if run.status_code != 201:
        raise RuntimeError(f"message: {run.text}, code: {run.status_code}")
    else:
        print("Run created successfully")
        return run.json()


async def start_run(run_id: int):
    async with httpx.AsyncClient() as client:
        run_start = await client.post(f"http://127.0.0.1:8000/runs/start/{run_id}/", timeout=None)
    if run_start.status_code != 200:
        raise RuntimeError(f"message: {run_start.text}, code: {run_start.status_code}")
    else:
        print(f"Run {run_id} started successfully")
        return run_id

import requests


class AIDojoClient:
    """
    Python client for interacting with the AI-Dojo REST API.
    """
    def __init__(self, base_url):
        """
        Initialize the client with the base URL of the API.

        :param base_url: The base URL of the API.
        """
        self.base_url = base_url.rstrip("/")

    def create_environment(self, data):
        """
        Create a new environment.

        :param data: A dictionary containing the environment details.
        :return: Response JSON if the request is successful, otherwise raises an exception.
        """
        url = f"{self.base_url}/api/v1/environment/create/"
        response = requests.post(url, json=data)
        self._handle_response(response)
        return response.json()

    def init_environment(self, name):
        """
        Initialize an environment by name.

        :param name: The name of the environment to initialize.
        :return: Response JSON if the request is successful, otherwise raises an exception.
        """
        url = f"{self.base_url}/api/v1/environment/init/"
        params = {"name": name}
        response = requests.post(url, params=params)
        self._handle_response(response)
        return response.json()

    def configure_environment(self, name):
        """
        Configure an environment by name.

        :param name: The name of the environment to configure.
        :return: Response JSON if the request is successful, otherwise raises an exception.
        """
        url = f"{self.base_url}/api/v1/environment/configure/"
        params = {"name": name}
        response = requests.post(url, params=params)
        self._handle_response(response)
        return response.json()

    def reset_environment(self, name):
        """
        Reset an environment by name.

        :param name: The name of the environment to reset.
        :return: Response JSON if the request is successful, otherwise raises an exception.
        """
        url = f"{self.base_url}/api/v1/environment/reset/"
        params = {"name": name}
        response = requests.post(url, params=params)
        self._handle_response(response)
        return response.json()

    @staticmethod
    def _handle_response(response):
        """
        Handle the API response, raising exceptions for error status codes.

        :param response: The HTTP response object.
        """
        if not response.ok:
            try:
                error_details = response.json()
            except ValueError:
                error_details = response.text
            raise Exception(f"API request failed with status {response.status_code}: {error_details}")


async def main(config_items=all_config_items, instances=1):
    config = create_configuration(config_items)
    template_id = create_template(config)["id"]
    run_id = create_run(template_id)["id"]

    async with asyncio.TaskGroup() as tg:
        for _ in range(instances):
            tg.create_task(start_run(run_id))


    print("done")
    return run_id


if __name__ == "__main__":
    asyncio.run(main())