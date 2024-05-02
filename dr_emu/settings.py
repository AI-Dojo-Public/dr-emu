from os import path
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    db_host: str
    management_network_name: str
    ignore_management_network: bool
    echo_sql: bool = True
    test: bool = False
    project_name: str = "Dr-emu"
    oauth_token_secret: str = "my_dev_secret"
    debug: bool = False


BASE_DIR = Path(__file__).parent

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

LOG_DIRECTORY = path.join(BASE_DIR, "log/")
LOG_FILE_PATH = path.join(LOG_DIRECTORY, "dr-emu.log")
LOG_FILE_PATH_DEBUG = path.join(LOG_DIRECTORY, "dr-emu-debug.log")

settings = Settings()  # type: ignore
