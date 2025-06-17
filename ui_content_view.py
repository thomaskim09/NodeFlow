from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QTextCursor, QColor
import os
import database


class ContentView(QWidget):
    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.documents_map = {}
        self.current_document_id = None

        # --- Layouts and Widgets ---
        main_layout = QVBoxLayout(self)
        top_bar_layout = QHBoxLayout()

        self.doc_selector = QComboBox()
        import_button = QPushButton("Import Document")

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)  # Start as read-only

        # --- Assemble Layout ---
        top_bar_layout.addWidget(self.doc_selector)
        top_bar_layout.addWidget(import_button)
        main_layout.addLayout(top_bar_layout)
        main_layout.addWidget(self.text_edit)

        # --- Connect Signals ---
        import_button.clicked.connect(self.import_document)
        self.doc_selector.currentIndexChanged.connect(self.load_document_content)

        # --- Load Initial Data ---
        self.load_document_list()

    def load_document_list(self):
        """Loads the list of documents for the project into the ComboBox."""
        self.doc_selector.clear()
        docs = database.get_documents_for_project(self.project_id)
        self.documents_map = {doc["title"]: doc["id"] for doc in docs}
        for title in self.documents_map.keys():
            self.doc_selector.addItem(title)

    def import_document(self):
        """Opens a file dialog to import a .txt file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Text Document", "", "Text Files (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                title = os.path.basename(file_path)
                database.add_document(self.project_id, title, content)
                self.load_document_list()
                self.doc_selector.setCurrentText(title)  # Auto-select the new doc
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import file: {e}")

    def load_document_content(self):
        """Loads the text of the selected document into the QTextEdit."""
        selected_title = self.doc_selector.currentText()
        if not selected_title:
            self.text_edit.clear()
            self.current_document_id = None
            return

        self.current_document_id = self.documents_map[selected_title]
        content = database.get_document_content(self.current_document_id)
        self.text_edit.setPlainText(content)

    def highlight_text(self, start, end, color_hex="#FFFF00"):
        """Applies a background color to a segment of text."""
        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        fmt = cursor.charFormat()
        fmt.setBackground(QColor(color_hex))
        cursor.setCharFormat(fmt)
