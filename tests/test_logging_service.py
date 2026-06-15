import logging
import sys
from logging.handlers import RotatingFileHandler

from services import logging_service


def test_configure_logging_adds_file_and_console_handlers():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    original_hook = sys.excepthook
    root.handlers = []
    try:
        log_path = logging_service.configure_logging()

        assert log_path.name == "nodeflow.log"
        assert any(isinstance(handler, RotatingFileHandler) for handler in root.handlers)
        assert any(
            isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, RotatingFileHandler)
            for handler in root.handlers
        )
        assert sys.excepthook == logging_service._log_unhandled_exception
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
        sys.excepthook = original_hook


def test_configure_logging_is_idempotent():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    original_hook = sys.excepthook
    root.handlers = []
    try:
        logging_service.configure_logging()
        logging_service.configure_logging()

        file_handlers = [
            handler for handler in root.handlers if isinstance(handler, RotatingFileHandler)
        ]
        console_handlers = [
            handler
            for handler in root.handlers
            if isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, RotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        assert len(console_handlers) == 1
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
        sys.excepthook = original_hook


def test_unhandled_exception_hook_logs_traceback(caplog):
    with caplog.at_level(logging.CRITICAL):
        try:
            raise RuntimeError("boom")
        except RuntimeError as error:
            logging_service._log_unhandled_exception(
                RuntimeError,
                error,
                error.__traceback__,
            )

    assert "Uncaught exception" in caplog.text
    assert "boom" in caplog.text
