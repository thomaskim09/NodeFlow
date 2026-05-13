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
from PySide6.QtGui import QKeyEvent, QColor, QIcon
from qt_material_icons import MaterialIcon
from utils.common import get_translation
from managers.theme_manager import load_settings

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
        self.name_label = QLabel(participant_name)

        self.stats_label = QLabel(stats_text)
        self.stats_label.setStyleSheet("color: #888;")

        self.edit_button = QPushButton()
        self.edit_icon = MaterialIcon("edit")
        self.edit_button.setIcon(self.edit_icon)
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setToolTip(
            get_translation("participant.edit_tooltip", parent_manager.language)
        )
        self.edit_button.clicked.connect(self.on_edit_clicked)
        self.edit_button.setVisible(False)

        self.delete_button = QPushButton()
        self.delete_icon = MaterialIcon("delete")
        self.delete_button.setIcon(self.delete_icon)
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setToolTip(
            get_translation("participant.delete_tooltip", parent_manager.language)
        )
        self.delete_button.clicked.connect(self.on_delete_clicked)
        self.delete_button.setVisible(False)

        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.stats_label)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)

    def set_icons_visible(self, visible):
        self.edit_button.setVisible(visible)
        self.delete_button.setVisible(visible)

    def set_selected_style(self, is_selected: bool):
        settings = load_settings()
        theme = settings.get("theme", "Default")
        is_dark = theme == "Dark"
        selected_fg = "#f0f0f0" if is_dark else "#000000"
        if is_selected:
            self.name_label.setStyleSheet(f"color: {selected_fg};")
            self.stats_label.setStyleSheet(f"color: {selected_fg};")
            self.edit_button.setStyleSheet(f"color: {selected_fg};")
            self.delete_button.setStyleSheet(f"color: {selected_fg};")
            icon_color = QColor(selected_fg)
            self.edit_icon.set_color(icon_color)
            self.delete_icon.set_color(icon_color)
            self.edit_button.setIcon(self.edit_icon)
            self.delete_button.setIcon(self.delete_icon)
        else:
            self.name_label.setStyleSheet("")
            self.stats_label.setStyleSheet("color: #888;")
            self.edit_button.setStyleSheet("")
            self.delete_button.setStyleSheet("")
            self.edit_icon._init_colors()
            self.delete_icon._init_colors()
            self.edit_button.setIcon(self.edit_icon)
            self.delete_button.setIcon(self.delete_icon)

    def on_edit_clicked(self):
        self.parent_manager.edit_participant(self.participant_id, self.participant_name)

    def on_delete_clicked(self):
        self.parent_manager.delete_participant(
            self.participant_id, self.participant_name
        )


