from pathlib import Path
from starlette.config import Config
from databases import DatabaseURL

BASE_DIR = Path(__file__).parent

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

config = Config(".env")

DEBUG = config("DEBUG", cast=bool, default=False)

# DATABASE_URL = config(
#     "DATABASE_URL", cast=DatabaseURL, default="postgresql://localhost/db"
# )
