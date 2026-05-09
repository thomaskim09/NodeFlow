from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from services.platform_service import platform_service


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
        QMessageBox.critical(
            parent,
            "Permission Denied",
            (
                f"Could not save the file to:\n{file_path}\n\n"
                "Please make sure you have permissions to write to this location and that the file is not currently open in another program."
            ),
        )

    def show_unexpected_error(
        self, parent: QWidget | None, action_label: str, error: Exception
    ) -> None:
        QMessageBox.critical(
            parent,
            action_label,
            f"An unexpected error occurred while saving the file:\n{error}",
        )


export_service = ExportService()
