from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QLabel,
)
from PySide6.QtCore import Signal, Qt

import database


# --- Custom Widget for each participant item ---
class ParticipantItemWidget(QWidget):
    def __init__(self, participant_id, participant_name, parent_manager):
        super().__init__()
        self.participant_id = participant_id
        self.participant_name = participant_name
        self.parent_manager = parent_manager

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 8)
        name_label = QLabel(participant_name)

        self.edit_button = QPushButton("✎")
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setToolTip("Edit Participant Name")
        self.edit_button.clicked.connect(self.on_edit_clicked)
        self.edit_button.setVisible(False)

        self.delete_button = QPushButton("🗑")
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setToolTip("Delete Participant")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.delete_button.setVisible(False)

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)

    def set_icons_visible(self, visible):
        self.edit_button.setVisible(visible)
        self.delete_button.setVisible(visible)

    def on_edit_clicked(self):
        self.parent_manager.edit_participant(self.participant_id, self.participant_name)

    def on_delete_clicked(self):
        self.parent_manager.delete_participant(
            self.participant_id, self.participant_name
        )


class ParticipantManager(QWidget):
    participant_updated = Signal()

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # --- Header ---
        header_layout = QHBoxLayout()
        header_label = QLabel("Participants")
        font = header_label.font()
        font.setBold(True)
        header_label.setFont(font)

        add_button = QPushButton("＋ Add")
        add_button.setToolTip("Add a new participant")
        add_button.clicked.connect(self.add_participant)

        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(add_button)
        main_layout.addLayout(header_layout)

        # --- List Widget ---
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self.on_selection_changed)
        main_layout.addWidget(self.list_widget)

        self.load_participants()

    def on_selection_changed(self, current_item, previous_item):
        if previous_item:
            widget = self.list_widget.itemWidget(previous_item)
            if widget:
                widget.set_icons_visible(False)

        if current_item:
            widget = self.list_widget.itemWidget(current_item)
            if widget:
                widget.set_icons_visible(True)

    def load_participants(self):
        self.list_widget.currentItemChanged.disconnect(self.on_selection_changed)
        self.list_widget.clear()
        participants = database.get_participants_for_project(self.project_id)

        if not participants:
            item = QListWidgetItem("No participants created.", self.list_widget)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        else:
            for p in sorted(participants, key=lambda x: x["name"]):
                list_item = QListWidgetItem(self.list_widget)
                item_widget = ParticipantItemWidget(p["id"], p["name"], self)
                list_item.setSizeHint(item_widget.sizeHint())
                self.list_widget.addItem(list_item)
                self.list_widget.setItemWidget(list_item, item_widget)
        self.list_widget.currentItemChanged.connect(self.on_selection_changed)

    def add_participant(self):
        name, ok = QInputDialog.getText(
            self, "Add Participant", "Enter participant's name:"
        )
        if ok and name.strip():
            database.add_participant(self.project_id, name.strip())
            self.load_participants()
            self.participant_updated.emit()

    def edit_participant(self, participant_id, current_name):
        new_name, ok = QInputDialog.getText(
            self, "Edit Participant", "Enter new name:", text=current_name
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            database.update_participant(participant_id, new_name.strip(), "")
            self.load_participants()
            self.participant_updated.emit()

    def delete_participant(self, participant_id, current_name):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{current_name}'? This will also unassign them from any documents or coded segments.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            database.delete_participant(participant_id)
            self.load_participants()
            self.participant_updated.emit()
