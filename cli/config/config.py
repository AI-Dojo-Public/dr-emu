from enum import Enum

import httpx
from pydantic_settings import BaseSettings
from rich import print
from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.console import Console
import json

console = Console()
error = Style(color="red", bold=True)
success = Style(color="green", bold=True)

success_message = {201: "created", 204: "deleted"}


class SettingsAPI(BaseSettings):
    app_host: str
    app_port: int
    ssl: bool
    debug: bool


class CLIManager:
    def __init__(self, host: str, port: int, ssl: bool, debug: bool):
        self._api_url = f'{"https" if ssl else "http"}://{host}:{port}'
        self.debug = debug

    def _build_request_url(self, endpoint_url: str, object_id: int = None, parameters: dict = None):
        url = f"{self._api_url}{endpoint_url if object_id is None else endpoint_url.format(object_id)}"
        if parameters:
            url += "?"
            for key, value in parameters.items():
                url += f"{key}={value}"
        return url

    def api_delete(self, endpoint_url: str, object_id: int):
        try:
            return httpx.delete(self._build_request_url(endpoint_url, object_id))
        except httpx.ReadTimeout:
            return "Connection timeout!"
        except httpx.ConnectError as conn_err:
            return str(conn_err)

    def api_get(self, endpoint_url: str, object_id: int = None, parameters: dict = None):
        try:
            return httpx.get(self._build_request_url(endpoint_url, object_id, parameters))
        except httpx.ReadTimeout:
            return "Connection timeout!"
        except httpx.ConnectError as conn_err:
            return str(conn_err)

    def api_post(
        self, endpoint_url: str, object_id: int = None, parameters: dict = None, data: dict = None, files: dict = None, timeout: float = 5.0
    ):
        try:
            return httpx.post(
                url=self._build_request_url(endpoint_url, object_id, parameters), data=data, files=files, timeout=timeout
            )
        except httpx.ReadTimeout:
            return "Connection timeout!"
        except httpx.ConnectError as conn_err:
            return str(conn_err)

    def print_get_message(self, response: httpx.Response | str):
        if isinstance(response, httpx.Response):
            try:
                response_message = response.json()
            except json.decoder.JSONDecodeError:
                response_message = response.text

            if type(response_message) is list:
                console.print(self.table_from_list(response_message))
            else:
                console.print(response_message, style=error)
        else:
            console.print(response, style=error)

    @staticmethod
    def print_non_get_message(
        response: httpx.Response | str,
        model_name: str,
        correct_code: int,
        model_id: int | None = None,
        action: str | None = None,
    ):
        if action is None:
            action = success_message.get(correct_code)

        if isinstance(response, str):
            console.print(response, style=error)
        elif isinstance(response, httpx.Response):
            try:
                response_message = response.json()
            except json.decoder.JSONDecodeError:
                response_message = response.text

            if response.status_code == correct_code:
                if model_id is None and (model_id := response_message.get("id")) is None:
                    console.print(f"{model_name} has been {action}", style=success)
                else:
                    console.print(f"{model_name} with id: {model_id} has been {action}", style=success)

            # TODO: what if some model is going to have "message" attribute?
            if response_message and not response_message.get("message"):
                console.print(response_message)

    @staticmethod
    def table_from_list(list_response):
        if not list_response:
            return list_response

        table = Table(*list_response[0].keys())
        for template in list_response:
            table.add_row(*map(str, template.values()))
        return table


settings = SettingsAPI()
clm = CLIManager(settings.app_host, settings.app_port, settings.ssl, settings.debug)
