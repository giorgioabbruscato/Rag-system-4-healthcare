import logging
import sys

import structlog

from src.config import settings


def setup_logging(level: str = settings.log_level):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(
                colors=True
            ),  # Dev-friendly console rendering
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to pass through to structlog's formatter
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=getattr(logging, level)
    )


def get_logger(name: str):
    # Ensure logging is setup. If already setup, this has minimal overhead.
    if not structlog.is_configured():
        setup_logging()
    return structlog.get_logger(name)
