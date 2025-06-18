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
    QApplication,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat
import os
import database
import docx


class ContentView(QWidget):
    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.documents_map = {}
        self.current_document_id = None
        self.current_participant_id = None
        self.is_dirty = False

        main_layout = QVBoxLayout(self)
        top_bar_layout = QHBoxLayout()

        # --- NEW: Area Title ---
        title_label = QLabel("Document View")
        font = title_label.font()
        font.setBold(True)
        title_label.setFont(font)

        # Document selector
        self.doc_selector = QComboBox()

        # --- NEW: Icon Buttons ---
        import_button = QPushButton("📥")
        import_button.setToolTip("Import Document (.txt, .docx)")
        import_button.setFixedSize(28, 28)

        self.save_button = QPushButton("💾")
        self.save_button.setToolTip(
            "Save Changes (clears existing codes for this document)"
        )
        self.save_button.setFixedSize(28, 28)
        self.save_button.setEnabled(False)  # Disabled by default

        delete_button = QPushButton("🗑️")
        delete_button.setToolTip("Delete Current Document")
        delete_button.setFixedSize(28, 28)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(False)  # Allow editing

        # --- NEW: Layout setup ---
        top_bar_layout.addWidget(title_label)
        top_bar_layout.addWidget(self.doc_selector)
        top_bar_layout.addStretch()  # Spacer
        top_bar_layout.addWidget(import_button)
        top_bar_layout.addWidget(self.save_button)
        top_bar_layout.addWidget(delete_button)

        main_layout.addLayout(top_bar_layout)
        main_layout.addWidget(self.text_edit)

        # Connect signals
        import_button.clicked.connect(self.import_document)
        self.save_button.clicked.connect(self.save_document_content)
        delete_button.clicked.connect(self.delete_current_document)
        self.doc_selector.currentIndexChanged.connect(self.load_document_content)
        self.text_edit.textChanged.connect(self.on_text_changed)

        self.load_document_list()

    def load_document_list(self):
        current_doc_id = self.current_document_id
        self.doc_selector.blockSignals(True)
        self.doc_selector.clear()

        docs = database.get_documents_for_project(self.project_id)
        self.documents_map = {
            f"{doc['title']} ({doc['participant_name'] or 'Unassigned'})": doc["id"]
            for doc in docs
        }
        id_to_display_text = {v: k for k, v in self.documents_map.items()}
        for display_text in sorted(self.documents_map.keys()):
            self.doc_selector.addItem(display_text)

        self.doc_selector.blockSignals(False)
        new_text_to_select = id_to_display_text.get(current_doc_id)
        index = self.doc_selector.findText(new_text_to_select)

        if index != -1:
            self.doc_selector.setCurrentIndex(index)
        elif self.doc_selector.count() > 0:
            self.doc_selector.setCurrentIndex(0)
        else:
            self.doc_selector.setCurrentIndex(-1)

    def import_document(self):
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
                "Please add a participant before importing a document.",
            )
            return

        dialog = AssignParticipantDialog(participants, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            participant_id = dialog.get_selected_participant_id()
            if not participant_id:
                return

            try:
                content = ""
                if file_path.lower().endswith(".docx"):
                    doc = docx.Document(file_path)
                    content = "\n".join([p.text for p in doc.paragraphs])
                else:
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

    def delete_current_document(self):
        if not self.current_document_id:
            QMessageBox.warning(self, "No document", "No document is selected.")
            return

        selected_text = self.doc_selector.currentText()
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete '{selected_text}' and all its coded segments?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            database.delete_document(self.current_document_id)
            self.load_document_list()

    def on_text_changed(self):
        """Marks the document as dirty and enables the save button."""
        if not self.text_edit.isReadOnly():
            self.is_dirty = True
            self.save_button.setEnabled(True)

    def save_document_content(self):
        """Saves the edited text, after warning the user about clearing codes."""
        if not self.is_dirty or not self.current_document_id:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Save and Clear Codes",
            "Saving changes to the document text requires clearing all existing coded segments for this document to prevent errors.\n\nAre you sure you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            new_content = self.text_edit.toPlainText()
            database.update_document_content(self.current_document_id, new_content)

            self.is_dirty = False
            self.save_button.setEnabled(False)

            # Manually trigger a refresh of the views
            parent_workspace = (
                self.parent().parent().parent()
            )  # Navigate up to WorkspaceView
            parent_workspace.on_document_changed()

            QMessageBox.information(
                self,
                "Success",
                "Document saved successfully. All codes for this document have been cleared.",
            )

    def load_document_content(self, index=None):
        """Loads a document, resetting the editor state."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.text_edit.textChanged.disconnect(self.on_text_changed)
            self.text_edit.clear()

            self.is_dirty = False
            self.save_button.setEnabled(False)

            selected_display_text = self.doc_selector.currentText()
            if not selected_display_text:
                self.current_document_id = None
                self.current_participant_id = None
                self.text_edit.setReadOnly(True)
                self.text_edit.textChanged.connect(self.on_text_changed)
                return

            self.text_edit.setReadOnly(False)
            self.current_document_id = self.documents_map[selected_display_text]
            content, participant_id = database.get_document_content(
                self.current_document_id
            )
            self.current_participant_id = participant_id
            self.text_edit.setPlainText(content)
            self.text_edit.textChanged.connect(self.on_text_changed)
        finally:
            QApplication.restoreOverrideCursor()

    def highlight_text(self, start, end, color_hex="#FFFF00"):
        """Applies a background color and contrasting text color to a segment."""
        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(color_hex))
        fmt.setForeground(QColor("black"))  # Force black text for contrast
        cursor.mergeCharFormat(fmt)


class AssignParticipantDialog(QDialog):
    def __init__(self, participants, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Participant")
        self.participants = {p["name"]: p["id"] for p in participants}
        layout = QVBoxLayout(self)
        label = QLabel("Assign this document to which participant?")
        self.combo = QComboBox()
        self.combo.addItems(sorted(self.participants.keys()))
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(label)
        layout.addWidget(self.combo)
        layout.addWidget(button_box)

    def get_selected_participant_id(self):
        name = self.combo.currentText()
        return self.participants.get(name)
