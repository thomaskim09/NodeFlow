from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QGroupBox,
    QMessageBox,
    QDialog,
    QLineEdit,
    QDialogButtonBox,
    QLabel,
)
import database


class ParticipantManager(QWidget):
    def __init__(self, project_id):
        super().__init__()

        self.project_id = project_id
        self.participants_map = {}

        # --- Main Layout and GroupBox ---
        # The QGroupBox provides a nice titled border
        group_box = QGroupBox("Participants")
        main_layout = QVBoxLayout(self)
        group_box_layout = QVBoxLayout(group_box)
        main_layout.addWidget(group_box)

        # --- Widgets ---
        self.list_widget = QListWidget()

        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        edit_button = QPushButton("Edit")
        delete_button = QPushButton("Delete")
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)

        # --- Assemble Layout ---
        group_box_layout.addWidget(self.list_widget)
        group_box_layout.addLayout(button_layout)

        # --- Connect Signals to Slots ---
        add_button.clicked.connect(self.add_participant)
        edit_button.clicked.connect(self.edit_participant)
        delete_button.clicked.connect(self.delete_participant)
        self.list_widget.itemDoubleClicked.connect(self.edit_participant)

        # --- Load Initial Data ---
        self.load_participants()

    def load_participants(self):
        """Loads participants for the current project into the list widget."""
        self.list_widget.clear()
        participants = database.get_participants_for_project(self.project_id)
        self.participants_map = {p["name"]: p["id"] for p in participants}
        for name in sorted(self.participants_map.keys()):
            self.list_widget.addItem(name)

    def add_participant(self):
        """Handles the logic for adding a new participant."""
        dialog = ParticipantDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            if name:
                database.add_participant(self.project_id, name)
                self.load_participants()

    def edit_participant(self):
        """Handles the logic for editing an existing participant."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, "No Selection", "Please select a participant to edit."
            )
            return

        current_name = selected_items[0].text()
        participant_id = self.participants_map[current_name]

        dialog = ParticipantDialog(self, current_name=current_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_name()
            if new_name:
                database.update_participant(
                    participant_id, new_name, ""
                )  # Details are empty for now
                self.load_participants()

    def delete_participant(self):
        """Deletes the selected participant."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, "No Selection", "Please select a participant to delete."
            )
            return

        current_name = selected_items[0].text()
        participant_id = self.participants_map[current_name]

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{current_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            database.delete_participant(participant_id)
            self.load_participants()


class ParticipantDialog(QDialog):
    """A dialog for adding or editing a participant's name."""

    def __init__(self, parent=None, current_name=""):
        super().__init__(parent)
        self.setWindowTitle("Participant Details")

        self.layout = QVBoxLayout(self)
        self.label = QLabel("Participant Name:")
        self.name_input = QLineEdit(current_name)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.name_input)
        self.layout.addWidget(self.button_box)

    def get_name(self):
        """Returns the stripped text from the name input field."""
        return self.name_input.text().strip()
