import structlog
import logging.config
import logging.handlers
import orjson

from testbed_app import settings


LOGGER_DEBUG = "debug"
LOGGER_PROD = "production"
LOGGER_TESTING = "testing"

if settings.DEBUG:
    logger_type = LOGGER_DEBUG
    logger_level = logging.DEBUG
else:
    logger_type = LOGGER_PROD
    logger_level = logging.INFO

structlog.configure(
    cache_logger_on_first_use=True,
    wrapper_class=structlog.make_filtering_bound_logger(logger_level),
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(serializer=orjson.dumps),
    ],
    logger_factory=structlog.BytesLoggerFactory(),
)

logger_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(message)s"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "debug_logger": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": settings.LOG_FILE_PATH_DEBUG,
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8",
        },
        "prod_logger": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": settings.LOG_FILE_PATH,
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8",
        },
    },
    "root": {"level": "NOTSET", "handlers": [], "propagate": True},
    "loggers": {
        "production": {"level": "INFO", "handlers": ["prod_logger"], "propagate": True},
        "debug": {"level": "DEBUG", "handlers": ["debug_logger", "console"], "propagate": True},
        "testing": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
    },
}


logging.config.dictConfig(logger_config)
logger = structlog.get_logger(logger_type)
