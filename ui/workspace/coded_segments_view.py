from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QTreeWidgetItemIterator,
    QAbstractItemView,
    QFrame,
    QMenu,
    QHeaderView,
    QDialog,
    QDialogButtonBox,
    QTextEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QColor, QIcon
import database
from qt_material_icons import MaterialIcon
from utils.common import get_translation
from managers.theme_manager import load_settings, get_effective_theme_mode
from repositories.workspace_snapshot_repository import workspace_snapshot_repository
from services.workspace_history_service import WorkspaceCommand
from ui.combo_box import FitPopupComboBox


class DeletableTreeWidget(QTreeWidget):
    """A QTreeWidget that handles the Delete key to remove a segment."""

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            current_item = self.currentItem()
            if current_item:
                segment_id = current_item.data(0, 1)
                preview = current_item.text(self.parent_view.preview_column)
                if segment_id is not None:
                    self.parent_view.confirm_delete_segment(segment_id, preview)
                    event.accept()
                    return
        super().keyPressEvent(event)


class ColorSwatch(QFrame):
    def __init__(self, color_hex: str):
        super().__init__()
        self.setFixedSize(14, 14)
        self.setStyleSheet(
            f"background-color: {color_hex}; border: 1px solid #888; border-radius: 2px;"
        )


class ColorSwatchCell(QWidget):
    def __init__(self, color_hex: str, tooltip: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        swatch = ColorSwatch(color_hex)
        swatch.setToolTip(tooltip)
        layout.addWidget(swatch)


class SegmentActionCell(QWidget):
    def __init__(self, language, click_handler):
        super().__init__()
        self.menu_button = QPushButton()
        self.menu_icon = MaterialIcon("more_vert")
        self.menu_button.setIcon(self.menu_icon)
        self.menu_button.setObjectName("codedSegmentActionButton")
        self.menu_button.setFixedSize(20, 20)
        self.menu_button.setToolTip(
            get_translation("coded_segments.more_actions_tooltip", language)
        )
        self.menu_button.clicked.connect(click_handler)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.menu_button)
        self.set_selected(False)

    def set_selected(self, is_selected: bool):
        is_dark = get_effective_theme_mode() == "Dark"
        selected_fg = "#f0f0f0" if is_dark else "#000000"
        normal_fg = "#d8d8d8" if is_dark else "#222222"
        current_fg = selected_fg if is_selected else normal_fg
        self.menu_button.setStyleSheet(f"color: {current_fg};")
        self.menu_icon.set_color(QColor(current_fg))
        self.menu_button.setIcon(self.menu_icon)


