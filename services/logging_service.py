from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.app_paths import get_logs_dir


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def get_log_path() -> Path:
    return get_logs_dir() / "nodeflow.log"


def _has_console_handler(root: logging.Logger) -> bool:
    return any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, RotatingFileHandler)
        for handler in root.handlers
    )


def _has_file_handler(root: logging.Logger, log_path: Path) -> bool:
    return any(
        isinstance(handler, RotatingFileHandler)
        and Path(handler.baseFilename) == log_path
        for handler in root.handlers
    )


def _log_unhandled_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger("nodeflow.unhandled").critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def configure_logging() -> Path:
    log_path = get_log_path()
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT)

    if not _has_file_handler(root, log_path):
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if not _has_console_handler(root):
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    logging.captureWarnings(True)
    sys.excepthook = _log_unhandled_exception
    logging.getLogger(__name__).debug("Logging configured at %s", log_path)
    return log_path
