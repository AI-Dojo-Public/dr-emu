from os import path
from pathlib import Path
from starlette.config import Config

BASE_DIR = Path(__file__).parent

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

config = Config(".env")

DEBUG = config("DEBUG", cast=bool, default=False)


LOG_DIRECTORY = path.join(BASE_DIR, "log/")
LOG_FILE_PATH = path.join(LOG_DIRECTORY, "dr-emu.log")
LOG_FILE_PATH_DEBUG = path.join(LOG_DIRECTORY, "dr-emu-debug.log")
