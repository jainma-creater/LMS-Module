import logging
import sys

from app.core.config import get_settings

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format=_FORMAT,
        stream=sys.stdout,
        force=True,
    )
    # Never let third-party loggers leak secrets at DEBUG in production.
    if settings.is_production and level < logging.INFO:
        for noisy in ("uvicorn.access",):
            logging.getLogger(noisy).setLevel(logging.INFO)
