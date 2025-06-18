# Create new file: ui/workspace/excel_import_dialog.py

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
)
import openpyxl


class ExcelImportDialog(QDialog):
    def __init__(self, file_path, participants, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from Excel")
        self.file_path = file_path
        self.participants = {p["name"]: p["id"] for p in participants}
        self.column_headers = self._get_excel_headers()

        if not self.column_headers:
            self.valid_headers = False
            return
        self.valid_headers = True

        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        # --- Column Mapping Fields ---
        self.title_combo = QComboBox()
        self.title_combo.addItems(self.column_headers)

        self.content_combo = QComboBox()
        self.content_combo.addItems(self.column_headers)

        self.participant_combo = QComboBox()
        # Add a special option to handle assignment later or use a fixed participant
        self.participant_combo.addItem("<Assign Later>", None)
        self.participant_combo.addItems(self.column_headers)

        form_layout.addRow(QLabel("Column for Document Title:"), self.title_combo)
        form_layout.addRow(QLabel("Column for Main Content:"), self.content_combo)
        form_layout.addRow(
            QLabel("Column for Participant Name:"), self.participant_combo
        )

        layout.addLayout(form_layout)
        # --- End Column Mapping ---

        # --- OK and Cancel Buttons ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _get_excel_headers(self):
        try:
            workbook = openpyxl.load_workbook(self.file_path, read_only=True)
            sheet = workbook.active
            return [cell.value for cell in sheet[1]]
        except Exception:
            return []

    def get_column_mappings(self):
        return {
            "title": self.title_combo.currentText(),
            "content": self.content_combo.currentText(),
            "participant": self.participant_combo.currentText(),
        }