class ParticipantManager(QWidget):
    participant_updated = Signal()
    participant_selected = Signal(int)

    def __init__(self, project_id, language=None):
        super().__init__()
        self.project_id = project_id
        self.language = language or "English"
        self.current_document_id = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        header_layout = QHBoxLayout()
        self.header_label = QLabel(get_translation("participant.header", self.language))
        font = self.header_label.font()
        font.setBold(True)
        self.header_label.setFont(font)

        self.scope_combo = QComboBox()
        self.scope_combo.addItems(
            [
                get_translation("participant.scope_current", self.language),
                get_translation("participant.scope_project", self.language),
            ]
        )
        self.scope_combo.setToolTip(
            get_translation("participant.show_all_tooltip", self.language)
        )
        self.scope_combo.setCurrentText(
            get_translation("participant.scope_current", self.language)
        )

        self.show_all_button = QPushButton()
        self.show_all_icon = MaterialIcon("filter_list")
        self.show_all_button.setIcon(self.show_all_icon)
        self.show_all_button.setText(
            get_translation("participant.show_all", self.language)
        )
        self.show_all_button.setToolTip(
            get_translation("participant.show_all_tooltip", self.language)
        )
        self.show_all_button.clicked.connect(self.clear_selection)

        self.add_button = QPushButton()
        self.add_icon = MaterialIcon("add")
        self.add_button.setIcon(self.add_icon)
        self.add_button.setText(get_translation("participant.add", self.language))
        self.add_button.setToolTip(
            get_translation("participant.add_tooltip", self.language)
        )
        self.add_button.clicked.connect(self.add_participant)

        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.scope_combo)
        header_layout.addWidget(self.show_all_button)
        header_layout.addWidget(self.add_button)
        main_layout.addLayout(header_layout)

        self.list_widget = RenamableListWidget(self)
        self.list_widget.currentItemChanged.connect(self.on_selection_changed)
        main_layout.addWidget(self.list_widget)

        self.scope_combo.currentTextChanged.connect(self.load_participants)
        self.update_theme(load_settings().get("theme", "Light"))
        self.load_participants()

    def set_current_document_id(self, doc_id):
        self.current_document_id = doc_id
        if self.scope_combo.currentText() == get_translation(
            "participant.scope_current", self.language
        ):
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
        self.list_widget.blockSignals(True)
        self.list_widget.setCurrentItem(None)

        self.list_widget.clear()
        participants = database.get_participants_for_project(self.project_id)

        scope = self.scope_combo.currentText()
        total_words = 0
        all_segments_in_scope = []

        if scope == get_translation("participant.scope_current", self.language):
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
            item = QListWidgetItem(
                get_translation("participant.no_participants", self.language),
                self.list_widget,
            )
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
                    stats_text = get_translation(
                        "participant.stats_with_percent",
                        self.language,
                        percent=f"{percentage:.1f}",
                        segments=segment_count,
                    )
                elif segment_count > 0:
                    stats_text = get_translation(
                        "participant.stats_segments_only",
                        self.language,
                        segments=segment_count,
                    )

                list_item = QListWidgetItem(self.list_widget)
                item_widget = ParticipantItemWidget(
                    p["id"], p["name"], stats_text, self
                )
                list_item.setSizeHint(item_widget.sizeHint())
                self.list_widget.addItem(list_item)
                self.list_widget.setItemWidget(list_item, item_widget)

        self.list_widget.blockSignals(False)

    def add_participant(self):
        name, ok = QInputDialog.getText(
            self,
            get_translation("participant.add_dialog_title", self.language),
            get_translation("participant.add_dialog_prompt", self.language),
        )
        if ok and name.strip():
            database.add_participant(self.project_id, name.strip())
            self.load_participants()
            self.participant_updated.emit()

    def edit_participant(self, participant_id, current_name):
        new_name, ok = QInputDialog.getText(
            self,
            get_translation("participant.edit_dialog_title", self.language),
            get_translation("participant.edit_dialog_prompt", self.language),
            text=current_name,
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            database.update_participant(participant_id, new_name.strip(), "")
            self.load_participants()
            self.participant_updated.emit()

    def delete_participant(self, participant_id, current_name):
        reply = QMessageBox.question(
            self,
            get_translation("participant.delete_confirm_title", self.language),
            get_translation(
                "participant.delete_confirm_message",
                self.language,
                current_name=current_name,
            ),
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

    def update_language(self, new_language):
        was_current_scope = self.scope_combo.currentText() == get_translation(
            "participant.scope_current", self.language
        )
        self.language = new_language
        self.header_label.setText(get_translation("participant.header", self.language))
        self.scope_combo.blockSignals(True)
        self.scope_combo.clear()
        self.scope_combo.addItems(
            [
                get_translation("participant.scope_current", self.language),
                get_translation("participant.scope_project", self.language),
            ]
        )
        self.scope_combo.setCurrentIndex(0 if was_current_scope else 1)
        self.scope_combo.blockSignals(False)
        self.show_all_button.setText(get_translation("participant.show_all", self.language))
        self.show_all_button.setToolTip(
            get_translation("participant.show_all_tooltip", self.language)
        )
        self.add_button.setText(get_translation("participant.add", self.language))
        self.add_button.setToolTip(get_translation("participant.add_tooltip", self.language))
        self.update_theme(load_settings().get("theme", "Light"))
        self.load_participants()

    def update_theme(self, theme):
        is_dark = theme == "Dark"
        fg = QColor("#f0f0f0" if is_dark else "#000000")
        disabled_fg = QColor("#a8a8a8" if is_dark else "#5e5e5e")
        self.show_all_icon.set_color(fg, QIcon.Mode.Normal)
        self.show_all_icon.set_color(disabled_fg, QIcon.Mode.Disabled)
        self.add_icon.set_color(fg, QIcon.Mode.Normal)
        self.add_icon.set_color(disabled_fg, QIcon.Mode.Disabled)
        self.show_all_button.setIcon(self.show_all_icon)
        self.add_button.setIcon(self.add_icon)
