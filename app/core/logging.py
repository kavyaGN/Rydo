import logging
import logging.config
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.settings import Settings


class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name


def configure_logging(settings: Settings) -> None:
    formatter: dict[str, Any]
    if settings.log_format == "json":
        formatter = {
            "()": "app.core.logging.JsonFormatter",
            "format": "%(asctime)s %(level)s %(name)s %(request_id)s %(message)s",
        }
    else:
        formatter = {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s",
        }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": formatter},
            "filters": {"request_id": {"()": "app.core.request_context.RequestIdLogFilter"}},
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": settings.log_level.upper(),
            },
            "loggers": {
                # Access lines come from RequestContextMiddleware (with request ids),
                # so silence uvicorn's own duplicate access log.
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": "WARNING",
                    "propagate": False,
                },
                "sqlalchemy.engine": {
                    "handlers": ["default"],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
        }
    )
