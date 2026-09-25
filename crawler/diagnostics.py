import logging
import multiprocessing as mp
import os
from logging.handlers import RotatingFileHandler

from crawler.options import PATH

LOG_PATH = os.path.join(PATH, "pixgrabber.log")

_LOGGER_NAME = "pixgrabber"
_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 3
_configured_pid = None


def _configure_logging():
    """Configure crawler diagnostics in the Commander process only.

    On Windows the main GUI process imports the crawler modules before the
    Commander process is spawned. If both processes open the same
    RotatingFileHandler, Windows prevents one process from renaming the log
    while the other still has it open, causing WinError 32 during rollover.

    All task/web-request diagnostics are produced by the Commander process and
    its worker threads, so keep a single rotating-file owner there.
    """
    global _configured_pid

    pid = os.getpid()
    if _configured_pid == pid:
        return

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # A forked child can inherit handlers created by its parent. Remove any
    # inherited rotating handlers before deciding whether this process owns
    # the diagnostic file.
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            try:
                handler.close()
            finally:
                logger.removeHandler(handler)

    # The GUI process only imports crawler modules; it does not produce the
    # task/request diagnostic stream. Avoid opening the rotating log here.
    if mp.current_process().name == "MainProcess":
        _configured_pid = pid
        return

    os.makedirs(PATH, exist_ok=True)

    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | pid=%(process)d | %(threadName)s | "
        "%(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(handler)

    _configured_pid = pid


def get_logger(component: str = "") -> logging.Logger:
    """Return a PixGrabber logger that writes to the rotating diagnostic log."""
    _configure_logging()
    if component:
        return logging.getLogger(f"{_LOGGER_NAME}.{component}")
    return logging.getLogger(_LOGGER_NAME)
