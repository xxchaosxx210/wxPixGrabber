import logging
import os
from logging.handlers import RotatingFileHandler

from crawler.options import PATH

LOG_PATH = os.path.join(PATH, "pixgrabber.log")

_LOGGER_NAME = "pixgrabber"
_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 3
_configured = False


def _configure_logging():
    """Configure a small rotating diagnostic log for crawler activity."""
    global _configured
    if _configured:
        return

    os.makedirs(PATH, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = os.path.abspath(LOG_PATH)
    handler_exists = any(
        isinstance(handler, RotatingFileHandler)
        and os.path.abspath(getattr(handler, "baseFilename", "")) == log_path
        for handler in logger.handlers
    )

    if not handler_exists:
        handler = RotatingFileHandler(
            LOG_PATH,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | pid=%(process)d | %(threadName)s | "
            "%(levelname)s | %(name)s | %(message)s"
        ))
        logger.addHandler(handler)

    _configured = True


def get_logger(component: str = "") -> logging.Logger:
    """Return a PixGrabber logger that writes to the rotating diagnostic log."""
    _configure_logging()
    if component:
        return logging.getLogger(f"{_LOGGER_NAME}.{component}")
    return logging.getLogger(_LOGGER_NAME)
