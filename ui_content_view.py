from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QDialog,
    QLabel,
    QDialogButtonBox,
)
from PySide6.QtGui import QTextCursor, QColor
import os
import database
import docx


class ContentView(QWidget):
    """
    Manages the central content view, including document import and display.
    """

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.documents_map = {}
        self.current_document_id = None
        self.current_participant_id = None

        main_layout = QVBoxLayout(self)
        top_bar_layout = QHBoxLayout()

        self.doc_selector = QComboBox()
        import_button = QPushButton("Import Document")

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        top_bar_layout.addWidget(self.doc_selector)
        top_bar_layout.addWidget(import_button)
        main_layout.addLayout(top_bar_layout)
        main_layout.addWidget(self.text_edit)

        import_button.clicked.connect(self.import_document)
        self.doc_selector.currentIndexChanged.connect(self.load_document_content)

        self.load_document_list()

    def load_document_list(self):
        """Loads the list of documents for the project into the ComboBox."""
        current_selection = self.doc_selector.currentText()
        self.doc_selector.blockSignals(True)
        self.doc_selector.clear()

        docs = database.get_documents_for_project(self.project_id)
        self.documents_map = {
            f"{doc['title']} ({doc['participant_name'] or 'Unassigned'})": doc["id"]
            for doc in docs
        }
        for display_text in self.documents_map.keys():
            self.doc_selector.addItem(display_text)

        self.doc_selector.blockSignals(False)
        index = self.doc_selector.findText(current_selection)
        if index != -1:
            self.doc_selector.setCurrentIndex(index)
        elif self.doc_selector.count() > 0:
            self.doc_selector.setCurrentIndex(0)

    def import_document(self):
        """Opens a file dialog to import a .txt or .docx file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Document", "", "Documents (*.txt *.docx)"
        )
        if not file_path:
            return

        participants = database.get_participants_for_project(self.project_id)
        if not participants:
            QMessageBox.warning(
                self,
                "No Participants",
                "Please add a participant to this project before importing a document.",
            )
            return

        dialog = AssignParticipantDialog(participants, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            participant_id = dialog.get_selected_participant_id()
            if not participant_id:
                return

            try:
                content = ""
                # This logic is now confirmed correct.
                if file_path.lower().endswith(".docx"):
                    doc = docx.Document(file_path)
                    content = "\n".join([p.text for p in doc.paragraphs])
                else:  # Assumes .txt or any other format
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                title = os.path.basename(file_path)
                new_doc_id = database.add_document(
                    self.project_id, title, content, participant_id
                )
                self.load_document_list()

                new_doc_display_text = next(
                    (k for k, v in self.documents_map.items() if v == new_doc_id), None
                )
                if new_doc_display_text:
                    self.doc_selector.setCurrentText(new_doc_display_text)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import file: {e}")

    def load_document_content(self, index=None):
        """Loads the text of the selected document into the QTextEdit."""
        selected_display_text = self.doc_selector.currentText()
        if not selected_display_text:
            self.text_edit.clear()
            self.current_document_id = None
            self.current_participant_id = None
            return

        self.current_document_id = self.documents_map[selected_display_text]
        content, participant_id = database.get_document_content(
            self.current_document_id
        )
        self.current_participant_id = participant_id
        self.text_edit.setPlainText(content)

    def highlight_text(self, start, end, color_hex="#FFFF00"):
        """Applies a background color to a segment of text."""
        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        fmt = cursor.charFormat()
        fmt.setBackground(QColor(color_hex))
        cursor.setCharFormat(fmt)


class AssignParticipantDialog(QDialog):
    """A dialog for assigning a participant to a new document."""

    def __init__(self, participants, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Participant")
        self.participants = {p["name"]: p["id"] for p in participants}
        layout = QVBoxLayout(self)
        label = QLabel("Assign this document to which participant?")
        self.combo = QComboBox()
        self.combo.addItems(self.participants.keys())
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(label)
        layout.addWidget(self.combo)
        layout.addWidget(button_box)

    def get_selected_participant_id(self):
        """Returns the ID of the participant selected in the combobox."""
        name = self.combo.currentText()
        return self.participants.get(name)