class CodedSegmentsView(QWidget):
    segment_deleted = Signal()
    segment_activated = Signal(int, int, int)  # document_id, start, end
    segment_edit_requested = Signal(int, int, int, int)  # seg_id, doc_id, start, end

    def __init__(self, project_id, language=None):
        super().__init__()
        self.project_id = project_id
        self.language = language or "English"
        self.current_document_id = None
        self.segments = []
        self.all_segments = []
        self._last_active_node_filter = None
        self.undo_executor = None
        self.color_column = 0
        self.preview_column = 1
        self.remark_column = 4

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        controls_layout = QHBoxLayout()
        self.header_label = QLabel(get_translation("coded_segments.header", self.language))
        font = self.header_label.font()
        font.setBold(True)
        self.header_label.setFont(font)

        self.scope_combo = FitPopupComboBox()
        self.scope_combo.addItems(
            [
                get_translation("coded_segments.scope_current", self.language),
                get_translation("coded_segments.scope_project", self.language),
            ]
        )
        self.scope_combo.setToolTip(
            get_translation("coded_segments.scope_tooltip", self.language)
        )

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            get_translation("coded_segments.search_placeholder", self.language)
        )
        self.search_icon = MaterialIcon("search", fill=False)
        self.search_icon_label = QLabel()
        self.search_icon_label.setPixmap(self.search_icon.pixmap(16, 16))
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        search_layout.addWidget(self.search_icon_label)
        search_layout.addWidget(self.search_input)
        search_container = QWidget()
        search_container.setLayout(search_layout)

        self.search_scope_combo = FitPopupComboBox()
        self.search_scope_combo.setToolTip(
            get_translation("coded_segments.search_scope_tooltip", self.language)
        )

        controls_layout.addWidget(self.header_label)
        controls_layout.addWidget(self.scope_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(search_container)
        controls_layout.addWidget(self.search_scope_combo)
        main_layout.addLayout(controls_layout)

        self.tree_widget = DeletableTreeWidget(self)
        self.tree_widget.setRootIsDecorated(False)
        self.tree_widget.setIndentation(0)
        self.tree_widget.setUniformRowHeights(True)
        self.tree_widget.setAllColumnsShowFocus(True)
        self.tree_widget.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        header = self.tree_widget.header()
        header.setSectionsMovable(False)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(24)
        main_layout.addWidget(self.tree_widget)

        self.scope_combo.currentTextChanged.connect(self.reload_view)
        self.search_input.textChanged.connect(self.filter_tree)
        self.search_scope_combo.currentTextChanged.connect(self.filter_tree)
        self.tree_widget.currentItemChanged.connect(self.on_selection_changed)
        self.tree_widget.itemActivated.connect(self.on_segment_activated)

        self.scope_combo.setCurrentText(
            get_translation("coded_segments.scope_current", self.language)
        )
        self.update_theme(load_settings().get("theme", "Light"))
        self.reload_view()

    def set_undo_executor(self, undo_executor):
        self.undo_executor = undo_executor

    def execute_workspace_command(self, command: WorkspaceCommand):
        if self.undo_executor:
            self.undo_executor(command)
        else:
            command.do()
            command.after_refresh()

    def on_segment_activated(self, item: QTreeWidgetItem, column: int):
        segment_id = item.data(0, 1)
        if segment_id is None:
            return

        segment_data = next(
            (s for s in self.all_segments if s["id"] == segment_id), None
        )
        if not segment_data:
            return

        doc_id = None
        if self.scope_combo.currentText() == get_translation(
            "coded_segments.scope_current", self.language
        ):
            doc_id = self.current_document_id
        else:
            doc_id = segment_data.get("document_id")

        if doc_id is not None:
            self.segment_activated.emit(
                doc_id, segment_data["segment_start"], segment_data["segment_end"]
            )

    def highlight_segment_by_id(self, segment_id):
        if not segment_id:
            return

        # Clear node filter
        self._last_active_node_filter = None
        self.search_input.clear()
        self.filter_tree()

        self.tree_widget.blockSignals(True)
        it = QTreeWidgetItemIterator(self.tree_widget)
        while it.value():
            item = it.value()
            if item.data(0, 1) == segment_id:
                self.tree_widget.setCurrentItem(item)
                self.tree_widget.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
                break
            it += 1
        self.tree_widget.blockSignals(False)

    def on_selection_changed(self, current, previous):
        if previous:
            previous_widget = self.tree_widget.itemWidget(
                previous, self.tree_widget.columnCount() - 1
            )
            if isinstance(previous_widget, SegmentActionCell):
                previous_widget.set_selected(False)

        if current:
            current_widget = self.tree_widget.itemWidget(
                current, self.tree_widget.columnCount() - 1
            )
            if isinstance(current_widget, SegmentActionCell):
                current_widget.set_selected(True)

    def show_segment_actions_menu(self, segment_id, preview, source):
        menu = QMenu(self)
        edit_action = menu.addAction(
            get_translation("coded_segments.edit_segment_tooltip", self.language)
        )
        edit_remark_action = menu.addAction(
            get_translation("coded_segments.edit_remark_tooltip", self.language)
        )
        delete_action = menu.addAction(
            get_translation("coded_segments.delete_segment_tooltip", self.language)
        )
        button = source
        if isinstance(source, QTreeWidgetItem):
            action_widget = self.tree_widget.itemWidget(
                source, self.tree_widget.columnCount() - 1
            )
            if isinstance(action_widget, SegmentActionCell):
                button = action_widget.menu_button
        action = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        if action == edit_action:
            self.request_segment_edit(segment_id)
        elif action == edit_remark_action:
            self.edit_segment_remark(segment_id)
        elif action == delete_action:
            self.confirm_delete_segment(segment_id, preview)

    def confirm_delete_segment(self, segment_id, segment_preview):
        current_item = self.tree_widget.currentItem()
        if not current_item or current_item.data(0, 1) != segment_id:
            return

        reply = QMessageBox.question(
            self,
            get_translation("coded_segments.confirm_delete_title", self.language),
            get_translation(
                "coded_segments.confirm_delete_message",
                self.language,
                preview=segment_preview,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            snapshot = workspace_snapshot_repository.get_segment(segment_id)
            if not snapshot:
                return

            def do():
                database.delete_coded_segment(segment_id)

            def undo():
                workspace_snapshot_repository.restore_segment(snapshot)

            self.execute_workspace_command(
                WorkspaceCommand(
                    "Delete Coded Segment",
                    do,
                    undo,
                    lambda: (self.reload_view(), self.segment_deleted.emit()),
                )
            )

    def request_segment_edit(self, segment_id):
        if segment_id is None:
            return

        segment_data = next(
            (s for s in self.all_segments if s["id"] == segment_id), None
        )
        if not segment_data:
            return

        doc_id = None
        if self.scope_combo.currentText() == get_translation(
            "coded_segments.scope_current", self.language
        ):
            doc_id = self.current_document_id
        else:
            doc_id = segment_data.get("document_id")

        if doc_id is not None:
            self.segment_edit_requested.emit(
                segment_id,
                doc_id,
                segment_data["segment_start"],
                segment_data["segment_end"],
            )

    def edit_segment_remark(self, segment_id):
        segment_data = next(
            (s for s in self.all_segments if s["id"] == segment_id), None
        )
        if not segment_data:
            return
        dialog = SegmentRemarkDialog(
            self.language, segment_data.get("remark", ""), self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        old_remark = segment_data.get("remark", "")
        new_remark = dialog.remark_text()
        if new_remark == old_remark:
            return

        def do():
            database.update_coded_segment_remark(segment_id, new_remark)

        def undo():
            database.update_coded_segment_remark(segment_id, old_remark)

        self.execute_workspace_command(
            WorkspaceCommand(
                "Edit Segment Remark",
                do,
                undo,
                lambda sid=segment_id: (self.reload_view(), self.highlight_segment_by_id(sid)),
            )
        )

    def load_segments(self, document_id):
        self.search_input.clear()
        self.current_document_id = document_id
        self.reload_view()

    def reload_view(self):
        self.tree_widget.blockSignals(True)
        self.tree_widget.setCurrentItem(None)

        self.tree_widget.clear()
        self.all_segments = []
        scope_display = self.scope_combo.currentText()
        # Map translated scope labels back to internal keys
        if scope_display == get_translation(
            "coded_segments.scope_current", self.language
        ):
            scope = "Current Document"
        else:
            scope = "Entire Project"

        if scope == "Current Document":
            headers = [
                "",
                get_translation("coded_segments.col_coded_text", self.language),
                get_translation("coded_segments.col_node", self.language),
                get_translation("coded_segments.col_participant", self.language),
                get_translation("coded_segments.col_remark", self.language),
                "",
            ]
            self.tree_widget.setHeaderLabels(headers)
            self._configure_columns(is_entire_project=False)
            self.search_scope_combo.clear()
            self.search_scope_combo.addItems(
                [
                    get_translation("coded_segments.search_all", self.language),
                    get_translation("coded_segments.col_coded_text", self.language),
                    get_translation("coded_segments.col_node", self.language),
                    get_translation("coded_segments.col_participant", self.language),
                    get_translation("coded_segments.col_remark", self.language),
                ]
            )
            if self.current_document_id:
                self.all_segments = database.get_coded_segments_for_document(
                    self.current_document_id
                )
        elif scope == "Entire Project":
            headers = [
                "",
                get_translation("coded_segments.col_coded_text", self.language),
                get_translation("coded_segments.col_node", self.language),
                get_translation("coded_segments.col_participant", self.language),
                get_translation("coded_segments.col_document", self.language),
                get_translation("coded_segments.col_remark", self.language),
                "",
            ]
            self.tree_widget.setHeaderLabels(headers)
            self._configure_columns(is_entire_project=True)
            self.search_scope_combo.clear()
            self.search_scope_combo.addItems(
                [
                    get_translation("coded_segments.search_all", self.language),
                    get_translation("coded_segments.col_coded_text", self.language),
                    get_translation("coded_segments.col_node", self.language),
                    get_translation("coded_segments.col_participant", self.language),
                    get_translation("coded_segments.col_document", self.language),
                    get_translation("coded_segments.col_remark", self.language),
                ]
            )
            self.all_segments = database.get_coded_segments_for_project(self.project_id)

        self.populate_tree(self.all_segments)
        # Reconnect the signal after populating
        self.tree_widget.blockSignals(False)

        if self._last_active_node_filter is not None:
            self.filter_by_node_family(self._last_active_node_filter)
        else:
            self.filter_tree()

    def _configure_columns(self, is_entire_project: bool):
        header = self.tree_widget.header()
        action_column = 6 if is_entire_project else 5

        header.setSectionResizeMode(self.color_column, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.color_column, 48)

        header.setSectionResizeMode(self.preview_column, QHeaderView.ResizeMode.Stretch)

        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.resizeSection(2, 140)

        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.resizeSection(3, 120)

        if is_entire_project:
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.resizeSection(4, 180)
            self.remark_column = 5
        else:
            self.remark_column = 4

        header.setSectionResizeMode(self.remark_column, QHeaderView.ResizeMode.Stretch)

        header.setSectionResizeMode(action_column, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(action_column, 34)

    def populate_tree(self, segments):
        is_entire_project = self.scope_combo.currentText() == get_translation(
            "coded_segments.scope_project", self.language
        )
        for segment in segments:
            preview = (
                segment["content_preview"]
                .replace("\n", " ")
                .replace("\t", " ")
                .strip()
            )
            if len(preview) > 100:
                preview = preview[:100] + "..."

            # This line should now work correctly as `segment` is a dict
            participant_name = segment.get("participant_name") or get_translation(
                "coded_segments.not_available", self.language
            )

            item_data = [
                "",
                preview,
                segment["node_name"],
                participant_name,
            ]
            if is_entire_project:
                item_data.append(segment["document_title"])
            item_data.append((segment.get("remark") or "").replace("\n", " ").strip())
            item_data.append("")

            item = QTreeWidgetItem(self.tree_widget, item_data)
            item.setData(0, 1, segment["id"])
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
            item.setTextAlignment(self.color_column, Qt.AlignmentFlag.AlignCenter)
            swatch = ColorSwatchCell(segment["node_color"], segment["node_name"])
            self.tree_widget.setItemWidget(item, self.color_column, swatch)
            action_widget = SegmentActionCell(
                self.language,
                lambda checked=False, sid=segment["id"], seg_preview=preview, tree_item=item: self.show_segment_actions_menu(
                    sid, seg_preview, tree_item
                ),
            )
            self.tree_widget.setItemWidget(
                item, self.tree_widget.columnCount() - 1, action_widget
            )

    def filter_tree(self):
        self._last_active_node_filter = None
        search_text = self.search_input.text().lower()
        scope_display = self.search_scope_combo.currentText()
        view_scope_display = self.scope_combo.currentText()
        # Map translated scope labels back to internal keys
        if view_scope_display == get_translation(
            "coded_segments.scope_current", self.language
        ):
            view_scope = "Current Document"
        else:
            view_scope = "Entire Project"
        # Map search scope
        if scope_display == get_translation("coded_segments.search_all", self.language):
            scope = "All"
        elif scope_display == get_translation(
            "coded_segments.col_coded_text", self.language
        ):
            scope = "Coded Text"
        elif scope_display == get_translation("coded_segments.col_node", self.language):
            scope = "Node"
        elif scope_display == get_translation(
            "coded_segments.col_participant", self.language
        ):
            scope = "Participant"
        elif scope_display == get_translation(
            "coded_segments.col_document", self.language
        ):
            scope = "Document"
        elif scope_display == get_translation("coded_segments.col_remark", self.language):
            scope = "Remark"
        else:
            scope = "All"

        self.tree_widget.blockSignals(True)
        self.tree_widget.setCurrentItem(None)

        self.tree_widget.clear()

        if not search_text:
            self.populate_tree(self.all_segments)
        else:
            filtered_segments = [
                seg
                for seg in self.all_segments
                if self._segment_matches_filter(seg, search_text, scope, view_scope)
            ]
            self.populate_tree(filtered_segments)

        self.tree_widget.blockSignals(False)

    def _segment_matches_filter(self, seg, search_text, scope, view_scope):
        text_match = search_text in seg["content_preview"].lower()
        node_match = search_text in seg["node_name"].lower()
        participant_match = (
            seg.get("participant_name")
            and search_text in seg.get("participant_name", "").lower()
        )
        doc_match = (
            view_scope == "Entire Project"
            and "document_title" in seg
            and search_text in seg["document_title"].lower()
        )
        remark_match = search_text in (seg.get("remark") or "").lower()

        if scope == "All":
            return text_match or node_match or participant_match or doc_match or remark_match
        elif scope == "Coded Text":
            return text_match
        elif scope == "Node":
            return node_match
        elif scope == "Participant":
            return participant_match
        elif scope == "Document":
            return doc_match
        elif scope == "Remark":
            return remark_match
        return False

    def filter_by_node_family(self, node_ids: list):
        self.search_input.clear()
        self._last_active_node_filter = node_ids

        self.tree_widget.blockSignals(True)
        self.tree_widget.setCurrentItem(None)

        self.tree_widget.clear()

        if not node_ids:
            self.populate_tree(self.all_segments)
        else:
            node_filtered_segments = [
                seg for seg in self.all_segments if seg["node_id"] in node_ids
            ]
            self.populate_tree(node_filtered_segments)

        self.tree_widget.blockSignals(False)

    def filter_by_single_node(self, node_id: int):
        self.search_input.clear()
        self._last_active_node_filter = [node_id]

        self.tree_widget.blockSignals(True)
        self.tree_widget.setCurrentItem(None)

        self.tree_widget.clear()

        if not node_id:
            self.populate_tree(self.all_segments)
        else:
            node_filtered_segments = [
                seg for seg in self.all_segments if seg["node_id"] == node_id
            ]
            self.populate_tree(node_filtered_segments)

        self.tree_widget.blockSignals(False)

    def filter_segments_by_participant(self, participant_id: int):
        if not self.all_segments:
            return
        self.tree_widget.blockSignals(True)
        self.tree_widget.setCurrentItem(None)
        self.tree_widget.clear()
        if participant_id == 0:
            target_segments = self.all_segments
        else:
            target_segments = [
                seg
                for seg in self.all_segments
                if seg.get("participant_id") == participant_id
            ]
        self.populate_tree(target_segments)
        self.tree_widget.blockSignals(False)

    def update_language(self, new_language):
        self.language = new_language
        self.header_label.setText(get_translation("coded_segments.header", self.language))
        current_scope_index = self.scope_combo.currentIndex()
        self.scope_combo.blockSignals(True)
        self.scope_combo.clear()
        self.scope_combo.addItems(
            [
                get_translation("coded_segments.scope_current", self.language),
                get_translation("coded_segments.scope_project", self.language),
            ]
        )
        self.scope_combo.setCurrentIndex(max(0, current_scope_index))
        self.scope_combo.setToolTip(
            get_translation("coded_segments.scope_tooltip", self.language)
        )
        self.scope_combo.blockSignals(False)
        self.search_input.setPlaceholderText(
            get_translation("coded_segments.search_placeholder", self.language)
        )
        self.search_scope_combo.setToolTip(
            get_translation("coded_segments.search_scope_tooltip", self.language)
        )
        self.update_theme(load_settings().get("theme", "Light"))
        self.reload_view()

    def update_theme(self, theme):
        is_dark = theme == "Dark"
        fg = QColor("#e8e8e8" if is_dark else "#4a4a4a")
        self.search_icon.set_color(fg, QIcon.Mode.Normal)
        self.search_icon_label.setPixmap(self.search_icon.pixmap(16, color=fg))


class SegmentRemarkDialog(QDialog):
    def __init__(self, language, remark_text, parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(
            get_translation("coded_segments.edit_remark_dialog_title", self.language)
        )
        layout = QVBoxLayout(self)
        label = QLabel(get_translation("coded_segments.edit_remark_label", self.language))
        self.editor = QTextEdit()
        self.editor.setPlaceholderText(
            get_translation("coded_segments.edit_remark_placeholder", self.language)
        )
        self.editor.setPlainText(remark_text)
        layout.addWidget(label)
        layout.addWidget(self.editor)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def remark_text(self):
        return self.editor.toPlainText()
