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
    QComboBox,
    QAbstractItemView,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeyEvent
from qt_material_icons import MaterialIcon

import database


class RenamableListWidget(QListWidget):
    """A QListWidget that handles the F2 key to trigger a rename action."""

    def __init__(self, parent_manager):
        super().__init__()
        self.parent_manager = parent_manager

    def keyPressEvent(self, event: QKeyEvent):
        """Handles F2 for rename and Delete for delete."""
        current_item = self.currentItem()
        if not current_item:
            super().keyPressEvent(event)
            return

        item_widget = self.itemWidget(current_item)
        if not item_widget:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_F2:
            if hasattr(item_widget, "on_edit_clicked"):
                item_widget.on_edit_clicked()
            event.accept()

        elif event.key() == Qt.Key.Key_Delete:
            if hasattr(item_widget, "on_delete_clicked"):
                item_widget.on_delete_clicked()
            event.accept()

        else:
            super().keyPressEvent(event)


class ParticipantItemWidget(QWidget):
    def __init__(self, participant_id, participant_name, stats_text, parent_manager):
        super().__init__()
        self.participant_id = participant_id
        self.participant_name = participant_name
        self.parent_manager = parent_manager

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 8)
        name_label = QLabel(participant_name)

        self.stats_label = QLabel(stats_text)
        self.stats_label.setStyleSheet("color: #888;")

        self.edit_button = QPushButton()
        edit_icon = MaterialIcon("edit")
        self.edit_button.setIcon(edit_icon)
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setToolTip("Edit Participant Name (F2)")
        self.edit_button.clicked.connect(self.on_edit_clicked)
        self.edit_button.setVisible(False)

        self.delete_button = QPushButton()
        delete_icon = MaterialIcon("delete")
        self.delete_button.setIcon(delete_icon)
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setToolTip("Delete Participant (Delete)")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.delete_button.setVisible(False)

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(self.stats_label)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)

    def set_icons_visible(self, visible):
        self.edit_button.setVisible(visible)
        self.delete_button.setVisible(visible)

    def set_selected_style(self, is_selected: bool):
        if is_selected:
            self.stats_label.setStyleSheet("color: white;")
        else:
            self.stats_label.setStyleSheet("color: #888;")

    def on_edit_clicked(self):
        self.parent_manager.edit_participant(self.participant_id, self.participant_name)

    def on_delete_clicked(self):
        self.parent_manager.delete_participant(
            self.participant_id, self.participant_name
        )


class ParticipantManager(QWidget):
    participant_updated = Signal()
    participant_selected = Signal(int)

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.current_document_id = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        header_layout = QHBoxLayout()
        header_label = QLabel("Participants")
        font = header_label.font()
        font.setBold(True)
        header_label.setFont(font)

        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Current Document", "Project Total"])
        self.scope_combo.setToolTip("Switch the scope of the stats calculation")
        self.scope_combo.setCurrentText("Current Document")

        self.show_all_button = QPushButton()
        show_all_icon = MaterialIcon("filter_list")
        self.show_all_button.setIcon(show_all_icon)
        self.show_all_button.setText("Show All")
        self.show_all_button.setToolTip("Clear selection and show all segments")
        self.show_all_button.clicked.connect(self.clear_selection)

        add_button = QPushButton()
        add_icon = MaterialIcon("add")
        add_button.setIcon(add_icon)
        add_button.setText("Add Participant")
        add_button.setToolTip("Add a new participant")
        add_button.clicked.connect(self.add_participant)

        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.scope_combo)
        header_layout.addWidget(self.show_all_button)
        header_layout.addWidget(add_button)
        main_layout.addLayout(header_layout)

        self.list_widget = RenamableListWidget(self)
        self.list_widget.currentItemChanged.connect(self.on_selection_changed)
        main_layout.addWidget(self.list_widget)

        self.scope_combo.currentTextChanged.connect(self.load_participants)
        self.load_participants()

    def set_current_document_id(self, doc_id):
        self.current_document_id = doc_id
        if self.scope_combo.currentText() == "Current Document":
            self.load_participants()

    def on_selection_changed(self, current_item, previous_item):
        if previous_item:
            widget = self.list_widget.itemWidget(previous_item)
            if widget:
                widget.set_icons_visible(False)
                widget.set_selected_style(False)

        if current_item:
            widget = self.list_widget.itemWidget(current_item)
            if widget:
                widget.set_icons_visible(True)
                widget.set_selected_style(True)
                self.participant_selected.emit(widget.participant_id)
        else:
            self.participant_selected.emit(0)

    def load_participants(self):
        # Safely disconnect to prevent warnings
        try:
            self.list_widget.currentItemChanged.disconnect(self.on_selection_changed)
        except RuntimeError:
            pass  # Signal was not connected

        self.list_widget.clear()
        participants = database.get_participants_for_project(self.project_id)

        scope = self.scope_combo.currentText()
        total_words = 0
        all_segments_in_scope = []

        if scope == "Current Document":
            if self.current_document_id:
                total_words = database.get_document_word_count(self.current_document_id)
                all_segments_in_scope = database.get_coded_segments_for_document(
                    self.current_document_id
                )
        else:  # Project Total
            total_words = database.get_project_word_count(self.project_id)
            all_segments_in_scope = database.get_coded_segments_for_project(
                self.project_id
            )

        if not participants:
            item = QListWidgetItem("No participants created.", self.list_widget)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        else:
            for p in sorted(participants, key=lambda x: x["name"]):
                participant_id = p["id"]

                # Filter segments for the current participant
                participant_segments = [
                    seg
                    for seg in all_segments_in_scope
                    if seg["participant_id"] == participant_id
                ]

                segment_count = len(participant_segments)
                word_count = sum(
                    len(seg["content_preview"].split()) for seg in participant_segments
                )

                stats_text = ""
                if segment_count > 0 and total_words > 0:
                    percentage = (word_count / total_words) * 100
                    stats_text = f"{percentage:.1f}% | {segment_count} Segments"
                elif segment_count > 0:
                    stats_text = f"{segment_count} Segments"

                list_item = QListWidgetItem(self.list_widget)
                item_widget = ParticipantItemWidget(
                    p["id"], p["name"], stats_text, self
                )
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

    def clear_selection(self):
        """Clears the current selection in the list widget."""
        self.list_widget.clearSelection()

    def highlight_participant_by_id(self, participant_id: int):
        """
        Highlights (selects and scrolls to) the participant with the given ID in the list widget,
        but does NOT trigger filtering or emit any signals. Used for visual highlight only.
        """
        self.list_widget.blockSignals(True)

        previous_item = self.list_widget.currentItem()
        if previous_item:
            widget = self.list_widget.itemWidget(previous_item)
            if widget:
                widget.set_icons_visible(False)
                widget.set_selected_style(False)

        new_current_item = None
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and widget.participant_id == participant_id:
                new_current_item = item
                break

        self.list_widget.setCurrentItem(new_current_item)

        if new_current_item:
            widget = self.list_widget.itemWidget(new_current_item)
            if widget:
                widget.set_icons_visible(False)
                widget.set_selected_style(True)
            self.list_widget.scrollToItem(
                new_current_item, QAbstractItemView.ScrollHint.PositionAtCenter
            )

        self.list_widget.blockSignals(False)
