from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QMessageBox,
    QTreeWidgetItemIterator,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QColor, QIcon
import database
from qt_material_icons import MaterialIcon
from utils.common import get_translation
from managers.theme_manager import load_settings, get_system_theme


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
                preview = current_item.text(0)
                if segment_id is not None:
                    self.parent_view.confirm_delete_segment(segment_id, preview)
                    event.accept()
                    return
        super().keyPressEvent(event)


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

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        controls_layout = QHBoxLayout()
        self.header_label = QLabel(get_translation("coded_segments.header", self.language))
        font = self.header_label.font()
        font.setBold(True)
        self.header_label.setFont(font)

        self.scope_combo = QComboBox()
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

        self.search_scope_combo = QComboBox()
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
            self.tree_widget.setItemWidget(
                previous, self.tree_widget.columnCount() - 1, None
            )

        if current:
            segment_id = current.data(0, 1)
            preview = current.text(0)

            edit_button = QPushButton()
            edit_icon = MaterialIcon("edit")
            edit_button.setIcon(edit_icon)
            edit_button.setObjectName("codedSegmentEditButton")
            edit_button.setFixedSize(20, 20)
            edit_button.setToolTip(
                get_translation("coded_segments.edit_segment_tooltip", self.language)
            )
            edit_button.clicked.connect(
                lambda checked=False, sid=segment_id: self.request_segment_edit(sid)
            )

            delete_button = QPushButton()
            delete_icon = MaterialIcon("delete")
            delete_button.setIcon(delete_icon)
            delete_button.setObjectName("codedSegmentDeleteButton")
            delete_button.setFixedSize(20, 20)
            delete_button.setToolTip(
                get_translation("coded_segments.delete_segment_tooltip", self.language)
            )
            delete_button.clicked.connect(
                lambda: self.confirm_delete_segment(segment_id, preview)
            )

            settings = load_settings()
            theme = settings.get("theme", "Default")
            is_dark = get_system_theme() == "Dark" if theme == "Default" else theme == "Dark"
            selected_fg = "#f0f0f0" if is_dark else "#000000"
            icon_color = QColor(selected_fg)
            edit_icon.set_color(icon_color)
            delete_icon.set_color(icon_color)
            edit_button.setIcon(edit_icon)
            delete_button.setIcon(delete_icon)

            button_container = QWidget()
            button_container.setFixedHeight(20)
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(5)
            button_layout.addStretch()
            button_layout.addWidget(edit_button)
            button_layout.addWidget(delete_button)
            button_layout.addStretch()

            self.tree_widget.setItemWidget(
                current, self.tree_widget.columnCount() - 1, button_container
            )

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
            database.delete_coded_segment(segment_id)
            self.all_segments = [s for s in self.all_segments if s["id"] != segment_id]
            (current_item.parent() or self.tree_widget.invisibleRootItem()).removeChild(
                current_item
            )
            self.segment_deleted.emit()

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
                get_translation("coded_segments.col_coded_text", self.language),
                get_translation("coded_segments.col_node", self.language),
                get_translation("coded_segments.col_participant", self.language),
                "",
            ]
            self.tree_widget.setHeaderLabels(headers)
            self.tree_widget.setColumnWidth(0, 300)
            self.tree_widget.setColumnWidth(1, 150)
            self.tree_widget.setColumnWidth(2, 150)
            self.tree_widget.setColumnWidth(3, 50)
            self.search_scope_combo.clear()
            self.search_scope_combo.addItems(
                [
                    get_translation("coded_segments.search_all", self.language),
                    get_translation("coded_segments.col_coded_text", self.language),
                    get_translation("coded_segments.col_node", self.language),
                    get_translation("coded_segments.col_participant", self.language),
                ]
            )
            if self.current_document_id:
                self.all_segments = database.get_coded_segments_for_document(
                    self.current_document_id
                )
        elif scope == "Entire Project":
            headers = [
                get_translation("coded_segments.col_coded_text", self.language),
                get_translation("coded_segments.col_node", self.language),
                get_translation("coded_segments.col_participant", self.language),
                get_translation("coded_segments.col_document", self.language),
                "",
            ]
            self.tree_widget.setHeaderLabels(headers)
            self.tree_widget.setColumnWidth(0, 300)
            self.tree_widget.setColumnWidth(1, 150)
            self.tree_widget.setColumnWidth(2, 150)
            self.tree_widget.setColumnWidth(3, 200)
            self.tree_widget.setColumnWidth(4, 50)
            self.search_scope_combo.clear()
            self.search_scope_combo.addItems(
                [
                    get_translation("coded_segments.search_all", self.language),
                    get_translation("coded_segments.col_coded_text", self.language),
                    get_translation("coded_segments.col_node", self.language),
                    get_translation("coded_segments.col_participant", self.language),
                    get_translation("coded_segments.col_document", self.language),
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
                preview,
                segment["node_name"],
                participant_name,
            ]
            if is_entire_project:
                item_data.append(segment["document_title"])

            item = QTreeWidgetItem(self.tree_widget, item_data)
            item.setData(0, 1, segment["id"])

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

        if scope == "All":
            return text_match or node_match or participant_match or doc_match
        elif scope == "Coded Text":
            return text_match
        elif scope == "Node":
            return node_match
        elif scope == "Participant":
            return participant_match
        elif scope == "Document":
            return doc_match
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
