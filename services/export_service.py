from __future__ import annotations

import logging
import traceback
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from services.logging_service import get_log_path
from services.platform_service import platform_service

LOGGER = logging.getLogger(__name__)


class ExportService:
    def show_success(self, parent: QWidget | None, title: str, file_path: str) -> None:
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(file_path)
        open_button = msg_box.addButton("Open File", QMessageBox.ActionRole)
        msg_box.addButton(QMessageBox.Ok)
        msg_box.exec()
        if msg_box.clickedButton() == open_button:
            platform_service.open_path(Path(file_path))

    def show_permission_error(self, parent: QWidget | None, file_path: str) -> None:
        LOGGER.warning("Permission denied while exporting to %s", file_path)
        QMessageBox.critical(
            parent,
            "Permission Denied",
            (
                f"Could not save the file to:\n{file_path}\n\n"
                "Please make sure you have permissions to write to this location and that the file is not currently open in another program."
            ),
        )

    def show_unexpected_error(
        self,
        parent: QWidget | None,
        action_label: str,
        error: Exception,
        details: str | None = None,
    ) -> None:
        log_path = get_log_path()
        detail_text = details or "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        LOGGER.error("%s failed: %s", action_label, error)

        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(action_label)
        msg_box.setText(f"An unexpected error occurred while saving the file:\n{error}")
        msg_box.setInformativeText(
            f"Detailed diagnostics were written to:\n{log_path}"
        )
        msg_box.setDetailedText(detail_text)
        msg_box.exec()


export_service = ExportService()
