import httpx
from pydantic_settings import BaseSettings
from rich import print
from rich.table import Table
from rich.text import Text


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
            print("[bold read]Connection timeout![/bold read]")

    def api_get_data(self, endpoint_url: str, object_id: int = None, parameters: dict = None):
        try:
            response = httpx.get(self._build_request_url(endpoint_url, object_id, parameters)).json()
            if type(response) is list:
                return self.table_from_list(response)
            else:
                text = Text()
                for key, value in response.items():
                    text += f"{key}: {value}\n"
                return text
        except httpx.ReadTimeout:
            print("[bold read]Connection timeout![/bold read]")

    def api_get(
        self,
        endpoint_url: str,
        object_id: int = None,
        parameters: dict = None,
        timeout: float = 5.0,
    ):
        try:
            return httpx.get(self._build_request_url(endpoint_url, object_id, parameters), timeout=timeout)
        except httpx.ReadTimeout:
            print("[bold read]Connection timeout![/bold read]")

    def api_post(
        self,
        endpoint_url: str,
        object_id: int = None,
        data: dict = None,
        files: dict = None,
        timeout: float = 5.0,
    ):
        try:
            return httpx.post(
                url=self._build_request_url(endpoint_url, object_id),
                data=data,
                files=files,
                timeout=timeout
            )
        except httpx.ReadTimeout:
            print("Connection Timeout")

    @staticmethod
    def table_from_list(list_response):
        table = Table(*list_response[0].keys())
        for template in list_response:
            table.add_row(*map(str, template.values()))
        return table


settings = SettingsAPI()
clm = CLIManager(settings.app_host, settings.app_port, settings.ssl, settings.debug)
