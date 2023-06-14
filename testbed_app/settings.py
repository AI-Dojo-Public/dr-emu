from pathlib import Path
from starlette.config import Config

BASE_DIR = Path(__file__).parent

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

config = Config(".env")

DEBUG = config("DEBUG", cast=bool, default=False)
